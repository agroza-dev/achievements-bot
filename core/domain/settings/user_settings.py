"""
Настройки пользователя.

Используются для таблицы user_settings.
"""

from typing import TYPE_CHECKING

from pydantic import Field

from core.domain.settings.base import SettingsBase

if TYPE_CHECKING:
    from core.dto.user_settings_dto import UserSettingsDTO
else:
    UserSettingsDTO = None


class UserNotificationSettings(SettingsBase):
    """
    Настройки уведомлений пользователя.

    - enabled: включены ли уведомления от бота
    """

    enabled: bool = True


class UserSettings(SettingsBase):
    """
    Все настройки пользователя.

    Для совместимости с таблицей user_settings.
    """

    notifications: UserNotificationSettings = Field(
        default_factory=UserNotificationSettings
    )

    @classmethod
    def from_db_settings(cls, db_settings: UserSettingsDTO) -> UserSettings:
        """
        Создать UserSettings из UserSettingsDTO.

        Args:
            db_settings: UserSettingsDTO из репозитория

        Returns:
            UserSettings domain модель
        """
        from core.dto.user_settings_dto import UserSettingsDTO

        if not isinstance(db_settings, UserSettingsDTO):
            raise ValueError("Expected UserSettingsDTO")

        return cls(
            notifications=UserNotificationSettings(
                enabled=db_settings.notifications_enabled,
            ),
        )

    @classmethod
    def empty(cls) -> UserSettings:
        """Создать пустые настройки с значениями по умолчанию."""
        return cls()
