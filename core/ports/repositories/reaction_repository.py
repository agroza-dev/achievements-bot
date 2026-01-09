from typing import Protocol

from core.dto.reaction_dto import ReactionDTO


class ReactionRepository(Protocol):
    async def list_for_update(
        self,
        chat_id: int,
        message_id: int,
        from_user_id: int,
    ) -> list[ReactionDTO]:
        ...

    async def add(self, reaction: ReactionDTO) -> None:
        ...

    async def delete(
        self,
        chat_id: int,
        message_id: int,
        from_user_id: int,
        reaction: str,
    ) -> None:
        ...
