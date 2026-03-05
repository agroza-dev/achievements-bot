"""
UseCase для обновления настроек чата.
"""

import logging

from core.domain.settings.chat_settings import ChatSettings
from core.infrastructure.repositories.chat_settings_repository import (
    ChatSettingsRepository,
)

logger = logging.getLogger(__name__)


class UpdateChatSettingsUseCase:
    """
    UseCase для обновления настроек чата.

    Полностью заменяет настройки чата новыми.
    """

    def __init__(self, settings_repo: ChatSettingsRepository):
        self.settings_repo = settings_repo

    async def execute(
        self,
        *,
        chat_id: int,
        settings: ChatSettings,
    ) -> bool:
        """
        Обновить настройки чата.

        Args:
            chat_id: Внутренний ID чата
            settings: Новые настройки

        Returns:
            True если успешно обновлено, False если чат не найден
        """
        success = await self.settings_repo.update_settings(
            chat_id=chat_id,
            settings=settings,
        )

        if success:
            logger.info(f"Обновлены настройки чата {chat_id}")
        else:
            logger.warning(f"Не удалось обновить настройки чата {chat_id}: чат не найден")

        return success
