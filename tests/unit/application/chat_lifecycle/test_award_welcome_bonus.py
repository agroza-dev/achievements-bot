"""Тесты для AwardWelcomeBonusUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.application.chat_lifecycle.award_welcome_bonus import AwardWelcomeBonusUseCase
from core.application.rating_ledger.rating_ledger_service import RatingLedgerService
from core.dto.rating_ledger_dto import RatingLedgerEntryDTO


@pytest.fixture
def mock_uow():
    """Мок UnitOfWork с замокированными репозиториями."""
    uow = MagicMock()
    ledger_repo = AsyncMock()
    rating_repo = AsyncMock()

    return uow, ledger_repo, rating_repo


@pytest.fixture
def rating_service(mock_uow):
    """Создать RatingLedgerService с моком репозитория."""
    _, ledger_repo, _ = mock_uow
    return RatingLedgerService(ledger_repo)


class TestAwardWelcomeBonusUseCase:
    """Тесты для начисления приветственного бонуса."""

    @pytest.mark.asyncio
    async def test_award_welcome_bonus_first_time(
        self,
        rating_service,
        mock_uow,
    ):
        """Тест: бонус начисляется при первом добавлении в чат."""
        # Arrange
        uow, ledger_repo, rating_repo = mock_uow
        ledger_repo.has_any_entries_for_user_in_chat = AsyncMock(return_value=False)
        rating_repo.add = AsyncMock(return_value=100)
        ledger_repo.add = AsyncMock()

        use_case = AwardWelcomeBonusUseCase(
            rating_service=rating_service,
            rating_repo=rating_repo,
            ledger_repo=ledger_repo,
        )

        # Act
        result = await use_case.execute(uow=uow, chat_id=1, user_id=42)

        # Assert
        assert result is True
        ledger_repo.has_any_entries_for_user_in_chat.assert_called_once_with(
            user_id=42,
            chat_id=1,
        )
        rating_repo.add.assert_called_once_with(
            chat_id=1,
            user_id=42,
            value=100,
        )
        ledger_repo.add.assert_called_once()
        call_args = ledger_repo.add.call_args[0][0]
        assert isinstance(call_args, RatingLedgerEntryDTO)
        assert call_args.chat_id == 1
        assert call_args.user_id == 42
        assert call_args.amount == 100
        assert call_args.balance_after == 100
        assert call_args.operation_type == "bonus"
        assert call_args.operation_subtype == "welcome"
        assert call_args.source_type == "system"
        assert call_args.meta == {"reason": "welcome_bonus"}

    @pytest.mark.asyncio
    async def test_award_welcome_bonus_already_has_entries(
        self,
        rating_service,
        mock_uow,
    ):
        """Тест: бонус не начисляется, если уже есть записи в ledger."""
        # Arrange
        uow, ledger_repo, rating_repo = mock_uow
        ledger_repo.has_any_entries_for_user_in_chat = AsyncMock(return_value=True)

        use_case = AwardWelcomeBonusUseCase(
            rating_service=rating_service,
            rating_repo=rating_repo,
            ledger_repo=ledger_repo,
        )

        # Act
        result = await use_case.execute(uow=uow, chat_id=1, user_id=42)

        # Assert
        assert result is False
        ledger_repo.has_any_entries_for_user_in_chat.assert_called_once_with(
            user_id=42,
            chat_id=1,
        )
        ledger_repo.add.assert_not_called()
        rating_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_award_welcome_bonus_with_existing_balance(
        self,
        rating_service,
        mock_uow,
    ):
        """Тест: бонус корректно начисляется к существующему балансу."""
        # Arrange
        uow, ledger_repo, rating_repo = mock_uow
        ledger_repo.has_any_entries_for_user_in_chat = AsyncMock(return_value=False)
        rating_repo.add = AsyncMock(return_value=150)
        ledger_repo.add = AsyncMock()

        use_case = AwardWelcomeBonusUseCase(
            rating_service=rating_service,
            rating_repo=rating_repo,
            ledger_repo=ledger_repo,
        )

        # Act
        result = await use_case.execute(uow=uow, chat_id=1, user_id=42)

        # Assert
        assert result is True
        rating_repo.add.assert_called_once_with(
            chat_id=1,
            user_id=42,
            value=100,
        )
        ledger_repo.add.assert_called_once()
        call_args = ledger_repo.add.call_args[0][0]
        assert call_args.amount == 100
        assert call_args.balance_after == 150
