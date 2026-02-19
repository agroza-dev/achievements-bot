from operator import attrgetter

from core.dto.rating_ledger_dto import RatingLedgerHistoryEntryDTO


class FakeRatingLedgerRepo:
    def __init__(self, entries: list[RatingLedgerHistoryEntryDTO]):
        self._entries = list(entries)

    async def list_for_user(
        self,
        *,
        user_id: int,
        chat_id: int | None,
        limit: int,
        offset: int,
    ) -> list[RatingLedgerHistoryEntryDTO]:
        items = [e for e in self._entries if e.user_id == user_id and (chat_id is None or e.chat_id == chat_id)]

        items.sort(key=attrgetter("created_at"), reverse=True)

        return items[offset : offset + limit]
