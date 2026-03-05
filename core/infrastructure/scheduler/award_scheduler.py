"""
Планировщик задач для периодических зачислений.

Архитектура:
- Producer: создаёт batch по расписанию (cron)
- Worker: постоянный цикл обработки batch

Надёжность:
- Idempotency через Ledger (UNIQUE(user_id, operation_type, operation_key))
- Resume через cursor_user_id в batch
- Crash-safe: при падении batch остаётся processing и продолжается
"""

import logging

from fastscheduler import FastScheduler

from core.config import periodic_award_config
from core.infrastructure.scheduler.award_producer import AwardProducer
from core.infrastructure.scheduler.award_worker import AwardWorker

logger = logging.getLogger(__name__)


class AwardScheduler:
    """
    Планировщик для периодических зачислений.

    Состоит из:
    - Producer: создаёт batch раз в неделю по cron
    - Worker: постоянный цикл обработки batch
    """

    def __init__(
        self,
        scheduler: FastScheduler,
        db_manager,
    ):
        self.scheduler = scheduler
        self.db_manager = db_manager
        self.producer = AwardProducer(db_manager)
        self.worker = AwardWorker(db_manager)
        self._job_id: str | None = None

    async def create_producer_job(self) -> None:
        """
        Создать cron-задачу для producer.

        Вызывается один раз при старте бота.
        """
        cron_expr = periodic_award_config.CRON_EXPRESSION
        timezone = periodic_award_config.TIMEZONE

        async def run_producer():
            """Запустить producer для создания batch."""
            try:
                logger.info(f"Запуск producer для создания batch (cron: {cron_expr})")
                await self.producer.create_batches()
                logger.info("Producer завершил создание batch")
            except Exception as e:
                logger.error(f"Ошибка в producer: {e}", exc_info=True)
                raise

        # Регистрируем cron-задачу
        self.scheduler.cron(cron_expr).tz(timezone)(run_producer)
        self._job_id = "award_producer"
        logger.info(f"Создана задача producer: cron={cron_expr}, tz={timezone}")

    async def start(self) -> None:
        """
        Запустить scheduler и worker.

        Вызывается при старте бота.
        """
        # Создаём cron-задачу для producer
        await self.create_producer_job()

        # Запускаем scheduler
        logger.info("Запуск планировщика")
        self.scheduler.start()

        # Запускаем worker
        await self.worker.start()

    async def stop(self) -> None:
        """
        Остановить scheduler и worker.

        Вызывается при остановке бота.
        """
        logger.info("Остановка планировщика и worker")

        # Останавливаем worker
        await self.worker.stop()

        # Останавливаем scheduler
        self.scheduler.stop()
