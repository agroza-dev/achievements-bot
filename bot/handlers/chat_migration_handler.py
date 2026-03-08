import logging

from telegram import Chat, Update
from telegram.ext import ContextTypes

from core.container import Container

logger = logging.getLogger(__name__)


async def chat_migration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик события миграции чата (группа -> супергруппа).

    При конвертации группы в супергруппу Telegram меняет идентификатор чата.
    Этот handler обновляет tg_id в базе данных для сохранения преемственности.

    Telegram отправляет два сообщения при миграции:
    1. В старую группу: migrate_to_chat_id=<новый_id>
    2. В новую супергруппу: migrate_from_chat_id=<старый_id>

    Обрабатываем оба случая.
    """
    message = update.message
    logger.info(f"Received chat_migration_handler message: {message}")

    if not message:
        return

    container: Container = context.bot_data.get("container")
    if not container:
        logger.error("Container not found in bot_data")
        return

    use_case = container.get_migrate_chat_use_case()

    # Случай 1: Сообщение из старой группы (migrate_to_chat_id)
    if message.migrate_to_chat_id:
        old_chat = message.chat
        new_chat_id = message.migrate_to_chat_id

        new_chat = Chat(
            id=new_chat_id,
            type="supergroup",
            title=old_chat.title,
            username=old_chat.username,
        )

        logger.info(
            f"Миграция (migrate_to_chat_id): {old_chat.id} -> {new_chat_id}",
            extra={"old_chat_id": old_chat.id, "new_chat_id": new_chat_id}
        )

        await use_case.execute(
            old_chat=old_chat,
            new_chat=new_chat,
        )
        return

    # Случай 2: Сообщение из новой супергруппы (migrate_from_chat_id)
    if message.migrate_from_chat_id:
        old_chat_id = message.migrate_from_chat_id
        new_chat = message.chat

        old_chat = Chat(
            id=old_chat_id,
            type="group",
            title=new_chat.title,
            username=new_chat.username,
        )

        logger.info(
            f"Миграция (migrate_from_chat_id): {old_chat_id} -> {new_chat.id}",
            extra={"old_chat_id": old_chat_id, "new_chat_id": new_chat.id}
        )

        await use_case.execute(
            old_chat=old_chat,
            new_chat=new_chat,
        )
        return
