import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    MessageReactionHandler,
    PicklePersistence,
    filters,
)
from telegram.request import HTTPXRequest

from bot.handlers.ensure_context_handler import ensure_context_handler
from bot.handlers.ensure_context_reaction_handler import ensure_context_reaction_handler
from bot.handlers.error_handler import error_handler
from bot.handlers.reaction_handler import reaction_handler
from bot.handlers.start_handler import start_handler
from core.config import settings
from core.database import db_manager
from utils.logger import logger


async def on_startup(application):
    logger.info("Bot startup")
    await db_manager.init_pool()


async def on_shutdown(application):
    logger.info("Bot shutdown")
    await db_manager.close_pool()


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

    # Handlers
    application.add_handler(
        MessageHandler(filters.ALL, ensure_context_handler),
        group=0
    )

    application.add_handler(
        MessageReactionHandler(ensure_context_reaction_handler),
        group=0
    )

    application.add_handler(MessageReactionHandler(reaction_handler), group=1)
    application.add_handler(CommandHandler("start", start_handler), group=1)

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
