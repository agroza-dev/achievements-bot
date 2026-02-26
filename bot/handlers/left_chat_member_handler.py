import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.container import Container

logger = logging.getLogger(__name__)


async def left_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик события left_chat_member.

    Обрабатывает случаи, когда:
    - Пользователь сам покидает чат
    - Пользователя удаляют из чата
    - Бота удаляют из чата (деактивация чата)
    """
    message = update.message
    logger.info(f"Received left_chat_member event: {message}")

    if not message or not message.left_chat_member:
        return

    container: Container = context.bot_data["container"]
    bot_id = context.bot.id
    left_member = message.left_chat_member

    # Проверяем, не бот ли это
    if left_member.id == bot_id:
        # Бот удалён из чата — деактивируем чат
        await _handle_bot_removed(update, context, container)
        return

    # Обычный пользователь покидает чат
    use_case = container.get_user_left_chat_use_case()
    await use_case.execute(
        tg_chat=message.chat,
        user=left_member,
    )


async def _handle_bot_removed(update: Update, context: ContextTypes.DEFAULT_TYPE, container: Container):
    """
    Обработать удаление бота из чата.

    Деактивирует чат и сохраняет метаданные о причине.
    """
    message = update.message
    chat = message.chat

    # Получаем use case для деактивации чата
    from core.application.chat_lifecycle.deactivate_chat import DeactivateChatUseCase
    use_case = DeactivateChatUseCase(container.get_uow_factory())

    await use_case.execute(
        tg_chat=chat,
        reason="bot_removed",
    )

    logger.info(
        f"Bot removed from chat {chat.title} (id={chat.id})",
        extra={
            "tg_chat_id": chat.id,
            "removed_by": message.from_user.id if message.from_user else None,
        }
    )
