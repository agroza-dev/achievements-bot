from datetime import UTC, datetime

from core.dto.rating_ledger_dto import RatingLedgerHistoryEntryDTO


def ledger_entry(
    *,
    user_id: int = 1,
    chat_id: int = 1,
    initiator_user_id: int = 2,
    amount: int = 10,
    balance_after: int = 10,
    created_at: datetime | None = None,
) -> RatingLedgerHistoryEntryDTO:
    return RatingLedgerHistoryEntryDTO(
        chat_id=chat_id,
        user_id=user_id,
        initiator_user_id=initiator_user_id,
        amount=amount,
        balance_after=balance_after,
        operation_type="reaction",
        operation_subtype="positive",
        source_type="message",
        source_id=1,
        meta={},
        created_at=created_at or datetime.now(UTC),
    )
