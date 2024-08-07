import re

from achievements_bot.db import execute, in_savepoint
from achievements_bot.services.logger import logger
from achievements_bot.services.user import UserEntity, update_points_total

POSITIVE = 'positive'
NEGATIVE = 'negative'
ERROR = 'error'

EFFECTIVE_STATUSES = [POSITIVE, NEGATIVE]


def classify_message(text):
    positive_patterns = [
        r'\bлови\b', r'\bполучай\b', r'\bэтому господину\b', r'\bэтому товарищу\b',
        r'\bдаю\b', r'\bна\b', r'\bдержи\b', r'\bвот тебе\b'
    ]
    negative_patterns = [
        r'\bминус\b', r'\bотобрать\b', r'\bзабрать\b', r'\bотнять\b'
    ]
    points = 0
    command_type = ERROR

    # Поиск чисел в тексте
    number_pattern = re.compile(r'[-+]?\d+')
    numbers = number_pattern.findall(text)

    if numbers:
        points = int(numbers[0])

    if points == 0:
        return command_type, points

    # Проверка на положительные триггеры
    for pattern in positive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            command_type = POSITIVE
            break

    # Проверка на отрицательные триггеры
    for pattern in negative_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            command_type = NEGATIVE
            break

    # Специальная проверка для чисел с плюсом или минусом
    if re.search(r'^\+(\s+)?\d+', text):
        command_type = POSITIVE
    elif re.search(r'^-(\s+)?\d+', text):
        command_type = NEGATIVE

    return command_type, points


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
                    "points": -points,
                    "message": message_id,
                },
                autocommit=False,
            )
            await update_points_total(appreciated, appreciated.points_rate - points)
        logger.info(f'Успешно отняли {points} у {appreciated} от {rater} за {message_id}')
        return True
    except Exception as e:
        logger.info(f'Не удалось отнять {points} у {appreciated} от {rater} за {message_id}')
        return False
