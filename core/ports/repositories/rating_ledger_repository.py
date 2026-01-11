from typing import Protocol

from core.dto.rating_ledger_dto import RatingLedgerEntryDTO, RatingLedgerRecordDTO


class RatingLedgerRepository(Protocol):
    """Protocol для репозитория rating_ledger"""

    async def add(self, entry: RatingLedgerEntryDTO) -> None:
        """Добавить запись в rating_ledger"""
        ...

    async def find_by_source(self, source_type: str, source_id: int, chat_id: int, user_id: int) -> list[RatingLedgerRecordDTO]:
        """Найти записи в rating_ledger по source_type и source_id"""
        ...

    async def mark_as_reverted_by_emoji(self, source_type: str, source_id: int, chat_id: int, user_id: int, reverted_by_id: int, emoji: str) -> None:
        """Пометить запись в rating_ledger как отмененную по эмодзи"""
        ...
