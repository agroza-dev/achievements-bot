"""
Настройки чата.

Используются для новой таблицы chat_settings_v2.
Для старых чатов есть миграция данных из JSONB.
"""

from pydantic import Field

from core.config import periodic_award_config
from core.domain.settings.base import SettingsBase


class ChatPeriodicAwardSettings(SettingsBase):
    """
    Настройки периодических зачислений.

    Расписание единое для всех чатов (в конфиге).
    В настройках чата только:
    - enabled: включено ли зачисление
    - amount: сумма (None = использовать базовую из конфига)
    """

    enabled: bool = True
    amount: int | None = Field(default=None, ge=0, le=10000)


class ChatTaxSettings(SettingsBase):
    """
    Настройки налога на переводы между пользователями.
    """

    enabled: bool = False
    rate: float = Field(default=0.0, ge=0.0, le=1.0)


class ChatSettings(SettingsBase):
    """
    Все настройки чата.

    Для совместимости с новой таблицей chat_settings_v2.
    """

    periodic_award: ChatPeriodicAwardSettings = Field(
        default_factory=ChatPeriodicAwardSettings
    )
    tax: ChatTaxSettings = Field(default_factory=ChatTaxSettings)

    @classmethod
    def from_db_settings(cls, db_settings) -> ChatSettings:
        """
        Создать ChatSettings из ChatSettingsDTO.

        Args:
            db_settings: ChatSettingsDTO из репозитория

        Returns:
            ChatSettings domain модель
        """
        from core.dto.chat_settings_dto import ChatSettingsDTO

        if not isinstance(db_settings, ChatSettingsDTO):
            raise ValueError("Expected ChatSettingsDTO")

        # Определяем сумму: если None, используем дефолт из конфига
        amount = db_settings.periodic_award_amount
        if amount is None:
            amount = periodic_award_config.DEFAULT_AMOUNT

        return cls(
            periodic_award=ChatPeriodicAwardSettings(
                enabled=db_settings.periodic_award_enabled,
                amount=amount,
            ),
            tax=ChatTaxSettings(
                enabled=db_settings.tax_enabled,
                rate=db_settings.tax_rate,
            ),
        )

    @classmethod
    def empty(cls) -> ChatSettings:
        """Создать пустые настройки с значениями по умолчанию."""
        return cls()
