"""
UseCase для получения настроек пользователя.
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.domain.settings.user_settings import UserSettings
from core.infrastructure.repositories.user_settings_repository import (
    UserSettingsRepository,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.infrastructure.database import DbUnitOfWork

UowFactory = Callable[[], "DbUnitOfWork"]


class GetUserSettingsUseCase:
    """
    UseCase для получения настроек пользователя.

    Возвращает настройки с значениями по умолчанию для отсутствующих полей.
    """

    def __init__(self, uow_factory: UowFactory):
        self.uow_factory = uow_factory

    async def execute(self, *, user_id: int) -> UserSettings:
        """
        Получить настройки пользователя.

        Args:
            user_id: Внутренний ID пользователя

        Returns:
            UserSettings (никогда не None, возвращает настройки по умолчанию)
        """

        logger.info(f"[USECASE] Getting user settings for user_id={user_id}")

        uow: DbUnitOfWork = self.uow_factory()
        async with uow:
            logger.info(f"[USECASE] Inside UOW context for user_id={user_id}")
            settings_repo = uow.get_repo(UserSettingsRepository)
            logger.info(f"[USECASE] Got settings_repo for user_id={user_id}")
            settings = await settings_repo.get_or_create_settings(user_id)
            logger.info(
                f"[USECASE] Got user settings for user_id={user_id}: "
                f"notifications_enabled={settings.notifications_enabled}"
            )

        return UserSettings.from_db_settings(settings)
