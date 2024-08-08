from dataclasses import dataclass
from collections.abc import Iterable
from telegram import User as TelegramUser
from achievements_bot.db import fetch_one, execute, DatabaseException, fetch_all
from achievements_bot.services.logger import logger
from achievements_bot.services.user import UserEntity


@dataclass()
class RateHistoryEntity:
    id: int
    appreciated_user: str
    rated_user: str
    points: int
    message: int
    created_at: str


async def get_history_by_user(user: UserEntity) -> Iterable[RateHistoryEntity] | None:
    logger.debug(f'Получаем историю для пользователя {user.name}')
    try:
        history = await fetch_all(
            """
            SELECT
                rate_history.id, 
                au.name as appreciated_user, 
                ar.name as rated_user, 
                points, 
                message, 
                created_at
            FROM rate_history
            LEFT JOIN user as au ON appreciated_user = au.id
            LEFT JOIN user as ar ON rated_user = ar.id
            WHERE rate_history.appreciated_user = :user_id
            """,
            {'user_id': user.id}
        )
    except DatabaseException as e:
        logger.debug(f'Ошибка при выполнении запроса: {e}')
        return None

    if not history:
        logger.debug(f'Не получилось достать историю для пользователя {user.name}.')
        return None
    logger.debug(f'Достали историю для пользователя {user.name}, упаковываем в entity')
    result = []
    for item in history:
        result.append(RateHistoryEntity(
            item['id'],
            item['appreciated_user'],
            item['rated_user'],
            item['points'],
            item['message'],
            item['created_at']
        ))
    return result

