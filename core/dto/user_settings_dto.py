"""
DTO для настроек пользователя.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class UserSettingsDTO:
    """DTO для настроек пользователя."""

    user_id: int
    notifications_enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    updated_by_user_id: int | None = None


@dataclass(slots=True)
class UserSettingsHistoryDTO:
    """DTO для истории изменений настроек."""

    id: int
    user_id: int
    setting_name: str
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    changed_by_user_id: int | None = None
    changed_at: datetime | None = None
