"""
DTO для настроек чата.

Используются для новой таблицы chat_settings_v2.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ChatSettingsDTO:
    """DTO для настроек чата."""

    chat_id: int
    periodic_award_enabled: bool = True
    periodic_award_amount: int | None = None  # None = использовать дефолт из конфига
    tax_enabled: bool = False
    tax_rate: float = 0.0  # 0.0 - 99.99 (проценты)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    updated_by_user_id: int | None = None


@dataclass(slots=True)
class ChatSettingsHistoryDTO:
    """DTO для истории изменений настроек."""

    id: int
    chat_id: int
    setting_name: str  # Например: "periodic_award.amount"
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    changed_by_user_id: int | None = None
    changed_at: datetime | None = None
