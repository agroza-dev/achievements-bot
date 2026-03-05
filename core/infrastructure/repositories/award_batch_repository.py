"""
Репозиторий для работы с пакетами периодических зачислений (award_batches).

Обеспечивает:
- Создание batch для чата
- Получение незавершённых batch
- Обновление cursor (возобновление после падения)
- Завершение batch
"""

import logging
from dataclasses import dataclass

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class AwardBatch:
    """Модель пакета зачислений."""

    id: int
    chat_id: int
    period_key: str  # "2026-W09"
    status: str  # pending|processing|done
    cursor_user_id: int | None  # ID последнего обработанного пользователя
    created_at: asyncpg.pgproto.pgproto.Datetime
    completed_at: asyncpg.pgproto.pgproto.Datetime | None


class AwardBatchRepository:
    """Репозиторий для управления batch зачислений."""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_or_get_batch(
        self,
        chat_id: int,
        period_key: str,
    ) -> AwardBatch:
        """
        Создать batch для чата на период или получить существующий.

        Idempotency обеспечивается UNIQUE(chat_id, period_key).

        Args:
            chat_id: Внутренний ID чата
            period_key: Ключ периода (например, "2026-W09")

        Returns:
            Созданный или существующий batch
        """
        query = """
            INSERT INTO award_batches (chat_id, period_key, status)
            VALUES ($1, $2, 'pending')
            ON CONFLICT (chat_id, period_key) DO NOTHING
            RETURNING id, chat_id, period_key, status, cursor_user_id, created_at, completed_at
        """

        record = await self.conn.fetchrow(query, chat_id, period_key)

        if record:
            logger.debug(f"Создан новый batch {record['id']} для чата {chat_id}, период {period_key}")
            return self._map_batch(record)

        # Batch уже существует
        return await self.get_batch(chat_id, period_key)

    async def get_batch(
        self,
        chat_id: int,
        period_key: str,
    ) -> AwardBatch | None:
        """Получить batch по chat_id и period_key."""
        query = """
            SELECT id, chat_id, period_key, status, cursor_user_id, created_at, completed_at
            FROM award_batches
            WHERE chat_id = $1 AND period_key = $2
        """
        record = await self.conn.fetchrow(query, chat_id, period_key)
        return self._map_batch(record) if record else None

    async def get_next_pending_batch(self) -> AwardBatch | None:
        """
        Получить следующий pending batch для обработки.

        Returns:
            Batch или None, если нет pending batch
        """
        query = """
            SELECT id, chat_id, period_key, status, cursor_user_id, created_at, completed_at
            FROM award_batches
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
        """
        record = await self.conn.fetchrow(query)
        return self._map_batch(record) if record else None

    async def get_next_processing_batch(self) -> AwardBatch | None:
        """
        Получить processing batch для продолжения обработки.

        Это нужно для recovery после падения бота.

        Returns:
            Batch или None, если нет processing batch
        """
        query = """
            SELECT id, chat_id, period_key, status, cursor_user_id, created_at, completed_at
            FROM award_batches
            WHERE status = 'processing'
            ORDER BY created_at ASC
            LIMIT 1
        """
        record = await self.conn.fetchrow(query)
        return self._map_batch(record) if record else None

    async def mark_processing(self, batch_id: int) -> None:
        """
        Пометить batch как processing.

        Args:
            batch_id: ID batch
        """
        query = """
            UPDATE award_batches
            SET status = 'processing'
            WHERE id = $1 AND status = 'pending'
        """
        await self.conn.execute(query, batch_id)
        logger.debug(f"Batch {batch_id} помечен как processing")

    async def update_cursor(self, batch_id: int, cursor_user_id: int) -> None:
        """
        Обновить cursor (ID последнего обработанного пользователя).

        Args:
            batch_id: ID batch
            cursor_user_id: ID пользователя
        """
        query = """
            UPDATE award_batches
            SET cursor_user_id = $2
            WHERE id = $1
        """
        await self.conn.execute(query, batch_id, cursor_user_id)

    async def mark_done(self, batch_id: int) -> None:
        """
        Пометить batch как завершённый.

        Args:
            batch_id: ID batch
        """
        query = """
            UPDATE award_batches
            SET status = 'done', completed_at = NOW()
            WHERE id = $1
        """
        await self.conn.execute(query, batch_id)
        logger.info(f"Batch {batch_id} завершён")

    async def get_users_for_batch(
        self,
        batch: AwardBatch,
        limit: int = 50,
    ) -> list[int]:
        """
        Получить пользователей для обработки.

        Берёт пользователей с ID > cursor_user_id (если есть) или всех сначала.

        Args:
            batch: Batch для обработки
            limit: Максимальное количество пользователей за раз

        Returns:
            Список ID пользователей
        """
        if batch.cursor_user_id:
            query = """
                SELECT user_id
                FROM chat_users
                WHERE chat_id = $1 AND is_active = true AND user_id > $2
                ORDER BY user_id
                LIMIT $3
            """
            rows = await self.conn.fetch(query, batch.chat_id, batch.cursor_user_id, limit)
        else:
            query = """
                SELECT user_id
                FROM chat_users
                WHERE chat_id = $1 AND is_active = true
                ORDER BY user_id
                LIMIT $2
            """
            rows = await self.conn.fetch(query, batch.chat_id, limit)

        return [row["user_id"] for row in rows]

    async def recover_stuck_batches(self, timeout_minutes: int = 5) -> int:
        """
        Вернуть stuck batch из processing в pending.

        Args:
            timeout_minutes: Через сколько минут считать batch stuck

        Returns:
            Количество восстановленных batch
        """
        query = f"""
            UPDATE award_batches
            SET status = 'pending', cursor_user_id = NULL
            WHERE status = 'processing'
              AND created_at < NOW() - INTERVAL '{timeout_minutes} minutes'
            RETURNING id
        """

        rows = await self.conn.fetch(query)
        count = len(rows)

        if count > 0:
            logger.warning(f"Восстановлено {count} stuck batch: {[r['id'] for r in rows]}")

        return count

    @staticmethod
    def _map_batch(record: asyncpg.Record) -> AwardBatch:
        """Преобразовать запись БД в модель."""
        return AwardBatch(
            id=record["id"],
            chat_id=record["chat_id"],
            period_key=record["period_key"],
            status=record["status"],
            cursor_user_id=record["cursor_user_id"],
            created_at=record["created_at"],
            completed_at=record["completed_at"],
        )
