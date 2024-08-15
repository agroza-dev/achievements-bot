import re
from typing import Union, Tuple

from telegram import Message
from telegram.constants import ReactionEmoji
from telegram.ext import ContextTypes

from achievements_bot.db import execute, in_savepoint
from achievements_bot.services import user
from achievements_bot.services.logger import logger
from achievements_bot.services.user import UserEntity, update_points_balance


class Triggers:
    POSITIVE: str = 'POSITIVE'
    NEGATIVE: str = 'NEGATIVE'
    ERROR: str = 'ERROR'

    EFFECTIVE_TRIGGERS: list = [POSITIVE, NEGATIVE]


def classify_message(text):
    text = text
    points = 0
    command_type = Triggers.ERROR
    effective_pattern = ''

    positive_patterns = [
        re.compile(r'лови\s*\+?\s*(\d+)\s*очков', re.RegexFlag.IGNORECASE),
        re.compile(r'\s*\+?\s*(\d+)\sэтому господину', re.RegexFlag.IGNORECASE),
        re.compile(r'\s*\+?\s*(\d+)\sочков этому господину', re.RegexFlag.IGNORECASE),
        re.compile(r'\s*\+?\s*(\d+)\sэтому товарищу', re.RegexFlag.IGNORECASE),
        re.compile(r'\s*\+?\s*(\d+)\sочков этому товарищу', re.RegexFlag.IGNORECASE),
        re.compile(r'плюс\s(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'увеличиваю социальный рейтинг на\s(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'увеличиваю социальный рейтинг этого господина на\s(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'увеличиваю социальный рейтинг этому товарищу на\s(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'\+\s*(\d+)', re.RegexFlag.IGNORECASE),
    ]
    negative_patterns = [
        re.compile(r'минус\s*(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'минусую\s*(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'отбираю\s*(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'отнимаю\s*(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'уменьшаю социальный рейтинг на\s(\d+)', re.RegexFlag.IGNORECASE),
        re.compile(r'-\s*(\d+)', re.RegexFlag.IGNORECASE),
    ]

    for pattern in positive_patterns:
        match = pattern.search(text)
        if match:
            points = int(match.group(1))
            command_type = Triggers.POSITIVE
            effective_pattern = pattern.pattern
            break

    if command_type == Triggers.ERROR:
        for pattern in negative_patterns:
            match = pattern.search(text)
            if match:
                points = int(match.group(1))
                command_type = Triggers.NEGATIVE
                effective_pattern = pattern.pattern
                break
    if command_type in Triggers.EFFECTIVE_TRIGGERS and points > 0:
        return command_type, points, effective_pattern
    else:
        return Triggers.ERROR, 0, effective_pattern


async def add_to_history(
        recipient: UserEntity,
        actor: UserEntity,
        chat_id: int,
        points: int,
        message_id: int,
        autocommit: bool = False
):
    await execute(
        """
            INSERT INTO rate_history 
            (recipient_user_id, actor_user_id, chat_id, points, message, created_at)
            VALUES 
            (:recipient, :actor, :chat_id, :points, :message, datetime('now', 'localtime'));
        """,
        {
            "recipient": recipient.user_id,
            "actor": actor.user_id,
            "chat_id": chat_id,
            "points": points,
            "message": message_id,
        },
        autocommit=autocommit,
    )


async def add_points(recipient: UserEntity, actor: UserEntity, points: int, message_id: int) -> bool:
    logger.info(f'Добавляем {points} - {recipient.user_name} от {actor.user_name} за {message_id}')

    try:
        async with in_savepoint():
            await add_to_history(recipient, actor, actor.chat_id, points, message_id)
            await update_points_balance(recipient, recipient.points_rate + points)
        logger.info(f'Успешно добавили {points} - {recipient.user_name} от {actor.user_name} за {message_id}')
        return True
    except Exception as e:
        logger.info(f'Не удалось добавить {points} - {recipient.user_name} от {actor.user_name} за {message_id}')
        return False


async def take_points(recipient: UserEntity, actor: UserEntity, points: int, message_id: int) -> bool:
    points = abs(points)
    logger.info(f'Отнимаем {points} у {recipient.user_name} от {actor.user_name} за {message_id}')

    try:
        async with in_savepoint():
            await add_to_history(recipient, actor, actor.chat_id, -points, message_id)
            await update_points_balance(recipient, recipient.points_rate - points)
        logger.info(f'Успешно отняли {points} у {recipient.user_name} от {actor.user_name} за {message_id}')
        return True
    except Exception as e:
        logger.info(f'Не удалось отнять {points} у {recipient.user_name} от {actor.user_name} за {message_id}')
        return False


async def get_target_users(message: Message) -> Union[bool, Tuple[UserEntity, UserEntity]]:
    recipient = await user.get_user(
        user.UserEntityBase.from_tg_message(message.reply_to_message, message.chat_id)
    )
    actor = await user.get_user(
        user.UserEntityBase.from_tg_message(message, message.chat_id)
    )
    logger.info(f"Это ответ на сообщение от {actor.user_name} на сообщение от {recipient.user_name}")

    if actor == recipient:
        return False
    return recipient, actor


async def run(message: Message, context: ContextTypes.DEFAULT_TYPE, recipient: UserEntity, actor: UserEntity):
    status, points, pattern = classify_message(message.text)
    if status == Triggers.POSITIVE:
        result = await add_points(recipient, actor, points, message.message_id)
        reaction = ReactionEmoji.SHOCKED_FACE_WITH_EXPLODING_HEAD
        if result:
            reaction = ReactionEmoji.THUMBS_UP
        await context.bot.setMessageReaction(message.chat_id, message.message_id, reaction=reaction)
    elif status == Triggers.NEGATIVE:
        result = await take_points(recipient, actor, points, message.message_id)
        reaction = ReactionEmoji.SHOCKED_FACE_WITH_EXPLODING_HEAD
        if result:
            reaction = ReactionEmoji.OK_HAND_SIGN
        await context.bot.setMessageReaction(message.chat_id, message.message_id, reaction=reaction)
