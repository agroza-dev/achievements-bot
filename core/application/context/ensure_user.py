from telegram import User

from core.dto.user_dto import UserDTO
from core.infrastructure.repositories.user_repository import UserRepository


class EnsureUserUseCase:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, tg_user: User) -> UserDTO:
        async with self.uow_factory() as uow:
            repo: UserRepository = uow.get_repo(UserRepository)

            user = await repo.get_by_tg_id(tg_user.id)
            if user:
                return user

            return await repo.upsert(tg_user)
