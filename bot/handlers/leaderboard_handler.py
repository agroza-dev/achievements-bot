import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.user_chats_keyboard import build_user_chats_keyboard
from bot.renders.leaderboard_renderer import render_leaderboard
from core.container import Container
from utils.logger import prettify

logger = logging.getLogger(__name__)


DEFAULT_LIMIT = 15


async def _show_leaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_chat_id: int,
    chat_title: str | None = None,
):
    """Показать таблицу лидеров для указанного чата."""
    logger.info(f"Showing leaderboard for chat {tg_chat_id}")
    container: Container = context.bot_data["container"]
    get_leaderboard_uc = container.get_chat_leaderboard_use_case()

    rows = await get_leaderboard_uc.execute(
        tg_chat_id=tg_chat_id,
        limit=DEFAULT_LIMIT,
    )
    logger.debug(f"Leaderboard rows: {prettify(rows)}")

    text = render_leaderboard(rows)
    logger.debug(f"Rendered leaderboard: {text}")

    if chat_title:
        text = f"📊 {chat_title}:\n\n{text}"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            disable_web_page_preview=True,
        )
    elif update.message:
        await update.message.reply_text(
            text=text,
            disable_web_page_preview=True,
        )


async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /leaderboard."""
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    if chat.type != "private":
        # В чате — сразу показываем leaderboard для этого чата
        context.user_data["leaderboard_chat_id"] = chat.id
        await _show_leaderboard(
            update=update,
            context=context,
            tg_chat_id=chat.id,
            chat_title=None,
        )
        return

    # В личном чате — нужно выбрать чат из списка
    container: Container = context.bot_data["container"]

    get_user_chats_uc = container.get_user_chats_use_case()

    chats = await get_user_chats_uc.execute(
        tg_user_id=user.id,
    )
    logger.debug(f"User chats: {prettify(chats)}")

    if not chats:
        await update.message.reply_text(
            "Ты пока не состоишь ни в одном чате, где я считаю рейтинг."
        )
        return

    if len(chats) == 1:
        # один чат — сразу показываем leaderboard
        context.user_data["leaderboard_chat_id"] = chats[0].chat_id
        await _show_leaderboard(
            update=update,
            context=context,
            tg_chat_id=chats[0].chat_id,
            chat_title=chats[0].title,
        )
        return

    keyboard = build_user_chats_keyboard(chats, callback_prefix="leaderboard:chat:")

    await update.message.reply_text(
        "📊 Выбери чат, по которому показать таблицу лидеров:",
        reply_markup=keyboard,
    )


async def leaderboard_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback query для выбора чата в leaderboard."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data
    if not data or not data.startswith("leaderboard:chat:"):
        return

    _, _, chat_id_raw = data.partition("leaderboard:chat:")
    try:
        chat_id = int(chat_id_raw)
    except ValueError:
        logger.warning("Invalid callback data: %s", data)
        return

    user = query.from_user
    if not user:
        return

    context.user_data["leaderboard_chat_id"] = chat_id

    # Получаем название чата из базы данных
    container: Container = context.bot_data["container"]
    get_user_chats_uc = container.get_user_chats_use_case()

    chats = await get_user_chats_uc.execute(
        tg_user_id=user.id,
    )
    chat_title = None
    for chat in chats:
        if chat.chat_id == chat_id:
            chat_title = chat.title
            break

    await _show_leaderboard(
        update=update,
        context=context,
        tg_chat_id=chat_id,
        chat_title=chat_title,
    )
