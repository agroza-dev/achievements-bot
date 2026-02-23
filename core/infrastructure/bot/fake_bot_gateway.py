"""Fake реализация BotGateway для тестов и нагрузочного тестирования."""

from dataclasses import dataclass, field
from typing import Any

from core.ports.bot_gateway import BotGateway


@dataclass
class SentMessage:
    """Запись об отправленном сообщении."""
    chat_id: int
    text: str
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class SetReaction:
    """Запись об установленной реакции."""
    chat_id: int
    message_id: int
    reaction: str | list[str]
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeChat:
    """Фейковые данные чата."""
    id: int
    type: str = "supergroup"
    title: str = "Test Chat"
    username: str | None = None
    description: str | None = None


@dataclass
class FakeChatMember:
    """Фейковые данные участника чата."""
    user_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    status: str = "member"
    is_bot: bool = False


class FakeBotGateway(BotGateway):
    """
    Fake реализация BotGateway для тестов.

    Позволяет:
    - Эмулировать действия без реального Telegram API
    - Отслеживать вызовы методов
    - Тестировать rate limiter
    - Проводить нагрузочное тестирование
    """

    def __init__(
        self,
        simulate_delay: bool = False,
        delay_seconds: float = 0.01,
        fail_probability: float = 0.0,
    ):
        """
        Инициализация fake gateway.

        Args:
            simulate_delay: Имитировать задержку сети
            delay_seconds: Задержка в секундах
            fail_probability: Вероятность ошибки (0.0-1.0)
        """
        self.simulate_delay = simulate_delay
        self.delay_seconds = delay_seconds
        self.fail_probability = fail_probability

        # Хранилище вызовов для инспекции в тестах
        self.sent_messages: list[SentMessage] = []
        self.set_reactions: list[SetReaction] = []
        self.callback_answers: list[tuple[str, str | None]] = []

        # Фейковые данные
        self._chats: dict[int, FakeChat] = {}
        self._chat_members: dict[tuple[int, int], FakeChatMember] = {}

        # Счётчики для статистики
        self.call_count = 0
        self.error_count = 0

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> dict[str, Any]:
        """Эмулировать отправку сообщения."""
        self.call_count += 1
        self._simulate_network()
        self._maybe_fail()

        message = SentMessage(chat_id=chat_id, text=text, kwargs=kwargs)
        self.sent_messages.append(message)

        return {
            "message_id": len(self.sent_messages),
            "chat_id": chat_id,
            "text": text,
            "from_user_id": 999999,  # Fake bot id
        }

    async def set_message_reaction(
        self,
        chat_id: int,
        message_id: int,
        reaction: str | list[str],
        **kwargs: Any,
    ) -> bool:
        """Эмулировать установку реакции."""
        self.call_count += 1
        self._simulate_network()
        self._maybe_fail()

        set_reaction = SetReaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=reaction,
            kwargs=kwargs,
        )
        self.set_reactions.append(set_reaction)
        return True

    async def get_chat(self, chat_id: int) -> dict[str, Any]:
        """Эмулировать получение чата."""
        self.call_count += 1
        self._simulate_network()

        if chat_id in self._chats:
            chat = self._chats[chat_id]
        else:
            chat = FakeChat(id=chat_id)
            self._chats[chat_id] = chat

        return {
            "id": chat.id,
            "type": chat.type,
            "title": chat.title,
            "username": chat.username,
            "description": chat.description,
        }

    async def get_chat_member(self, chat_id: int, user_id: int) -> dict[str, Any]:
        """Эмулировать получение участника чата."""
        self.call_count += 1
        self._simulate_network()

        key = (chat_id, user_id)
        if key in self._chat_members:
            member = self._chat_members[key]
        else:
            member = FakeChatMember(user_id=user_id)
            self._chat_members[key] = member

        return {
            "user_id": member.user_id,
            "username": member.username,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "status": member.status,
            "is_bot": member.is_bot,
        }

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """Эмулировать ответ на callback query."""
        self.call_count += 1
        self._simulate_network()
        self._maybe_fail()

        self.callback_answers.append((callback_query_id, text))
        return True

    # Методы для настройки тестовых данных

    def add_chat(self, chat: FakeChat) -> None:
        """Добавить фейковый чат."""
        self._chats[chat.id] = chat

    def add_chat_member(self, member: FakeChatMember, chat_id: int) -> None:
        """Добавить фейкового участника чата."""
        self._chat_members[(chat_id, member.user_id)] = member

    def clear_history(self) -> None:
        """Очистить историю вызовов."""
        self.sent_messages.clear()
        self.set_reactions.clear()
        self.callback_answers.clear()
        self.call_count = 0
        self.error_count = 0

    def get_stats(self) -> dict[str, int]:
        """Получить статистику вызовов."""
        return {
            "total_calls": self.call_count,
            "send_message": len(self.sent_messages),
            "set_message_reaction": len(self.set_reactions),
            "answer_callback_query": len(self.callback_answers),
            "errors": self.error_count,
        }

    # Внутренние методы

    def _simulate_network(self) -> None:
        """Имитировать задержку сети."""
        if self.simulate_delay:
            import time
            time.sleep(self.delay_seconds)

    def _maybe_fail(self) -> None:
        """С вероятностью fail_probability выбросить ошибку."""
        import random
        if random.random() < self.fail_probability:
            self.error_count += 1
            raise RuntimeError("Simulated network error")
