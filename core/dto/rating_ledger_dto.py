from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class RatingLedgerEntryDTO:
    """DTO для записи в rating_ledger"""
    chat_id: int
    user_id: int
    initiator_user_id: int | None
    amount: int
    balance_after: int | None
    operation_type: str
    operation_subtype: str | None
    source_type: str
    source_id: int | None
    meta: dict[str, Any] = field(default_factory=dict)
    counterparty_user_id: int | None = None
    operation_key: str = ''  # Для idempotency (например, period_key="2026-W09"), по умолчанию ''


@dataclass(slots=True)
class RatingLedgerHistoryEntryDTO:
    """DTO для истории записей rating_ledger с username"""
    chat_id: int
    user_id: int
    initiator_user_id: int | None
    amount: int
    balance_after: int | None
    operation_type: str
    operation_subtype: str | None
    source_type: str
    source_id: int | None
    meta: dict[str, Any]
    counterparty_user_id: int | None
    created_at: datetime
    initiator_username: str | None = None
    counterparty_username: str | None = None
    tax: int | None = None

@dataclass(slots=True)
class RatingLedgerRecordDTO:
    """DTO для записи из rating_ledger при поиске"""
    id: int
    amount: int
    operation_type: str
    operation_subtype: str | None
    is_reverted: bool
    meta: dict[str, Any]
