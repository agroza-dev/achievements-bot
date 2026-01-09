from typing import Protocol

from core.dto.chat_message_create_dto import ChatMessageCreateDTO
from core.dto.chat_message_dto import ChatMessageDTO


class ChatMessageRepository(Protocol):

    async def get_by_tg_id(
        self,
        chat_id: int,
        tg_message_id: int,
    ) -> ChatMessageDTO | None:
        ...

    async def save_if_not_exists(
        self,
        message: ChatMessageCreateDTO,
    ) -> ChatMessageDTO:
        ...
