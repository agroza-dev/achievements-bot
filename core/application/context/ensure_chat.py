from telegram import Chat

from core.dto.chat_dto import ChatDTO
from core.infrastructure.repositories.chat_repository import ChatRepository


class EnsureChatUseCase:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, tg_chat: Chat) -> ChatDTO:
        async with self.uow_factory() as uow:
            repo: ChatRepository = uow.get_repo(ChatRepository)

            user = await repo.get_by_tg_id(tg_chat.id)
            if user:
                return user

            return await repo.upsert(tg_chat)
