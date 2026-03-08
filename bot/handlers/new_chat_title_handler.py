import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.container import Container

logger = logging.getLogger(__name__)


async def new_chat_title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик события изменения названия чата.

    При изменении названия чата обновляет название в базе данных.
    """
    message = update.message
    logger.info(f"Received new_chat_title_handler message: {message}")

    if not message:
        return

    # Проверяем наличие поля new_chat_title
    if not message.new_chat_title:
        return

    container: Container = context.bot_data.get("container")
    if not container:
        logger.error("Container not found in bot_data")
        return

    use_case = container.get_update_chat_title_use_case()

    await use_case.execute(tg_chat=message.chat)
