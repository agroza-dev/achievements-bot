"""PostgreSQL-based persistence for telegram.ext bots."""

import asyncio
from collections.abc import Callable
from copy import deepcopy
from logging import getLogger
from typing import Any

from telegram.ext import BasePersistence, PersistenceInput
from telegram.ext._contexttypes import ContextTypes
from telegram.ext._utils.types import BD, CD, UD, CDCData, ConversationDict, ConversationKey

from core.infrastructure.repositories.bot_persistence_repository import (
    PostgreSQLBotPersistenceRepository,
)

logger = getLogger(__name__)


class PostgreSQLPersistence(BasePersistence[UD, CD, BD]):
    """
    PostgreSQL-based persistence for telegram.ext bots.

    Stores bot_data, chat_data, user_data, callback_data, and conversations
    in a PostgreSQL database using JSON columns.

    Args:
        pool_factory: Callable that returns asyncpg.Pool (for lazy initialization)
        store_data: Specifies which kinds of data will be saved
        update_interval: Time in seconds between persistence updates (default: 60)
        context_types: Custom context types (optional)

    Attributes:
        store_data: Specifies which kinds of data will be saved
        bot: The bot instance (set by Application)
    """

    __slots__ = (
        "_lock",
        "_on_flush",
        "_pool_factory",
        "_repository",
        "bot_data",
        "callback_data",
        "chat_data",
        "context_types",
        "conversations",
        "user_data",
    )

    def __init__(
        self,
        pool_factory: Callable[[], Any],  # Returns asyncpg.Pool
        store_data: PersistenceInput | None = None,
        update_interval: float = 60,
        context_types: ContextTypes[Any, UD, CD, BD] | None = None,
    ):
        super().__init__(store_data=store_data, update_interval=update_interval)
        self._pool_factory = pool_factory
        self._repository: PostgreSQLBotPersistenceRepository | None = None
        self._lock = asyncio.Lock()
        self.context_types: ContextTypes[Any, UD, CD, BD] = context_types or ContextTypes()
        self._on_flush = False  # Внутренний флаг для отслеживания flush

        # In-memory cache
        self.bot_data: BD | None = None
        self.chat_data: dict[int, CD] | None = None
        self.user_data: dict[int, UD] | None = None
        self.callback_data: CDCData | None = None
        self.conversations: dict[str, dict[ConversationKey, object]] | None = None

    @property
    def on_flush(self) -> bool:
        """Return whether persistence should only be saved on flush."""
        return self._on_flush

    def _get_repository(self) -> PostgreSQLBotPersistenceRepository:
        """Get or create repository."""
        if self._repository is None:
            pool = self._pool_factory()
            self._repository = PostgreSQLBotPersistenceRepository(pool)
        return self._repository

    async def get_user_data(self) -> dict[int, UD]:
        """
        Returns the user_data from the database or an empty dict.

        Returns:
            dict[int, UD]: The restored user data.
        """
        if self.user_data is not None:
            return deepcopy(self.user_data)

        # Если репозиторий ещё не инициализирован, возвращаем пустые данные
        if self._repository is None:
            return {}

        async with self._lock:
            if self.user_data is not None:
                return deepcopy(self.user_data)

            repository = self._get_repository()
            user_ids = await repository.get_all_user_ids()
            self.user_data = {}

            for user_id in user_ids:
                data = await repository.get_user_data(user_id)
                if data:
                    self.user_data[user_id] = data

            return deepcopy(self.user_data)

    async def get_chat_data(self) -> dict[int, CD]:
        """
        Returns the chat_data from the database or an empty dict.

        Returns:
            dict[int, CD]: The restored chat data.
        """
        if self.chat_data is not None:
            return deepcopy(self.chat_data)

        # Если репозиторий ещё не инициализирован, возвращаем пустые данные
        if self._repository is None:
            return {}

        async with self._lock:
            if self.chat_data is not None:
                return deepcopy(self.chat_data)

            repository = self._get_repository()
            chat_ids = await repository.get_all_chat_ids()
            self.chat_data = {}

            for chat_id in chat_ids:
                data = await repository.get_chat_data(chat_id)
                if data:
                    self.chat_data[chat_id] = data

            return deepcopy(self.chat_data)

    async def get_bot_data(self) -> BD:
        """
        Returns the bot_data from the database or an empty object.

        Returns:
            BD: The restored bot data.
        """
        if self.bot_data is not None:
            return deepcopy(self.bot_data)

        # Если репозиторий ещё не инициализирован, возвращаем пустые данные
        if self._repository is None:
            return self.context_types.bot_data()

        async with self._lock:
            if self.bot_data is not None:
                return deepcopy(self.bot_data)

            repository = self._get_repository()
            data = await repository.get_bot_data()
            self.bot_data = data if data else self.context_types.bot_data()

            return deepcopy(self.bot_data)

    async def get_callback_data(self) -> CDCData | None:
        """
        Returns the callback_data from the database or None.

        Returns:
            CDCData | None: The restored callback data or None.
        """
        if self.callback_data is not None:
            return deepcopy(self.callback_data)

        async with self._lock:
            if self.callback_data is not None:
                return deepcopy(self.callback_data)

            repository = self._get_repository()
            bot_data = await repository.get_bot_data()
            self.callback_data = bot_data.get("__callback_data__") if bot_data else None

            return deepcopy(self.callback_data) if self.callback_data else None

    async def get_conversations(self, name: str) -> ConversationDict:
        """
        Returns the conversations for the given handler name.

        Args:
            name: The handler's name.

        Returns:
            dict: The restored conversations for the handler.
        """
        if self.conversations is not None:
            return self.conversations.get(name, {}).copy()

        async with self._lock:
            if self.conversations is not None:
                return self.conversations.get(name, {}).copy()

            repository = self._get_repository()
            bot_data = await repository.get_bot_data()
            conversations = bot_data.get("__conversations__", {}) if bot_data else {}
            self.conversations = conversations

            return self.conversations.get(name, {}).copy()

    async def update_conversation(
        self, name: str, key: ConversationKey, new_state: object | None
    ) -> None:
        """
        Update the conversation state for the given handler.

        Args:
            name: The handler's name.
            key: The key the state is changed for.
            new_state: The new state for the given key.
        """
        if self.conversations is None:
            self.conversations = {}

        if self.conversations.setdefault(name, {}).get(key) == new_state:
            return

        self.conversations[name][key] = new_state

        if not self.on_flush:
            await self._save_bot_data()

    async def update_user_data(self, user_id: int, data: UD) -> None:
        """
        Update the user_data for the given user.

        Args:
            user_id: The user ID.
            data: The user data.
        """
        if self.user_data is None:
            self.user_data = {}

        if self.user_data.get(user_id) == data:
            return

        self.user_data[user_id] = data
        logger.debug(f"Persistence: update_user_data user_id={user_id}, data={data}")

        if not self.on_flush:
            repository = self._get_repository()
            await repository.set_user_data(user_id, data)

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        """
        Update the chat_data for the given chat.

        Args:
            chat_id: The chat ID.
            data: The chat data.
        """
        if self.chat_data is None:
            self.chat_data = {}

        if self.chat_data.get(chat_id) == data:
            return

        self.chat_data[chat_id] = data
        logger.debug(f"Persistence: update_chat_data chat_id={chat_id}, data={data}")

        if not self.on_flush:
            repository = self._get_repository()
            await repository.set_chat_data(chat_id, data)

    async def update_bot_data(self, data: BD) -> None:
        """
        Update the bot_data.

        Args:
            data: The bot data.
        """
        if self.bot_data == data:
            return

        self.bot_data = data
        logger.debug(f"Persistence: update_bot_data data={data}")

        if not self.on_flush:
            await self._save_bot_data()

    async def update_callback_data(self, data: CDCData) -> None:
        """
        Update the callback_data.

        Args:
            data: The callback data.
        """
        if self.callback_data == data:
            return

        self.callback_data = data

        if not self.on_flush:
            await self._save_bot_data()

    async def drop_chat_data(self, chat_id: int) -> None:
        """
        Delete chat data from persistence.

        Args:
            chat_id: The chat ID to delete.
        """
        if self.chat_data is None:
            return

        self.chat_data.pop(chat_id, None)

        if not self.on_flush:
            repository = self._get_repository()
            await repository.drop_chat_data(chat_id)

    async def drop_user_data(self, user_id: int) -> None:
        """
        Delete user data from persistence.

        Args:
            user_id: The user ID to delete.
        """
        if self.user_data is None:
            return

        self.user_data.pop(user_id, None)

        if not self.on_flush:
            repository = self._get_repository()
            await repository.drop_user_data(user_id)

    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        """
        Refresh user data from external source (no-op by default).

        Args:
            user_id: The user ID.
            user_data: The user data to refresh.
        """
        # No-op: no external refresh needed
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        """
        Refresh chat data from external source (no-op by default).

        Args:
            chat_id: The chat ID.
            chat_data: The chat data to refresh.
        """
        # No-op: no external refresh needed
        pass

    async def refresh_bot_data(self, bot_data: BD) -> None:
        """
        Refresh bot data from external source (no-op by default).

        Args:
            bot_data: The bot data to refresh.
        """
        # No-op: no external refresh needed
        pass

    async def flush(self) -> None:
        """
        Flush all in-memory data to the database.
        """
        async with self._lock:
            repository = self._get_repository()

            # Save user data
            if self.user_data:
                for user_id, data in self.user_data.items():
                    await repository.set_user_data(user_id, data)

            # Save chat data
            if self.chat_data:
                for chat_id, data in self.chat_data.items():
                    await repository.set_chat_data(chat_id, data)

            # Save bot data (including callback_data and conversations)
            await self._save_bot_data()

    async def _save_bot_data(self) -> None:
        """
        Save bot_data along with callback_data and conversations.

        Исключает служебные ключи, которые не должны сохраняться в БД:
        - container
        - db_manager
        - persistence_repository
        """
        repository = self._get_repository()

        # Ключи, которые не должны сохраняться в persistence
        excluded_keys = {'container', 'db_manager', 'persistence_repository'}

        # bot_data может быть dict или кастомным объектом
        if self.bot_data is None:
            data = {}
        elif isinstance(self.bot_data, dict):
            # Фильтруем исключая служебные ключи
            data = {k: v for k, v in self.bot_data.items() if k not in excluded_keys}
        else:
            # Для кастомных объектов пытаемся получить dict
            data = dict(self.bot_data) if hasattr(self.bot_data, '__iter__') else {}

        if self.callback_data is not None:
            data["__callback_data__"] = self.callback_data

        if self.conversations is not None:
            data["__conversations__"] = self.conversations

        await repository.set_bot_data(data)
