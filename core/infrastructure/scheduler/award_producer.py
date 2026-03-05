"""
Producer для создания пакетов периодических зачислений.

Запускается по расписанию (cron) и создаёт batch для каждого
активного чата с включенными зачислениями.

Надёжность:
- Idempotency через UNIQUE(chat_id, period_key) в БД
- period_key = номер недели (например, "2026-W09")
"""

import logging
from datetime import UTC, datetime

import asyncpg

from core.config import settings
from core.infrastructure.repositories.award_batch_repository import AwardBatchRepository
from core.infrastructure.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class AwardProducer:
    """
    Producer для создания batch периодических зачислений.

    Вызывается по cron расписанию из конфига.
    """

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._db_config = {
            'host': settings.db.host,
            'port': settings.db.port,
            'database': settings.db.name,
            'user': settings.db.login,
            'password': settings.db.password,
        }

    async def create_batches(self) -> int:
        """
        Создать batch для всех активных чатов.

        Returns:
            Количество созданных batch
        """
        # Создаём НОВОЕ подключение в этом event loop
        conn = await asyncpg.connect(**self._db_config)
        try:
            async with conn.transaction():
                chat_repo = ChatRepository(conn)
                batch_repo = AwardBatchRepository(conn)

                # Получаем текущий период (номер недели)
                period_key = self._get_current_period_key()
                logger.info(f"Создание batch для периода {period_key}")

                # Получаем все активные чаты
                chats = await chat_repo.list_active_chats()

                created_count = 0
                for chat in chats:
                    chat_id = chat["chat_id"]
                    is_award_enabled = chat.get("is_award_enabled", False)

                    # Пропускаем чаты где зачисления отключены
                    if not is_award_enabled:
                        logger.debug(f"Чат {chat_id}: зачисления отключены")
                        continue

                    # Создаём или получаем batch
                    batch = await batch_repo.create_or_get_batch(
                        chat_id=chat_id,
                        period_key=period_key,
                    )

                    if batch.status == "pending":
                        created_count += 1
                        logger.info(f"Создан batch {batch.id} для чата {chat_id}, период {period_key}")
                    else:
                        logger.debug(f"Batch для чата {chat_id}, период {period_key} уже существует (status={batch.status})")

                logger.info(
                    f"Создано {created_count} batch из {len(chats)} активных чатов "
                    f"для периода {period_key}"
                )

                return created_count
        finally:
            await conn.close()

    @staticmethod
    def _get_current_period_key() -> str:
        """
        Получить ключ текущего периода.

        Формат: "YYYY-Www" (ISO неделя)
        Например: "2026-W09"

        Returns:
            Строка периода
        """
        now = datetime.now(UTC)
        iso_calendar = now.isocalendar()
        return f"{iso_calendar.year}-W{iso_calendar.week:02d}"
