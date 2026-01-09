from core.dto.chat_user_dto import ChatUserDTO
from core.infrastructure.repositories.chat_user_repository import ChatUserRepository


class EnsureChatUserUseCase:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, chat_id: int, user_id: int) -> ChatUserDTO:
        async with self.uow_factory() as uow:
            repo: ChatUserRepository = uow.get_repo(ChatUserRepository)

            chat_user = await repo.get_chat_user(chat_id, user_id)
            if chat_user:
                return chat_user

            return await repo.add_user_to_chat(chat_id, user_id, False)
