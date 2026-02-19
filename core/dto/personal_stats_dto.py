from dataclasses import dataclass

from core.dto.rating_ledger_dto import RatingLedgerHistoryEntryDTO


@dataclass(frozen=True)
class PersonalStatsDTO:
    balance: int
    entries: list[RatingLedgerHistoryEntryDTO]
