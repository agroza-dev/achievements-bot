"""
Базовый класс для всех настроек в приложении.

Обеспечивает единую точку расширения для будущей функциональности:
- Версионирование настроек
- Валидация
- Сериализация/десериализация
"""

from typing import TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="SettingsBase")


class SettingsBase(BaseModel):
    """
    Базовый класс для настроек.

    Все настройки сериализуются в JSONB поле в БД.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="ignore",  # Игнорируем неизвестные поля для обратной совместимости
        validate_assignment=True,
    )

    def to_json(self) -> str:
        """Сериализовать настройки в JSON строку."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls: type[T], json_str: str) -> T:
        """Десериализовать настройки из JSON строки."""
        return cls.model_validate_json(json_str)

    def to_dict(self) -> dict:
        """Сериализовать настройки в dict для сохранения в БД."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls: type[T], data: dict) -> T:
        """Создать настройки из dict."""
        return cls.model_validate(data)
