from telegram import Update
from telegram.ext import ContextTypes

from achievements_bot.db import DatabaseException, fetch_all
from achievements_bot.handlers.response import send_response
from achievements_bot.services.logger import logger
from achievements_bot.services.rate_history import get_history_by_user
from achievements_bot.services.user import UserEntity, get_user
from achievements_bot.templates import render_template


async def get_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await get_user(update.message.from_user)
    logger.debug(f'Пользователь {user.name} запросил историю начислений по себе')

    history = await get_history_by_user(user)
    print(history)
    await send_response(update, context, response=render_template("get_user_stats.j2", {'history': history, 'user': user}))
