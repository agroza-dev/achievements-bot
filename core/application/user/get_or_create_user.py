"""
UseCase для получения внутреннего ID пользователя по tg_id.
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.infrastructure.database import DbUnitOfWork

UowFactory = Callable[[], "DbUnitOfWork"]


class GetOrCreateUserUseCase:
    """
    UseCase для получения или создания пользователя по tg_id.

    Возвращает внутренний ID пользователя.
    """

    def __init__(self, uow_factory: UowFactory):
        self.uow_factory = uow_factory

    async def execute(self, *, tg_id: int) -> int:
        """
        Получить или создать пользователя по tg_id.

        Args:
            tg_id: Telegram user ID

        Returns:
            Внутренний ID пользователя
        """

        uow: DbUnitOfWork = self.uow_factory()
        async with uow:
            user_repo = uow.get_repo(UserRepository)

            # Пробуем получить пользователя
            user = await user_repo.get_by_tg_id(tg_id)
            if user:
                return user.id

            # Если не найден, создаём нового
            # Для этого нужно создать объект telegram.User
            from telegram import User as TgUser

            tg_user = TgUser(
                id=tg_id,
                first_name="Unknown",
                is_bot=False,
                username=None,
                last_name=None,
            )
            created_user = await user_repo.upsert(tg_user)
            return created_user.id
