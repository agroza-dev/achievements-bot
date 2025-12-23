from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import logger


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    user_id = update.effective_user.id if update and update.effective_user else "unknown"

    logger.error(f"Unexpected error for user {user_id}: {error}", exc_info=True)
    if update and update.message:
        await update.message.reply_text(
            "Произошла неизвестная ошибка. Пожалуйста, попробуйте позже."
        )
