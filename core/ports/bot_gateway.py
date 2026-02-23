"""Абстракция над Telegram Bot API для тестируемости и эмуляции действий."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ReactionInfo:
    """Информация о реакции."""
    emoji: str


@dataclass
class MessageInfo:
    """Информация о сообщении."""
    message_id: int
    chat_id: int
    from_user_id: int
    text: str | None = None
    reply_to_message_id: int | None = None


class BotGateway(ABC):
    """
    Порт для взаимодействия с Telegram Bot API.

    Позволяет эмулировать действия пользователей для тестирования
    и нагрузочного тестирования rate limiter.
    """

    @abstractmethod
    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> dict[str, Any]:
        """
        Отправить сообщение в чат.

        Args:
            chat_id: ID чата
            text: Текст сообщения
            **kwargs: Дополнительные аргументы (reply_to_message_id, parse_mode, etc.)

        Returns:
            Данные отправленного сообщения
        """
        pass

    @abstractmethod
    async def set_message_reaction(
        self,
        chat_id: int,
        message_id: int,
        reaction: str | list[str],
        **kwargs: Any,
    ) -> bool:
        """
        Установить реакцию на сообщение.

        Args:
            chat_id: ID чата
            message_id: ID сообщения
            reaction: Эмодзи реакции или список эмодзи
            **kwargs: Дополнительные аргументы (is_big, etc.)

        Returns:
            True если успешно
        """
        pass

    @abstractmethod
    async def get_chat(self, chat_id: int) -> dict[str, Any]:
        """
        Получить информацию о чате.

        Args:
            chat_id: ID чата

        Returns:
            Данные чата
        """
        pass

    @abstractmethod
    async def get_chat_member(self, chat_id: int, user_id: int) -> dict[str, Any]:
        """
        Получить информацию о пользователе в чате.

        Args:
            chat_id: ID чата
            user_id: ID пользователя

        Returns:
            Данные участника чата
        """
        pass

    @abstractmethod
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        Ответить на callback query.

        Args:
            callback_query_id: ID callback query
            text: Текст ответа (опционально)
            **kwargs: Дополнительные аргументы

        Returns:
            True если успешно
        """
        pass
