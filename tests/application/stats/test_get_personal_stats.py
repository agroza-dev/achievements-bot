import pytest

from core.application.stats.get_personal_stats import GetPersonalStatsUseCase
from tests.builders.ledger_entry_builder import ledger_entry
from tests.fakes.fake_db_uow import FakeDbUnitOfWork
from tests.fakes.fake_rating_ledger_repo import FakeRatingLedgerRepo


def _create_uow_factory(repo: FakeRatingLedgerRepo):
    """Создаёт фабрику FakeDbUnitOfWork для тестов."""
    def factory():
        return FakeDbUnitOfWork(rating_ledger_repo=repo)
    return factory


@pytest.mark.asyncio
async def test_returns_entries_desc_and_balance_from_last():
    repo = FakeRatingLedgerRepo(
        entries=[
            ledger_entry(amount=+10, balance_after=10),
            ledger_entry(amount=-5, balance_after=5),
        ]
    )

    uow_factory = _create_uow_factory(repo)
    uc = GetPersonalStatsUseCase(uow_factory)

    result = await uc.execute(
        tg_user_id=1,
        tg_chat_id=1,
        limit=10,
        offset=0,
    )

    assert result.balance == 5
    assert len(result.entries) == 2
    assert result.entries[0].amount == -5
    assert result.entries[1].amount == 10


@pytest.mark.asyncio
async def test_filters_by_chat():
    repo = FakeRatingLedgerRepo(
        entries=[
            ledger_entry(chat_id=1, amount=10),
            ledger_entry(chat_id=2, amount=20),
        ]
    )

    uow_factory = _create_uow_factory(repo)
    uc = GetPersonalStatsUseCase(uow_factory)

    result = await uc.execute(
        tg_user_id=1,
        tg_chat_id=1,
        limit=10,
        offset=0,
    )

    assert len(result.entries) == 1
    assert result.entries[0].chat_id == 1


@pytest.mark.asyncio
async def test_limit_and_offset():
    repo = FakeRatingLedgerRepo(
        entries=[
            ledger_entry(user_id=1, amount=10),
            ledger_entry(user_id=1, amount=20),
            ledger_entry(user_id=1, amount=30),
        ]
    )

    uow_factory = _create_uow_factory(repo)
    uc = GetPersonalStatsUseCase(uow_factory)

    result = await uc.execute(
        tg_user_id=1,
        tg_chat_id=1,
        limit=1,
        offset=1,
    )

    assert len(result.entries) == 1
    assert result.entries[0].amount == 20


@pytest.mark.asyncio
async def test_personal_stats_returns_entries_in_desc_order():
    repo = FakeRatingLedgerRepo(
        entries=[
            ledger_entry(amount=+10, balance_after=10),
            ledger_entry(amount=-5, balance_after=5),
        ]
    )

    uow_factory = _create_uow_factory(repo)
    uc = GetPersonalStatsUseCase(uow_factory)

    stats = await uc.execute(
        tg_user_id=1,
        tg_chat_id=1,
        limit=10,
        offset=0,
    )

    assert stats.balance == 5
    assert stats.entries[0].amount == -5
