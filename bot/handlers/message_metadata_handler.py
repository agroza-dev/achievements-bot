"""Handler для обработки метаданных сообщений."""
import logging

from telegram import Message, MessageOrigin, Update
from telegram.ext import ContextTypes

from core.container import Container
from core.dto.bot_context import BotContextDTO
from core.dto.chat_message_create_dto import ChatMessageCreateDTO

logger = logging.getLogger(__name__)

async def message_metadata_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработать метаданные сообщения и сохранить в базу данных.

    Args:
        update: Telegram update объект
        context: Контекст обработчика бота
    """
    # Читаем контекст из chat_data по user_id
    user = update.effective_user
    user_id = user.id if user else None
    user_contexts = context.chat_data.get('user_contexts', {})
    ctx: BotContextDTO | None = user_contexts.get(user_id) if user_id else None

    chat = update.effective_chat
    if chat.type == "private":
        logger.debug('Skipped counting metadata for private chat')
        return

    if not ctx:
        logger.error("Bot context not found in message_metadata_handler")
        return

    message: Message = update.message

    message_kind, message_meta = parse_message(message)

    message_dto = ChatMessageCreateDTO(
        chat_id=ctx.chat.id,
        tg_message_id=message.message_id,
        author_user_id=ctx.user.id if ctx.user else None,
        message_type=message_kind,
        message_meta=message_meta,
        created_at=message.date,
    )

    # Получаем контейнер из application context
    container: Container = context.bot_data.get('container')
    if not container:
        raise RuntimeError("Container not initialized. Ensure container is set in bot_data during startup.")

    # Получаем use case из контейнера
    use_case = container.get_process_message_use_case()

    await use_case.execute(ctx=ctx, message_dto=message_dto)


def _get_message_kind(message: Message) -> str:
    """
    Возвращает нормализованный тип сообщения.
    Используется для message_kind в БД.
    """

    # 1. Системные события
    if message.left_chat_member:
        return "left_chat_member"

    if message.new_chat_members:
        return "new_chat_member" # TODO не логировать или вынести в отдельный use-case

    # 2. Forward / repost
    if message.forward_origin:
        return "forward"

    # 3. Reply / quote
    if message.reply_to_message:
        return "reply"

    # 4. Контент
    if message.text:
        return "text"

    if message.sticker:
        return "sticker"

    if message.photo:
        return "photo"

    if message.video:
        return "video"

    if message.voice:
        return "voice"

    if message.audio:
        return "audio"

    if message.animation:
        return "animation"

    if message.document:
        return "document"

    if message.poll:
        return "poll"

    if message.contact:
        return "contact"

    if message.location:
        return "location"

    if message.venue:
        return "venue"

    # 5. Fallback
    return "unknown" # TODO - нужно отслеживать событие, когда группа превращается в супер группу, чтобы не терять связь

def _detect_media_type(message: Message) -> str:
    if message.photo:
        return "photo"
    if message.video:
        return "video"
    if message.audio:
        return "audio"
    if message.voice:
        return "voice"
    if message.document:
        return "document"
    if message.animation:
        return "animation"
    return "unknown"

def _extract_mentions(message: Message) -> list[dict]:
    """
    Извлекает упоминания пользователей из message.entities и caption_entities.

    Возвращает список словарей, пригодных для сохранения в message_meta.
    """
    mentions: list[dict] = []

    entities = (message.entities or ()) + (message.caption_entities or ())

    for entity in entities:
        # text_mention — единственный надежный вариант
        # где Telegram дает реального User
        if entity.type == "text_mention" and entity.user:
            mentions.append({
                "user_id": entity.user.id,
                "type": "text_mention",
            })

    return mentions

def parse_message(message: Message) -> tuple[str, dict]:
    message_kind = _get_message_kind(message)
    meta: dict = {}

    mentions = _extract_mentions(message)
    if mentions:
        return "mentions", {"list": mentions}

    if message.forward_origin:
        fo: MessageOrigin = message.forward_origin
        source = fo.type.lower()

        # Initialize both from_chat and from_user as None
        from_chat = None
        from_user = None

        # Handle each MessageOrigin type appropriately
        if hasattr(fo, 'chat') and fo.chat:  # MessageOriginChannel
            from_chat = {
                "id": fo.chat.id,
                "title": getattr(fo.chat, 'title', None),
                "username=": getattr(fo.chat, 'username', None),
            }
        elif hasattr(fo, 'sender_chat') and fo.sender_chat:  # MessageOriginChat
            from_chat = {
                "id": fo.sender_chat.id,
                "title": getattr(fo.sender_chat, 'title', None),
            }

        if hasattr(fo, 'sender_user') and fo.sender_user:  # MessageOriginUser
            from_user = {
                "id": fo.sender_user.id,
                "username": getattr(fo.sender_user, 'username', None),
            }
        elif hasattr(fo, 'sender_user_name'):  # MessageOriginHiddenUser
            from_user = {
                "name": fo.sender_user_name,
            }

        return "forward", {
            "source": source,
            "from_chat": from_chat,
            "from_user": from_user,
        }

    if message.quote:
        return "quote", {
            "quoted_text": message.quote.text,
            "quoted_message_id": (message.reply_to_message.message_id if message.reply_to_message else None),
        }

    if message.sticker:
        return "sticker", {
            "sticker_file_id": message.sticker.file_id,
            "sticker_set_name": message.sticker.set_name,
            "is_animated": message.sticker.is_animated,
            "is_video": message.sticker.is_video,
            "emoji": message.sticker.emoji,
        }

    if any(
        [
            message.photo,
            message.video,
            message.audio,
            message.voice,
            message.document,
            message.animation,
        ]
    ):
        return "media", {
            "has_caption": bool(message.caption),
            "caption_length": len(message.caption) if message.caption else None,
            "media_type": _detect_media_type(message),
        }

    if message.poll:
        return "poll", {
            "poll_id": message.poll.id,
            "is_anonymous": message.poll.is_anonymous,
            "type": message.poll.type,
        }

    if message.text:
        return "text", {
            "length": len(message.text),
        }

    return message_kind, meta
