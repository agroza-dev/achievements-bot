from dataclasses import dataclass
from collections.abc import Iterable
from telegram import User as TelegramUser
from achievements_bot.db import fetch_one, execute, DatabaseException, fetch_all
from achievements_bot.services.logger import logger


@dataclass()
class UserEntity:
    id: int
    name: str
    points_rate: int


async def get_user(user: TelegramUser) -> UserEntity:
    if not await _is_user_exists(int(user.id)):
        await create_user(user)
    sql = """
        SELECT id, name, points_rate
        FROM user WHERE id = :id LIMIT 1
       """
    _user = await fetch_one(sql, {
        "id": user.id
    })
    return UserEntity(_user['id'], _user['name'], _user['points_rate'])


async def _is_user_exists(user_id: int) -> bool:
    logger.debug(f'Проверяем если есть пользователь с id {str(user_id)}')
    try:
        user = await fetch_one(
            """
            SELECT id FROM user WHERE id = :id LIMIT 1
            """,
            {"id": user_id}
        )
    except DatabaseException as e:
        logger.debug(f'Проверка не удалась. Ошибка при выполнении запроса: {e}')
        return False

    if not user:
        logger.debug(f'Пользователя с id {str(user_id)} не нашли')
        return False
    logger.debug(f'Пользователя с id {str(user_id)} существует')
    return True


async def create_user(user: TelegramUser) -> None:
    logger.debug(f'Создаем пользователя')
    await execute(
        """
            INSERT INTO USER (id, name)
            VALUES (:id, :name)
        """,
        {
            "id": user.id,
            "name": user.username,
        },
        autocommit=True,
    )


async def update_points_total(user: UserEntity, new_points_rate: int) -> None:
    """
    Важно, чтобы при обновлении не срабатывал коммит, иначе он сбивает цепочку.
    """
    logger.debug(f'Обновляем очки пользователя {user.name}. Было - {user.points_rate}, стало - {new_points_rate}')
    await execute(
        """
            UPDATE USER  SET points_rate = :points WHERE id = :id
        """,
        {
            "id": user.id,
            "points": new_points_rate,
        },
        autocommit=False,
    )


async def get_all_users() -> Iterable[UserEntity] | None:
    logger.debug(f'Получаем всех пользователей')
    try:
        users = await fetch_all(
            """
            SELECT id, name, points_rate FROM user
            """,
        )
    except DatabaseException as e:
        logger.debug(f'Ошибка при выполнении запроса: {e}')
        return None

    if not users:
        logger.debug(f'Не получилось достать список пользователей.')
        return None
    logger.debug(f'Достали список пользователей, упаковываем в entity')
    result = []
    for user in users:
        result.append(UserEntity(user['id'], user['name'], user['points_rate']))
    return result
