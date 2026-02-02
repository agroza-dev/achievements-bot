import logging
import traceback
import uuid

from telegram import Update
from telegram.error import (
    BadRequest,
    Forbidden,
    NetworkError,
    TimedOut,
)
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    """Ошибки бизнес-логики, которые можно показывать пользователю."""
    pass


async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    request_id = str(uuid.uuid4())[:8]

    # Универсальные данные (работают для message / callback / reaction)
    user_id = update.effective_user.id if update and update.effective_user else None
    chat_id = update.effective_chat.id if update and update.effective_chat else None
    update_type = type(update).__name__ if update else "None"

    # ---------- ОЖИДАЕМЫЕ ОШИБКИ TELEGRAM API ----------
    match error:
        case Forbidden():
            logger.warning(
                "[%s] Forbidden: bot blocked or no rights "
                "(user_id=%s chat_id=%s)",
                request_id,
                user_id,
                chat_id,
            )
            return

        case BadRequest():
            logger.warning("[%s] BadRequest (update_type=%s): %s %s", request_id, update_type, error, update)
            return

        case TimedOut() | NetworkError():
            logger.warning(
                "[%s] Telegram API temporary error: %s",
                request_id,
                error,
            )
            return

        # ---------- БИЗНЕС-ОШИБКИ ----------
        case BusinessError():
            logger.info(
                "[%s] Business error (user_id=%s): %s",
                request_id,
                user_id,
                error,
            )
            if update and update.effective_message:
                await update.effective_message.reply_text(str(error))
            return

    # ---------- НЕОЖИДАННЫЕ ОШИБКИ ----------
    logger.error(
        "[%s] Unhandled exception\n"
        "update_type=%s\n"
        "user_id=%s\n"
        "chat_id=%s\n"
        "error=%r\n"
        "traceback:\n%s",
        request_id,
        update_type,
        user_id,
        chat_id,
        error,
        "".join(traceback.format_exception(error)),
    )

    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"⚠️ Произошла внутренняя ошибка.\n"
            f"Код ошибки: `{request_id}`",
            parse_mode="Markdown",
        )
