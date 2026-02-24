"""Интеграционные тесты для RatingLedgerRepository с PostgreSQL."""

import pytest
from telegram import Chat, User

from core.dto.rating_ledger_dto import RatingLedgerEntryDTO
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.user_repository import UserRepository


async def _create_test_user_chat(user_repo: UserRepository, chat_repo: ChatRepository, prefix: str):
    """Создать тестовых пользователя и чат с уникальным префиксом."""
    import hashlib

    # Уникальные ID на основе префикса
    hash_val = int(hashlib.md5(prefix.encode()).hexdigest()[:8], 16) % 1000
    user_id = 30000 + hash_val
    chat_id = 40000 + hash_val

    tg_user = User(id=user_id, is_bot=False, first_name="Test", username=f"test{prefix}")
    user_dto = await user_repo.upsert(tg_user)

    tg_chat = Chat(id=chat_id, type="supergroup", title=f"Test {prefix}")
    chat_dto = await chat_repo.upsert(tg_chat)

    return user_dto.id, chat_dto.id


@pytest.mark.integration
class TestRatingLedgerRepository:
    """Интеграционные тесты DbRatingLedgerRepository."""

    @pytest.mark.asyncio
    async def test_add_entry(
        self,
        rating_ledger_repo: DbRatingLedgerRepository,
        user_repo: UserRepository,
        chat_repo: ChatRepository,
    ):
        """Тест: добавление записи в rating ledger."""
        user_id, chat_id = await _create_test_user_chat(user_repo, chat_repo, "add_entry")

        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=user_id,
            amount=10,
            balance_after=10,
            operation_type="transfer",
            operation_subtype="received",
            source_type="message",
            source_id=1,
            meta={"test": "data"},
        )

        await rating_ledger_repo.add(entry)

        entries = await rating_ledger_repo.list_for_user(
            user_id=user_id,
            chat_id=chat_id,
            limit=10,
            offset=0,
        )

        assert len(entries) == 1
        assert entries[0].amount == 10
        assert entries[0].operation_type == "transfer"

    @pytest.mark.asyncio
    async def test_add_multiple_entries_ordering(
        self,
        rating_ledger_repo: DbRatingLedgerRepository,
        user_repo: UserRepository,
        chat_repo: ChatRepository,
    ):
        """Тест: порядок записей (DESC по created_at)."""
        user_id, chat_id = await _create_test_user_chat(user_repo, chat_repo, "ordering")

        for i in range(5):
            entry = RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=user_id,
                initiator_user_id=user_id,
                amount=i,
                balance_after=i,
                operation_type="transfer",
                operation_subtype="received",
                source_type="message",
                source_id=i,
                meta={"index": i},
            )
            await rating_ledger_repo.add(entry)

        entries = await rating_ledger_repo.list_for_user(
            user_id=user_id,
            chat_id=chat_id,
            limit=10,
            offset=0,
        )

        assert len(entries) == 5
        assert entries[0].amount == 4
        assert entries[4].amount == 0

    @pytest.mark.asyncio
    async def test_list_for_user_with_limit_offset(
        self,
        rating_ledger_repo: DbRatingLedgerRepository,
        user_repo: UserRepository,
        chat_repo: ChatRepository,
    ):
        """Тест: лимит и смещение при выборке."""
        user_id, chat_id = await _create_test_user_chat(user_repo, chat_repo, "limit_offset")

        for i in range(10):
            entry = RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=user_id,
                initiator_user_id=user_id,
                amount=i,
                balance_after=i,
                operation_type="transfer",
                operation_subtype="received",
                source_type="message",
                source_id=i,
                meta={},
            )
            await rating_ledger_repo.add(entry)

        entries = await rating_ledger_repo.list_for_user(
            user_id=user_id,
            chat_id=chat_id,
            limit=3,
            offset=0,
        )
        assert len(entries) == 3
        assert entries[0].amount == 9

        entries = await rating_ledger_repo.list_for_user(
            user_id=user_id,
            chat_id=chat_id,
            limit=3,
            offset=3,
        )
        assert len(entries) == 3
        assert entries[0].amount == 6

    @pytest.mark.asyncio
    async def test_list_for_user_filter_by_chat(
        self,
        rating_ledger_repo: DbRatingLedgerRepository,
        user_repo: UserRepository,
        chat_repo: ChatRepository,
    ):
        """Тест: фильтрация по чату."""
        user_id, chat_id = await _create_test_user_chat(user_repo, chat_repo, "filter_chat")

        # Создаём второй чат
        tg_chat2 = Chat(id=59999, type="supergroup", title="Other Chat")
        chat_dto2 = await chat_repo.upsert(tg_chat2)
        other_chat_id = chat_dto2.id

        for cid in [chat_id, other_chat_id]:
            for i in range(3):
                entry = RatingLedgerEntryDTO(
                    chat_id=cid,
                    user_id=user_id,
                    initiator_user_id=user_id,
                    amount=i,
                    balance_after=i,
                    operation_type="transfer",
                    operation_subtype="received",
                    source_type="message",
                    source_id=i,
                    meta={},
                )
                await rating_ledger_repo.add(entry)

        entries = await rating_ledger_repo.list_for_user(
            user_id=user_id,
            chat_id=chat_id,
            limit=10,
            offset=0,
        )

        assert len(entries) == 3
        assert all(e.chat_id == chat_id for e in entries)

    @pytest.mark.asyncio
    async def test_find_by_source(
        self,
        rating_ledger_repo: DbRatingLedgerRepository,
        user_repo: UserRepository,
        chat_repo: ChatRepository,
    ):
        """Тест: поиск записей по source."""
        user_id, chat_id = await _create_test_user_chat(user_repo, chat_repo, "find_source")

        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=user_id,
            amount=5,
            balance_after=5,
            operation_type="reaction",
            operation_subtype="added",
            source_type="message",
            source_id=123,
            meta={"emoji": "👍"},
        )
        await rating_ledger_repo.add(entry)

        records = await rating_ledger_repo.find_by_source(
            source_type="message",
            source_id=123,
            chat_id=chat_id,
            user_id=user_id,
        )

        assert len(records) == 1
        assert records[0].amount == 5
        assert records[0].operation_type == "reaction"

    @pytest.mark.asyncio
    async def test_mark_as_reverted_by_emoji(
        self,
        rating_ledger_repo: DbRatingLedgerRepository,
        user_repo: UserRepository,
        chat_repo: ChatRepository,
    ):
        """Тест: пометка записи как отменённой."""
        user_id, chat_id = await _create_test_user_chat(user_repo, chat_repo, "revert")

        # Создаём второго пользователя
        tg_user2 = User(id=6999, is_bot=False, first_name="Reverter", username="reverter")
        user_dto2 = await user_repo.upsert(tg_user2)
        reverted_by_id = user_dto2.id

        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=user_id,
            amount=10,
            balance_after=10,
            operation_type="reaction",
            operation_subtype="added",
            source_type="message",
            source_id=456,
            meta={"emoji": "🔥"},
        )
        await rating_ledger_repo.add(entry)

        await rating_ledger_repo.mark_as_reverted_by_emoji(
            source_type="message",
            source_id=456,
            chat_id=chat_id,
            user_id=user_id,
            reverted_by_id=reverted_by_id,
            emoji="🔥",
        )

        records = await rating_ledger_repo.find_by_source(
            source_type="message",
            source_id=456,
            chat_id=chat_id,
            user_id=user_id,
        )

        assert len(records) == 1
        assert records[0].is_reverted is True
