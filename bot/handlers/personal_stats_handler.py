import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.user_chats_keyboard import build_user_chats_keyboard
from bot.renders.personal_stats_renderer import render_personal_stats
from core.container import Container
from core.ports.bot_gateway import BotGateway
from utils.logger import prettify

logger = logging.getLogger(__name__)


DEFAULT_LIMIT = 5


async def personal_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    if chat.type != "private":
        await update.message.reply_text(
            "📊 Посмотреть личную статистику можно только в личных сообщениях с ботом."
        )
        return

    container: Container = context.bot_data["container"]
    bot_gateway: BotGateway = container.get_bot_gateway()

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
        # один чат — сразу идём за статистикой
        context.user_data["stats_chat_id"] = chats[0].chat_id
        await bot_gateway.send_message(
            chat_id=chat.id,
            text=f"📊 Статистика для чата «{chats[0].title}»:",
        )
        # дальше можно вызвать общий метод показа статистики
        context.args = [str(chats[0].chat_id)]
        return

    keyboard = build_user_chats_keyboard(chats)

    await update.message.reply_text(
        "📊 Выбери чат, по которому показать статистику:",
        reply_markup=keyboard,
    )


async def personal_stats_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data
    if not data or not data.startswith("stats:chat:"):
        return

    _, _, chat_id_raw = data.partition("stats:chat:")
    try:
        chat_id = int(chat_id_raw)
    except ValueError:
        logger.warning("Invalid callback data: %s", data)
        return

    user = query.from_user
    if not user:
        return

    container: Container = context.bot_data["container"]

    get_stats_uc = container.get_personal_stats_use_case()

    stats = await get_stats_uc.execute(
        tg_user_id=update.effective_user.id,
        tg_chat_id=chat_id,
        limit=DEFAULT_LIMIT,
        offset=0,
    )
    logger.debug(f"User stats: {prettify(stats)}")
    text = render_personal_stats(
        stats,
        current_user_id=user.id,
        user_timezone=stats.user_timezone,
    )

    await query.edit_message_text(
        text=text,
        disable_web_page_preview=True,
    )
