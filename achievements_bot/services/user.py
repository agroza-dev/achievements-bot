from dataclasses import dataclass, field
from collections.abc import Iterable
from telegram import User as TelegramUser, Chat, Message
from achievements_bot.db import fetch_one, execute, DatabaseException, fetch_all
from achievements_bot.services.logger import logger
from typing import Optional, Dict


@dataclass()
class UserEntityId:
    user_id: int = field(metadata={"comment": "ID пользователя в Telegram"})
    chat_id: int = field(metadata={"comment": "ID чата, с которым работаем"})


@dataclass()
class UserEntityBase(UserEntityId):
    user_name: str = field(metadata={"comment": "Уникальное имя пользователя"})

    @staticmethod
    def from_tg_message(message: Message, chat: int) -> 'UserEntityBase':
        return UserEntityBase(
            user_id=message.from_user.id,
            user_name=message.from_user.username,
            chat_id=chat,  # TODO: проверить, можно ли брать его тоже из message
        )


@dataclass()
class UserEntity(UserEntityBase):
    points_rate: int = field(metadata={"comment": "Количество очков, которое пользователь заработал"})

    @staticmethod
    def from_dict(data: Dict) -> 'UserEntity':
        required_fields = ['user_id', 'chat_id', 'user_name']
        for required_field in required_fields:
            if required_field not in data:
                raise ValueError(f"Missing required field: {field}")

        return UserEntity(
            user_id=data['user_id'],
            chat_id=data['chat_id'],
            user_name=data.get('user_name', 'Unknown'),
            points_rate=data.get('points_rate', 0)
        )


async def get_user(user: UserEntityBase) -> UserEntity:
    if not await _is_user_exists(user):
        await create_user(user)
    sql = """
        SELECT user_id, chat_id, user_name, points_rate
        FROM user WHERE user_id = :user_id LIMIT 1
       """
    result = await fetch_one(sql, {
        "user_id": user.user_id
    })
    return UserEntity.from_dict(result)


async def _is_user_exists(user: UserEntityBase) -> bool:
    logger.debug(f'Проверяем если есть пользователь с id {str(user.user_id)} в чате {str(user.chat_id)}')
    try:
        found_user = await fetch_one(
            """
            SELECT user_id FROM user WHERE user_id = :user_id AND chat_id = :chat_id LIMIT 1
            """,
            {"user_id": user.user_id, "chat_id": user.chat_id}
        )
    except DatabaseException as e:
        logger.debug(f'Проверка не удалась. Ошибка при выполнении запроса: {e}')
        return False

    if not found_user:
        logger.debug(f'Пользователя с id {str(user.user_id)} в чате {str(user.chat_id)} не нашли')
        return False
    logger.debug(f'Пользователя с  id {str(user.user_id)} в чате {str(user.chat_id)} существует')
    return True


async def create_user(user: UserEntityBase) -> None:
    logger.debug(f'Создаем пользователя: ')
    logger.debug(user)
    await execute(
        """
            INSERT INTO USER (user_id, chat_id, user_name)
            VALUES (:user_id, :chat_id, :user_name)
        """,
        {
            "user_id": user.user_id,
            "chat_id": user.chat_id,
            "user_name": user.user_name,
        },
        autocommit=True,
    )


async def update_points_balance(user: UserEntity, new_points_rate: int, autocommit=False) -> None:
    logger.debug(f'Обновляем баланс очков пользователя {user.user_name}. '
                 f'В чате {user.chat_id} '
                 f'Было - {user.points_rate} => стало - {new_points_rate}')
    await execute(
        """
            UPDATE USER  SET points_rate = :points WHERE user_id = :user_id AND chat_id = :chat_id 
        """,
        {
            "user_id": user.user_id,
            "chat_id": user.chat_id,
            "points": new_points_rate,
        },
        autocommit=autocommit,
    )


async def get_all_users() -> Iterable[UserEntity] | None:
    logger.debug(f'Получаем всех пользователей')
    try:
        users = await fetch_all(
            """
            SELECT user_id, chat_id, user_name, points_rate FROM user
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
        result.append(UserEntity.from_dict(user))
    return result
