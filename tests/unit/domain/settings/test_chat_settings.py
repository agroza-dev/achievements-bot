"""
Тесты для схем настроек чата.
"""

import pytest

from core.domain.settings import (
    ChatPeriodicAwardSettings,
    ChatSettings,
    ChatTaxSettings,
)


class TestChatPeriodicAwardSettings:
    """Тесты для настроек периодических бонусов."""

    def test_default_values(self):
        """Проверка значений по умолчанию."""
        settings = ChatPeriodicAwardSettings()
        assert settings.enabled is True
        assert settings.amount is None

    def test_custom_values(self):
        """Проверка установки кастомных значений."""
        settings = ChatPeriodicAwardSettings(
            enabled=False,
            amount=100,
        )
        assert settings.enabled is False
        assert settings.amount == 100

    def test_amount_validation_positive(self):
        """Проверка валидации amount (положительные значения)."""
        settings = ChatPeriodicAwardSettings(amount=0)
        assert settings.amount == 0

        settings = ChatPeriodicAwardSettings(amount=10000)
        assert settings.amount == 10000

    def test_amount_validation_negative(self):
        """Проверка валидации amount (отрицательные значения)."""
        with pytest.raises(ValueError):
            ChatPeriodicAwardSettings(amount=-1)

    def test_amount_validation_too_large(self):
        """Проверка валидации amount (слишком большое значение)."""
        with pytest.raises(ValueError):
            ChatPeriodicAwardSettings(amount=10001)


class TestChatTaxSettings:
    """Тесты для настроек налога."""

    def test_default_values(self):
        """Проверка значений по умолчанию."""
        settings = ChatTaxSettings()
        assert settings.enabled is False
        assert settings.rate == 0.0

    def test_custom_values(self):
        """Проверка установки кастомных значений."""
        settings = ChatTaxSettings(
            enabled=True,
            rate=0.15,
        )
        assert settings.enabled is True
        assert settings.rate == 0.15

    def test_rate_validation_zero(self):
        """Проверка валидации rate (ноль)."""
        settings = ChatTaxSettings(rate=0.0)
        assert settings.rate == 0.0

    def test_rate_validation_max(self):
        """Проверка валидации rate (максимум)."""
        settings = ChatTaxSettings(rate=1.0)
        assert settings.rate == 1.0

    def test_rate_validation_negative(self):
        """Проверка валидации rate (отрицательное)."""
        with pytest.raises(ValueError):
            ChatTaxSettings(rate=-0.1)

    def test_rate_validation_too_large(self):
        """Проверка валидации rate (слишком большое)."""
        with pytest.raises(ValueError):
            ChatTaxSettings(rate=1.1)


class TestChatSettings:
    """Тесты для основных настроек чата."""

    def test_empty_settings(self):
        """Проверка создания пустых настроек."""
        settings = ChatSettings.empty()
        assert settings.periodic_award.enabled is True
        assert settings.periodic_award.amount is None
        assert settings.tax.enabled is False

    def test_default_initialization(self):
        """Проверка инициализации по умолчанию."""
        settings = ChatSettings()
        assert isinstance(settings.periodic_award, ChatPeriodicAwardSettings)
        assert isinstance(settings.tax, ChatTaxSettings)

    def test_custom_initialization(self):
        """Проверка кастомной инициализации."""
        settings = ChatSettings(
            periodic_award=ChatPeriodicAwardSettings(
                enabled=False,
                amount=200,
            ),
            tax=ChatTaxSettings(
                enabled=True,
                rate=0.2,
            ),
        )
        assert settings.periodic_award.enabled is False
        assert settings.periodic_award.amount == 200
        assert settings.tax.enabled is True
        assert settings.tax.rate == 0.2

    def test_model_copy(self):
        """Проверка копирования модели с изменениями."""
        original = ChatSettings()
        modified = original.model_copy(
            update={
                "periodic_award": original.periodic_award.model_copy(
                    update={"enabled": False, "amount": 150}
                )
            }
        )
        assert original.periodic_award.enabled is True
        assert original.periodic_award.amount is None
        assert modified.periodic_award.enabled is False
        assert modified.periodic_award.amount == 150

    def test_serialization_to_json(self):
        """Проверка сериализации в JSON."""
        settings = ChatSettings(
            periodic_award=ChatPeriodicAwardSettings(
                enabled=False,
                amount=100,
            )
        )
        json_str = settings.to_json()
        assert isinstance(json_str, str)
        assert "periodic_award" in json_str

    def test_deserialization_from_json(self):
        """Проверка десериализации из JSON."""
        json_str = """
        {
            "periodic_award": {
                "enabled": true,
                "amount": 75
            },
            "tax": {
                "enabled": false,
                "rate": 0.0
            }
        }
        """
        settings = ChatSettings.from_json(json_str)
        assert settings.periodic_award.enabled is True
        assert settings.periodic_award.amount == 75

    def test_serialization_to_dict(self):
        """Проверка сериализации в dict."""
        settings = ChatSettings(
            periodic_award=ChatPeriodicAwardSettings(enabled=False)
        )
        data = settings.to_dict()
        assert isinstance(data, dict)
        assert data["periodic_award"]["enabled"] is False

    def test_deserialization_from_dict(self):
        """Проверка десериализации из dict."""
        data = {
            "periodic_award": {
                "enabled": True,
                "amount": 50,
            }
        }
        settings = ChatSettings.from_dict(data)
        assert settings.periodic_award.enabled is True

    def test_extra_fields_ignored(self):
        """Проверка игнорирования неизвестных полей."""
        data = {
            "periodic_award": {
                "enabled": True,
                "unknown_field": "some_value",
            },
            "unknown_section": {},
        }
        settings = ChatSettings.from_dict(data)
        assert settings.periodic_award.enabled is True
