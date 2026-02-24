from dataclasses import dataclass
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
    meta: dict[str, Any]

@dataclass(slots=True)
class RatingLedgerHistoryEntryDTO(RatingLedgerEntryDTO):
    created_at: datetime
    initiator_username: str | None = None

@dataclass(slots=True)
class RatingLedgerRecordDTO:
    """DTO для записи из rating_ledger при поиске"""
    id: int
    amount: int
    operation_type: str
    operation_subtype: str | None
    is_reverted: bool
    meta: dict[str, Any]
