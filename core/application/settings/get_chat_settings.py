"""
UseCase для получения настроек чата.
"""

import logging

from core.domain.settings.chat_settings import ChatSettings
from core.infrastructure.repositories.chat_settings_repository import (
    ChatSettingsRepository,
)

logger = logging.getLogger(__name__)


class GetChatSettingsUseCase:
    """
    UseCase для получения настроек чата.

    Возвращает настройки с значениями по умолчанию для отсутствующих полей.
    """

    def __init__(self, settings_repo: ChatSettingsRepository):
        self.settings_repo = settings_repo

    async def execute(self, *, chat_id: int) -> ChatSettings:
        """
        Получить настройки чата.

        Args:
            chat_id: Внутренний ID чата

        Returns:
            ChatSettings (никогда не None, возвращает настройки по умолчанию)
        """
        settings = await self.settings_repo.get_settings(chat_id=chat_id)

        if settings is None:
            logger.warning(f"Чат {chat_id} не найден, возвращаем настройки по умолчанию")
            return ChatSettings.empty()

        return settings
