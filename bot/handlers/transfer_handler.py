import logging

from telegram import Message, Update
from telegram.constants import ReactionEmoji
from telegram.error import Forbidden, TelegramError
from telegram.ext import ContextTypes

from core.application.transfers.transfer_result import TransferStatus
from core.container import Container
from core.dto.bot_context import BotContextDTO
from core.dto.transfer_dto import TransferCommandDTO
from core.ports.bot_gateway import BotGateway
from utils.logger import prettify

logger = logging.getLogger(__name__)

# Текст подсказки об управлении уведомлениями
NOTIFICATIONS_HINT = "\n\nℹ️ Выкл уведомления: /notifications off"


async def _get_user_notifications_enabled(container: Container, user_id: int, tg_id: int) -> bool:
    """Проверяет, включены ли уведомления для пользователя."""
    try:
        logger.info(f"[SETTINGS] Checking notifications settings for user_id={user_id}, tg_id={tg_id}")
        use_case = container.get_user_settings_use_case()
        logger.info(f"[SETTINGS] Got use_case, calling execute for user_id={user_id}")
        settings = await use_case.execute(user_id=user_id)
        logger.info(f"[SETTINGS] Got settings for user_id={user_id}: enabled={settings.notifications.enabled}")
        return settings.notifications.enabled
    except Exception as e:
        logger.exception(f"[SETTINGS] Failed to get user settings for user_id={user_id}, tg_id={tg_id}: {e}")
        # По умолчанию уведомления включены
        return True


async def _send_notification(
    bot_gateway: BotGateway,
    container: Container,
    ctx: BotContextDTO,
    text: str,
    notification_type: str,
) -> None:
    """
    Отправить уведомление пользователю.

    Если уведомления выключены, сообщение не отправляется.
    """
    logger.info(f"[NOTIFICATION] Start sending {notification_type} to user_id={ctx.user.id}, tg_id={ctx.user.tg_id}")

    # Проверяем настройки уведомлений
    logger.info(f"[NOTIFICATION] Calling _get_user_notifications_enabled for user_id={ctx.user.id}")
    notifications_enabled = await _get_user_notifications_enabled(
        container, ctx.user.id, ctx.user.tg_id
    )
    logger.info(f"[NOTIFICATION] Got notifications_enabled={notifications_enabled} for user_id={ctx.user.id}")

    logger.info(
        f"Sending {notification_type} transfer notification to user_id={ctx.user.id}, "
        f"tg_id={ctx.user.tg_id}, notifications_enabled={notifications_enabled}"
    )

    # Если уведомления выключены, не отправляем сообщение вообще
    if not notifications_enabled:
        logger.info(
            f"[NOTIFICATION] Skipping {notification_type} notification for user_id={ctx.user.id}, "
            f"tg_id={ctx.user.tg_id} - notifications disabled"
        )
        return

    logger.info(f"[NOTIFICATION] notifications_enabled={notifications_enabled}, proceeding to send message")

    try:
        logger.info(f"[NOTIFICATION] Calling bot_gateway.send_message for {notification_type}")
        await bot_gateway.send_message(
            chat_id=ctx.user.tg_id,
            text=text,
        )
        logger.info(
            f"[NOTIFICATION] Successfully sent {notification_type} notification to user_id={ctx.user.id}, "
            f"tg_id={ctx.user.tg_id}"
        )
    except Forbidden:
        logger.warning(
            f"[NOTIFICATION] Bot is forbidden to send {notification_type} notification to "
            f"user_id={ctx.user.id}, tg_id={ctx.user.tg_id}"
        )
    except TelegramError as e:
        logger.error(
            f"[NOTIFICATION] Failed to send {notification_type} notification to "
            f"user_id={ctx.user.id}, tg_id={ctx.user.tg_id}: {e}"
        )


