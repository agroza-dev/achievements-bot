import re

from achievements_bot.db import execute, in_savepoint
from achievements_bot.services.logger import logger
from achievements_bot.services.user import UserEntity, update_points_total


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


async def add_points(appreciated: UserEntity, rater: UserEntity, points: int, message_id: int) -> bool:
    logger.info(f'Добавляем {points} - {appreciated} от {rater} за {message_id}')

    try:
        async with in_savepoint():
            await execute(
                """
                    INSERT INTO rate_history (appreciated_user, rated_user, points, message)
                    VALUES (:appreciated_user, :rated_user, :points, :message);
                """,
                {
                    "appreciated_user": appreciated.id,
                    "rated_user": rater.id,
                    "points": points,
                    "message": message_id,
                },
                autocommit=False,
            )
            await update_points_total(appreciated, appreciated.points_rate + points)
        logger.info(f'Успешно добавили {points} - {appreciated} от {rater} за {message_id}')
        return True
    except Exception as e:
        logger.info(f'Не удалось добавить {points} - {appreciated} от {rater} за {message_id}')
        return False


async def take_points(appreciated: UserEntity, rater: UserEntity, points: int, message_id: int) -> bool:
    logger.info(f'Отнимаем {points} у {appreciated} от {rater} за {message_id}')

    try:
        async with in_savepoint():
            await execute(
                """
                    INSERT INTO rate_history (appreciated_user, rated_user, points, message)
                    VALUES (:appreciated_user, :rated_user, :points, :message);
                """,
                {
                    "appreciated_user": appreciated.id,
                    "rated_user": rater.id,
                    "points": points,
                    "message": message_id,
                },
                autocommit=False,
            )
            await update_points_total(appreciated, appreciated.points_rate - abs(points))
        logger.info(f'Успешно отняли {points} у {appreciated} от {rater} за {message_id}')
        return True
    except Exception as e:
        logger.info(f'Не удалось отнять {points} у {appreciated} от {rater} за {message_id}')
        return False
