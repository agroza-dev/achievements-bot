"""Главный модуль для запуска Telegram бота."""

import httpx
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    MessageReactionHandler,
    PicklePersistence,
    filters,
)
from telegram.request import HTTPXRequest

from bot.handlers.bot_membership_handler import bot_membership_handler
from bot.handlers.ensure_context_handler import ensure_context_handler
from bot.handlers.ensure_context_reaction_handler import ensure_context_reaction_handler
from bot.handlers.error_handler import error_handler
from bot.handlers.message_metadata_handler import message_metadata_handler
from bot.handlers.reaction_handler import reaction_handler
from bot.handlers.start_handler import start_handler
from bot.handlers.transfer_handler import transfer_handler
from core.config import settings
from core.container import Container
from core.infrastructure.database import DatabaseManager
from utils import trace_logger
from utils.logger import logger


async def on_startup(application):
    trace_logger.get_logger(__name__)
    """Инициализация при старте бота."""
    logger.info("Bot startup")

    # Инициализируем менеджер базы данных
    db_manager = DatabaseManager()
    await db_manager.init_pool()

    # Создаем DI контейнер с инициализированным менеджером БД
    container = Container(db_manager)

    # Сохраняем контейнер в application context для использования в handlers
    application.bot_data['container'] = container
    application.bot_data['db_manager'] = db_manager  # Для обратной совместимости, если нужно

    logger.info("Container initialized and ready")


async def on_shutdown(application):
    """Очистка при остановке бота."""
    logger.info("Bot shutdown")

    # Закрываем пул подключений к БД
    db_manager: DatabaseManager = application.bot_data.get('db_manager')
    if db_manager:
        await db_manager.close_pool()

    logger.info("Database pool closed")


def main():
    request = HTTPXRequest(
        httpx_kwargs={
            "timeout": httpx.Timeout(
                connect=settings.bot.builder.get("connect"),
                read=settings.bot.builder.get("read"),
                write=settings.bot.builder.get("write"),
                pool=settings.bot.builder.get("pool"),
            )
        }
    )

    persistence = PicklePersistence(
        filepath=settings.bot.persistence,
    )

    application = (
        ApplicationBuilder()
        .token(settings.bot.token)
        .request(request)
        .persistence(persistence)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_membership_handler),
        group=0,
    )
    # Handlers
    application.add_handler(
        MessageHandler(filters.ALL, ensure_context_handler),
        group=0
    )

    application.add_handler(
        MessageReactionHandler(ensure_context_reaction_handler),
        group=0
    )

    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.UpdateType.EDITED_MESSAGE,
            message_metadata_handler,
        ),
        group=1,
    )

    application.add_handler(MessageReactionHandler(reaction_handler), group=2)
    application.add_handler(CommandHandler("start", start_handler), group=2)

    application.add_handler(MessageHandler(filters.TEXT, transfer_handler), group=3)

    # Error handler
    application.add_error_handler(error_handler)

    application.run_polling(
        allowed_updates=[
            "message",
            "message_reaction",
            "message_reaction_count",
            "inline_query",
            "chosen_inline_result",
            "callback_query",
            "poll",
            "poll_answer",
        ]
    )


if __name__ == "__main__":
    main()