async def transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Читаем контекст из chat_data по user_id
    user = update.effective_user
    user_id = user.id if user else None
    user_contexts = context.chat_data.get('user_contexts', {})
    ctx: BotContextDTO | None = user_contexts.get(user_id) if user_id else None

    logger.info("Received update (message_id=%s, chat=%s, from=%s)",
                update.message.message_id if update.message else None,
                update.effective_chat.title if update.effective_chat else None,
                update.effective_user.username if update.effective_user else None)

    # Логируем контекст для отладки
    if ctx:
        logger.info(f"Bot context resolved: user.id={ctx.user.id}, user.tg_id={ctx.user.tg_id}, "
                    f"user.username={ctx.user.username}, chat.id={ctx.chat.id}")
    else:
        logger.warning(f"Bot context is None for user_id={user_id}")

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

    # Получаем BotGateway из контейнера
    bot_gateway: BotGateway = container.get_bot_gateway()

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
    logger.debug("Transfer command:\n%s", prettify(command))
    use_case = container.get_transfer_points_use_case()
    transfer_result = await use_case.execute(command)
    logger.debug("Transfer result:\n%s", prettify(transfer_result))
    if transfer_result.status is TransferStatus.SUCCESS:
        await bot_gateway.set_message_reaction(
            message.chat_id, message.message_id, reaction=ReactionEmoji.WRITING_HAND
        )
        recipient_display = f"@{transfer_result.recipient_username}" if transfer_result.recipient_username else "пользователю"
        total_deducted = (transfer_result.amount or 0) + (transfer_result.tax or 0)

        await _send_notification(
            bot_gateway=bot_gateway,
            container=container,
            ctx=ctx,
            text=(
                f"✅ Трансфер успешно выполнен!\n\n"
                f"Получатель: {recipient_display}\n"
                f"Сумма трансфера: {transfer_result.amount or 0}\n"
                f"Налог: {transfer_result.tax or 0}\n"
                f"Всего списано: {total_deducted}\n"
                f"Ваш баланс: {transfer_result.initiator_balance or 0}"
                f"{NOTIFICATIONS_HINT}"
            ),
            notification_type="SUCCESS",
        )

    elif transfer_result.status is TransferStatus.FORBIDDEN:
        await bot_gateway.set_message_reaction(message.chat_id, message.message_id, reaction=ReactionEmoji.CLOWN_FACE)

        await _send_notification(
            bot_gateway=bot_gateway,
            container=container,
            ctx=ctx,
            text=transfer_result.message or "Запрещённое действие",
            notification_type="FORBIDDEN",
        )

    elif transfer_result.status is TransferStatus.INSUFFICIENT_FUNDS:
        await bot_gateway.set_message_reaction(
            message.chat_id, message.message_id, reaction=ReactionEmoji.PILL
        )
        recipient_display = f"@{transfer_result.recipient_username}" if transfer_result.recipient_username else "пользователю"
        missing = (transfer_result.required_amount or 0) - (transfer_result.initiator_balance or 0)

        await _send_notification(
            bot_gateway=bot_gateway,
            container=container,
            ctx=ctx,
            text=(
                f"❌ Недостаточный баланс для трансфера\n\n"
                f"Получатель: {recipient_display}\n"
                f"Требуется: {transfer_result.required_amount or 0}\n"
                f"Включая налог: {transfer_result.tax or 0}\n"
                f"Ваш текущий баланс: {transfer_result.initiator_balance or 0}\n"
                f"Не хватает: {missing}"
                f"{NOTIFICATIONS_HINT}"
            ),
            notification_type="INSUFFICIENT_FUNDS",
        )

    elif transfer_result.status is TransferStatus.QUIET_STOP:
        logger.debug("Transfer is not processable. Just ignored")
        # Не каждое сообщение должно быть трансфером.
        # Если трансфер не нашли, значит его там нет и не нужно его никак в этом handler обрабатывать

    elif transfer_result.status is TransferStatus.NOT_FOUND:
        logger.debug("Transfer not found in message. Just ignored")
        # Не каждое сообщение должно быть трансфером.
        # Если трансфер не нашли, значит его там нети не нужно его никак в этом handler обрабатывать
        pass

    elif transfer_result.status is TransferStatus.INVALID:
        await bot_gateway.set_message_reaction(
            message.chat_id, message.message_id, reaction=ReactionEmoji.CLOWN_FACE
        )

        await _send_notification(
            bot_gateway=bot_gateway,
            container=container,
            ctx=ctx,
            text="Неверный формат трансфера",
            notification_type="INVALID",
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
