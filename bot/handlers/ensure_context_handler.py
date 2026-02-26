from telegram import Update
from telegram.ext import (
    ContextTypes,
    filters,
)

from bot.handlers.middleware.ensure_context import ensure_context

# Фильтр для пропуска служебных сообщений о членстве в чате
MEMBERSHIP_FILTERS = filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER


async def ensure_context_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик для обеспечения контекста (user, chat, chat_user).

    Пропускает служебные сообщения (новый участник, выход участника)
    """
    msg = update.message
    if not msg:
        return

    # Пропускаем служебные сообщения о членстве — для них есть отдельные обработчики
    if MEMBERSHIP_FILTERS.check_update(update):
        return

    await ensure_context(
        update=update,
        context=context
    )
