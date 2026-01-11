from typing import Protocol


class RatingRepository(Protocol):
    async def add(self, chat_id: int, user_id: int, value: int) -> int:
        """
        Добавить значение к рейтингу пользователя в чате.
        
        Returns:
            Новый баланс рейтинга после изменения
        """
        ...
