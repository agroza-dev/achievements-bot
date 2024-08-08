from telegram import Update
from telegram.ext import ContextTypes

from achievements_bot.handlers.response import send_response
from achievements_bot.services.logger import logger
from achievements_bot.services.user import get_all_users
from achievements_bot.templates import render_template


async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug(f'Пользователь {update.message.from_user.username} запросил стастистику по всем пользователям')
    users = await get_all_users()
    await send_response(update, context, response=render_template("get_stats.j2", {'users': users}))
