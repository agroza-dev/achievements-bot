"""Middleware для обеспечения контекста бота."""
import logging

from telegram import Chat, Update, User
from telegram.ext import CallbackContext

from core.container import Container

logger = logging.getLogger(__name__)


async def ensure_context(update: Update, context: CallbackContext):
    """
    Обеспечить контекст бота (user, chat, chat_user) в одной транзакции.

    Args:
        update: Telegram update объект
        context: Контекст обработчика бота
    """
    user: User = update.effective_user
    chat: Chat = update.effective_chat

    if not user or not chat:
        return

    # Получаем контейнер из application context
    container: Container = context.bot_data.get('container')
    if not container:
        raise RuntimeError("Container not initialized. Ensure container is set in bot_data during startup.")
    logger.debug(f"User: {user.username}, chat: {chat.title}, chat_id: {chat.id}")
    # Используем объединенный use case для выполнения всех операций в одной транзакции
    ensure_context_use_case = container.get_ensure_context_use_case()
    bot_context = await ensure_context_use_case.execute(tg_user=user, tg_chat=chat)
    logger.debug(bot_context)
    context.bot_data['ctx'] = bot_context
