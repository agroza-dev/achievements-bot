from collections.abc import Callable

from core.dto.chat_user_dto import UserChatDTO
from core.infrastructure.database import DbUnitOfWork
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.user_repository import UserRepository

UowFactory = Callable[[], DbUnitOfWork]


class GetUserChatsUseCase:
    def __init__(self, uow_factory: UowFactory):
        self._uow_factory = uow_factory

    async def execute(
        self,
        *,
        tg_user_id: int,
    ) -> list[UserChatDTO]:

        async with self._uow_factory() as uow:
            user_repo: UserRepository = uow.get_repo(UserRepository)
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)

            user_id = await user_repo.get_id_by_tg_id(tg_user_id)

            if user_id is None:
                return []

            chats = await chat_repo.list_for_user(user_id=user_id)

        return chats
