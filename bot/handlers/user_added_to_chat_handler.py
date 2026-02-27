import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.container import Container

logger = logging.getLogger(__name__)


async def user_added_to_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик добавления обычных пользователей в чат.

    Начисляет приветственный бонус каждому пользователю при ПЕРВОМ добавлении в чат.
    """
    message = update.message
    logger.info(f"Received user_added_to_chat_handler message: {message}")

    if not message or not message.new_chat_members:
        return

    container: Container = context.bot_data["container"]

    # Фильтруем только обычных пользователей (не ботов)
    users_to_add = [m for m in message.new_chat_members if not m.is_bot]

    if not users_to_add:
        return

    use_case = container.get_user_added_to_chat_use_case()

    # Обрабатываем каждого добавленного пользователя
    for tg_user in users_to_add:
        await use_case.execute(
            tg_chat=message.chat,
            tg_user=tg_user,
            added_by=message.from_user,
        )
