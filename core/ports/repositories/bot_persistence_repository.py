from typing import Any, Protocol


class BotPersistenceRepository(Protocol):
    """Репозиторий для хранения данных персистентности бота."""

    async def get_bot_data(self) -> dict[str, Any]:
        """Получить глобальные данные бота."""
        ...

    async def set_bot_data(self, data: dict[str, Any]) -> None:
        """Установить глобальные данные бота."""
        ...

    async def get_chat_data(self, chat_id: int) -> dict[str, Any]:
        """Получить данные чата."""
        ...

    async def set_chat_data(self, chat_id: int, data: dict[str, Any]) -> None:
        """Установить данные чата."""
        ...

    async def get_user_data(self, user_id: int) -> dict[str, Any]:
        """Получить данные пользователя."""
        ...

    async def set_user_data(self, user_id: int, data: dict[str, Any]) -> None:
        """Установить данные пользователя."""
        ...

    async def drop_chat_data(self, chat_id: int) -> None:
        """Удалить данные чата."""
        ...

    async def drop_user_data(self, user_id: int) -> None:
        """Удалить данные пользователя."""
        ...

    async def get_all_chat_ids(self) -> list[int]:
        """Получить все ID чатов."""
        ...

    async def get_all_user_ids(self) -> list[int]:
        """Получить все ID пользователей."""
        ...
