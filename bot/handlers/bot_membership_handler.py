import logging

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from core.container import Container

logger = logging.getLogger(__name__)


async def bot_membership_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    logger.info(f"Received bot_membership_handler message: {message}")
    if not message or not message.new_chat_members:
        return

    bot_id = context.bot.id

    if not any(m.id == bot_id for m in message.new_chat_members):
        return

    container: Container = context.bot_data["container"]
    use_case = container.get_bot_added_to_chat_use_case()
    bots = [user for user in message.new_chat_members if user.is_bot]

    logger.debug(f"Chat {message.chat}")
    logger.debug(f"From user {message.from_user}")
    logger.debug(f"Bots {bots}")

    for bot in bots:
        await use_case.execute(
            tg_chat=message.chat,
            bot=bot,
            added_by=message.from_user,
        )
        is_super_group = message.chat.type == ChatType.SUPERGROUP
        # TODO Тут нужно написать нормальное сообщение чтобы было понятно, что:
        # TODO Функции бота работают только если группа является супер группой и бот является админом в группе

        # TODO Также нужно пометить как админа пользователя, который бота в группу добавил.
        await update.message.reply_text('Бот добавлен. Для корректной работы всех функций ')
        logger.info(
            f"Bot added to chat {message.chat.title} by {message.from_user.username}",
            extra={
                "tg_chat_id": message.chat.id,
                "added_by": message.from_user.id if message.from_user else None,
            }
        )
