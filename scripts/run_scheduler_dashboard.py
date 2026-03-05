"""
Запуск FastAPI Dashboard для мониторинга планировщика задач.

Dashboard доступен по адресу: http://localhost:8000/scheduler/
"""

import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastscheduler import FastScheduler
from fastscheduler.fastapi_integration import create_scheduler_routes

from core.config import ProjectPaths, settings
from core.infrastructure.database import DatabaseManager
from core.infrastructure.scheduler import BonusScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Запустить планировщик и FastAPI dashboard."""

    # Создаём все необходимые директории
    ProjectPaths.ensure_dirs()

    # Инициализация БД
    db_manager = DatabaseManager()
    await db_manager.init_pool()

    # Создание планировщика
    scheduler = FastScheduler(
        quiet=False,  # quiet=False для логирования
        state_file=settings.scheduler.state_file,
    )
    bonus_scheduler = BonusScheduler(
        scheduler=scheduler,
        db_manager=db_manager,
    )

    # Синхронизация задач
    await bonus_scheduler.sync_chat_jobs()

    # Запуск планировщика
    bonus_scheduler.start()

    # Создание FastAPI приложения
    app = FastAPI(
        title="Achievements Bot Scheduler",
        description="Dashboard для мониторинга планировщика периодических бонусов",
        version="1.0.0",
    )

    # Добавление роутов для дашборда
    app.include_router(create_scheduler_routes(scheduler))

    logger.info("=" * 60)
    logger.info("🚀 Scheduler Dashboard запущен!")
    logger.info("📊 Dashboard: http://localhost:8000/scheduler/")
    logger.info("📋 API docs: http://localhost:8000/docs")
    logger.info("=" * 60)

    # Запуск uvicorn
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Остановка дашборда...")
    finally:
        # Остановка планировщика
        bonus_scheduler.stop()
        await db_manager.close_pool()
        logger.info("Дашборд остановлен")


if __name__ == "__main__":
    asyncio.run(main())
