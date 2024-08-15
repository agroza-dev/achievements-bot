from telegram import Update, ReactionType, User
from telegram.constants import ReactionEmoji
from telegram.ext import ContextTypes
from achievements_bot import config
from achievements_bot.handlers.response import send_response
from achievements_bot.services import points_rate, user
from achievements_bot.services.logger import logger


async def all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    logger.info('Получено сообщение:')
    logger.info(message)

    if message.sticker:
        logger.info(f"Это стикер от {update.message.from_user}")
        # await send_response(update, context, 'Это стикер!')
    elif message.forward_origin:
        logger.info(f"Это репост от {update.message.from_user}")
        # await send_response(update, context, 'Это репост!')
    elif update.message_reaction:
        # logger.info(f"Это реакция на сообщение {update.message.from_user}")
        await send_response(update, context, 'Это репост!')
    elif message.text and message.reply_to_message:
        # TODO: можно красивее сделать, нужно подумать как.
        users = await points_rate.get_target_users(message)
        if isinstance(users, tuple):
            recipient = users[0]
            actor = users[1]
            # TODO: прокидывать контекст в метод, возможно не самая лучшая идея...
            await points_rate.run(message, context, recipient, actor)

    elif message.text:
        logger.info('simple message')