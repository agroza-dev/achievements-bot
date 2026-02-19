import logging

from telegram import Message, Update
from telegram.constants import ReactionEmoji
from telegram.ext import ContextTypes

from core.application.transfers.transfer_result import TransferStatus
from core.container import Container
from core.dto.bot_context import BotContextDTO
from core.dto.transfer_dto import TransferCommandDTO

logger = logging.getLogger(__name__)


async def transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Читаем контекст из chat_data по user_id
    user = update.effective_user
    user_id = user.id if user else None
    user_contexts = context.chat_data.get('user_contexts', {})
    ctx: BotContextDTO | None = user_contexts.get(user_id) if user_id else None

    logger.info("Received update: %s", update)

    chat = update.effective_chat
    if chat.type == "private":
        logger.debug("Skipped counting metadata for private chat")
        return

    if not ctx:
        logger.error("Bot context not found in transfer handler")
        return

    # Получаем контейнер из application context
    container: Container = context.bot_data.get("container")
    if not container:
        logger.error("Container not initialized.")
        raise RuntimeError("Container not initialized. Ensure container is set in bot_data during startup.")

    message: Message = update.message
    if not message or not message.text:
        logger.error("Message not found in transfer handler")
        return

    mentioned_usernames = extract_mentions(message)

    command = TransferCommandDTO(
        initiator_user_id=ctx.user.id,
        chat_id=ctx.chat.id,
        raw_text=message.text,
        reply_to_message_id=(message.reply_to_message.message_id if message.reply_to_message else None),
        mentioned_usernames=mentioned_usernames,
    )
    logger.debug("Transfer command: %s", command)
    use_case = container.get_transfer_points_use_case()
    transfer_result = await use_case.execute(command)
    logger.debug("Transfer result: %s", transfer_result)
    if transfer_result.status is TransferStatus.SUCCESS:
        await context.bot.setMessageReaction(
            message.chat_id, message.message_id, reaction=[ReactionEmoji.WRITING_HAND]
        )
        await context.bot.send_message(
            chat_id=command.initiator_user_id,
            text="Трансфер успешно выполнен 👍",
        )

    elif transfer_result.status is TransferStatus.FORBIDDEN:
        await context.bot.setMessageReaction(message.chat_id, message.message_id, reaction=ReactionEmoji.CLOWN_FACE)
        await context.bot.send_message(
            chat_id=command.initiator_user_id,
            text=transfer_result.message or "Запрещённое действие",
        )

    elif transfer_result.status is TransferStatus.INSUFFICIENT_FUNDS:
        await context.bot.setMessageReaction(
            message.chat_id, message.message_id, reaction=ReactionEmoji.PILL
        )
        await context.bot.send_message(
            chat_id=command.initiator_user_id,
            text="Недостаточно очков для трансфера",
        )

    elif transfer_result.status is TransferStatus.QUIET_STOP:
        await context.bot.setMessageReaction(
            message.chat_id, message.message_id, reaction=ReactionEmoji.CLOWN_FACE
        )
        await context.bot.send_message(
            chat_id=command.initiator_user_id,
            text="❌ Получатель не найден. Упомяните пользователя @username или ответьте на его сообщение",
        )

    elif transfer_result.status is TransferStatus.NOT_FOUND:
        await context.bot.setMessageReaction(
            message.chat_id, message.message_id, reaction=ReactionEmoji.CLOWN_FACE
        )
        await context.bot.send_message(
            chat_id=command.initiator_user_id,
            text="Трансфер не найден. Возможно, вы не указали получателя?",
        )

    elif transfer_result.status is TransferStatus.INVALID:
        await context.bot.setMessageReaction(
            message.chat_id, message.message_id, reaction=ReactionEmoji.CLOWN_FACE
        )
        await context.bot.send_message(
            chat_id=command.initiator_user_id,
            text="Неверный формат трансфера",
        )


def extract_mentions(message: Message) -> list[str]:
    """Извлекает упоминания из entities"""
    mentions = []
    entities = (message.entities or ()) + (message.caption_entities or ())
    for entity in entities:
        if entity.type == "mention":
            mentions.append(message.text[entity.offset:entity.offset + entity.length])
        else:
            logger.warning("Unsupported entity type: %s", entity.type)
            logger.info(entity)
    return mentions
