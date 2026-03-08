import asyncpg
from telegram import Chat

from core.dto.chat_dto import ChatDTO
from core.dto.chat_user_dto import UserChatDTO
from core.infrastructure.repositories.mappers.chat_mapper import map_chat


class ChatRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_by_tg_id(self, tg_id: int) -> ChatDTO | None:
        query = "SELECT * FROM chats WHERE tg_id = $1"

        record = await self.conn.fetchrow(query, tg_id)

        return map_chat(record) if record else None

    async def list_for_user(
        self,
        *,
        user_id: int,
    ) -> list[UserChatDTO]:
        rows = await self.conn.fetch(
            """
            SELECT
                c.id,
                c.tg_id as chat_id,
                c.title
            FROM chat_users cu
                     JOIN chats c ON c.id = cu.chat_id
            WHERE cu.user_id = $1
              AND cu.is_active = true
            ORDER BY c.title
            """,
            user_id,
        )

        return [
            UserChatDTO(
                id=row["id"],
                chat_id=row["chat_id"],
                title=row["title"],
            )
            for row in rows
        ]

    async def upsert(self, chat: Chat) -> ChatDTO:
        query = """
            INSERT INTO chats (tg_id, type, title, is_active)
            VALUES ($1, $2, $3, true)
            ON CONFLICT (tg_id) DO UPDATE
            SET
                type = EXCLUDED.type,
                title = EXCLUDED.title,
                is_active = true,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """
        record = await self.conn.fetchrow(
            query,
            chat.id,
            chat.type,
            chat.title,
        )

        # Создаём настройки по умолчанию если их нет
        if record:
            await self._ensure_settings_exist(record["id"])

        return map_chat(record)

    async def _ensure_settings_exist(self, chat_id: int) -> None:
        """Создать настройки по умолчанию если их нет."""
        await self.conn.execute("""
            INSERT INTO chat_settings (chat_id)
            VALUES ($1)
            ON CONFLICT (chat_id) DO NOTHING
        """, chat_id)

    async def deactivate(self, chat_id: int):
        """Деактивировать чат."""
        query = """
            UPDATE chats
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await self.conn.execute(query, chat_id)

    async def activate(self, chat_id: int):
        """Активировать чат."""
        query = """
            UPDATE chats
            SET is_active = true, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await self.conn.execute(query, chat_id)

    async def migrate_chat(self, old_tg_id: int, new_tg_id: int) -> bool:
        """
        Миграция чата при превращении группы в супергруппу.

        Обновляет tg_id чата в базе данных, сохраняя все связанные данные.

        Args:
            old_tg_id: Старый идентификатор чата (группа)
            new_tg_id: Новый идентификатор чата (супергруппа)

        Returns:
            True если миграция успешна, False если чат не найден
        """
        query = """
            UPDATE chats
            SET tg_id = $1, updated_at = CURRENT_TIMESTAMP
            WHERE tg_id = $2
        """
        result = await self.conn.execute(query, new_tg_id, old_tg_id)
        return result != "UPDATE 0"

    async def list_active_chats(self) -> list[dict]:
        """
        Получить все активные чаты с флагом включения зачислений.

        Returns:
            Список dict с полями: chat_id, is_award_enabled
        """
        query = """
            SELECT
                c.id as chat_id,
                COALESCE(cs.periodic_award_enabled, true) as is_award_enabled
            FROM chats c
            LEFT JOIN chat_settings cs ON c.id = cs.chat_id
            WHERE c.is_active = true
            ORDER BY c.id
        """
        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]
