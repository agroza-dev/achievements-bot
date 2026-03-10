"""
UseCase для обновления настроек уведомлений пользователя.
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


class UpdateUserNotificationsUseCase:
    """
    UseCase для включения/выключения уведомлений пользователя.
    """

    def __init__(self, uow_factory: UowFactory):
        self.uow_factory = uow_factory

    async def execute(
        self,
        *,
        user_id: int,
        enabled: bool,
        updated_by_user_id: int | None = None,
    ) -> UserSettings:
        """
        Обновить настройки уведомлений пользователя.

        Args:
            user_id: Внутренний ID пользователя
            enabled: Включить (True) или выключить (False) уведомления
            updated_by_user_id: Кто изменил настройки (опционально)

        Returns:
            Обновлённые UserSettings
        """

        uow: DbUnitOfWork = self.uow_factory()
        async with uow:
            settings_repo = uow.get_repo(UserSettingsRepository)

            # Получаем или создаём настройки
            await settings_repo.get_or_create_settings(user_id)

            # Обновляем настройки
            updated = await settings_repo.update_settings(
                user_id=user_id,
                notifications_enabled=enabled,
                updated_by_user_id=updated_by_user_id,
            )

            if updated is None:
                logger.warning(f"Не удалось обновить настройки пользователя {user_id}")
                raise ValueError(f"User {user_id} not found")

            # Преобразуем в domain модель
            return UserSettings.from_db_settings(updated)
