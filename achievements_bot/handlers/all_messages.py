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
        appreciated_user = await user.get_user(message.reply_to_message.from_user)
        rater_user = await user.get_user(message.from_user)
        logger.info(f"Это ответ на сообщение от {rater_user.name} на сообщение от {appreciated_user.name}")

        if appreciated_user.name == config.BOT_NAME:
            logger.info('Ответ на сообщение бота...')
            return None
        if rater_user == appreciated_user:
            return None

        status, points, pattern = points_rate.classify_message(message.text)
        if status == points_rate.Triggers.POSITIVE:
            result = await points_rate.add_points(appreciated_user, rater_user, points, message.message_id)
            reaction = ReactionEmoji.SHOCKED_FACE_WITH_EXPLODING_HEAD
            if result:
                reaction = ReactionEmoji.THUMBS_UP
            await context.bot.setMessageReaction(message.chat_id, message.message_id, reaction=reaction)
        elif status == points_rate.Triggers.NEGATIVE:
            result = await points_rate.take_points(appreciated_user, rater_user, points, message.message_id)
            reaction = ReactionEmoji.SHOCKED_FACE_WITH_EXPLODING_HEAD
            if result:
                reaction = ReactionEmoji.OK_HAND_SIGN
            await context.bot.setMessageReaction(message.chat_id, message.message_id, reaction=reaction)

    elif message.text:
        logger.info('simple message')