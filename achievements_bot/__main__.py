from achievements_bot.services.logger import logger

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters, MessageReactionHandler,
)

from achievements_bot import config, handlers
from achievements_bot.db import close_db

COMMAND_HANDLERS = {
    "start": handlers.start,
    "help": handlers.help_,
    "get_stats": handlers.get_stats,
    "get_my_stats": handlers.get_user_stats,
}

if not config.BOT_TOKEN or not config.TARGET_CHANNEL_ID:
    raise ValueError(
        "BOT_TOKEN and TARGET_CHANNEL_ID should be initialized in config.py"
    )


def main():
    logger.info('Bot started')
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    for command_name, command_handler in COMMAND_HANDLERS.items():
        application.add_handler(CommandHandler(command_name, command_handler))

    application.add_handler(MessageHandler(filters.ALL, handlers.all_messages))
    logger.info('Handlers enabled')
    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        logger.warning(traceback.format_exc())
    finally:
        close_db()
