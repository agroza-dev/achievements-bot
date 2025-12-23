import httpx
from telegram.ext import ApplicationBuilder, CommandHandler, MessageReactionHandler, PicklePersistence
from telegram.request import HTTPXRequest

from bot.handlers.error_handler import error_handler
from bot.handlers.reaction_handler import reaction_handler
from bot.handlers.start_handler import start_handler
from core.config import settings

if __name__ == "__main__":
    request = HTTPXRequest(
        httpx_kwargs={
            "timeout": httpx.Timeout(
                connect = settings.bot.builder.get('connect'),
                read = settings.bot.builder.get('read'),
                write = settings.bot.builder.get('write'),
                pool = settings.bot.builder.get('pool'),
            )
        }
    )

    persistence = PicklePersistence(filepath=settings.bot.persistence)

    application = (ApplicationBuilder()
                   .token(settings.bot.token)
                   .request(request)
                   .persistence(persistence)
                   .build()
    )

    # Добавляем обработчик реакций до обработчика команд, чтобы проверить срабатывание
    application.add_handler(MessageReactionHandler(reaction_handler))
    application.add_handler(CommandHandler("start", start_handler))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run polling with all allowed updates including message reactions
    application.run_polling(allowed_updates=["message", "message_reaction", "message_reaction_count", "inline_query", "chosen_inline_result", "callback_query", "poll", "poll_answer"])
