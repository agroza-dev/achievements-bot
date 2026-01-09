from typing import Protocol


class RatingRepository(Protocol):
    async def add(self, user_id: int, value: int) -> None:
        ...
