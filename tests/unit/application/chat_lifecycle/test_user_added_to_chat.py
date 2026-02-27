"""Тесты для UserAddedToChatUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, User

from core.application.chat_lifecycle.user_added_to_chat import UserAddedToChatUseCase


@pytest.fixture
def mock_uow():
    """Мок UnitOfWork с замокированными репозиториями."""
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    user_repo = AsyncMock()
    chat_repo = AsyncMock()
    chat_user_repo = AsyncMock()
    rating_repo = AsyncMock()
    ledger_repo = AsyncMock()

    def get_repo(repo_class):
        repo_map = {
            "UserRepository": user_repo,
            "ChatRepository": chat_repo,
            "ChatUserRepository": chat_user_repo,
            "DbRatingRepository": rating_repo,
            "DbRatingLedgerRepository": ledger_repo,
        }
        repo_name = repo_class.__name__ if hasattr(repo_class, "__name__") else repo_class
        return repo_map.get(repo_name, MagicMock())

    uow.get_repo = MagicMock(side_effect=get_repo)
    return uow, user_repo, chat_repo, chat_user_repo, rating_repo, ledger_repo


@pytest.fixture
def uow_factory(mock_uow):
    """Фабрика для создания UoW."""
    uow, *_ = mock_uow

    def factory():
        return uow

    return factory


class TestUserAddedToChatUseCase:
    """Тесты для UserAddedToChatUseCase."""

    @pytest.mark.asyncio
    async def test_user_added_to_chat(self, uow_factory, mock_uow):
        """Тест: пользователь добавляется в чат с начислением бонуса."""
        # Arrange
        _, user_repo, chat_repo, chat_user_repo, rating_repo, ledger_repo = mock_uow

        # Мок возврата существующих чата и пользователя
        chat_dto = MagicMock()
        chat_dto.id = 1
        chat_repo.get_by_tg_id = AsyncMock(return_value=chat_dto)

        user_dto = MagicMock()
        user_dto.id = 100
        user_repo.get_by_tg_id = AsyncMock(return_value=user_dto)

        # Мок проверки ledger (записей нет)
        ledger_repo.has_any_entries_for_user_in_chat = AsyncMock(return_value=False)

        # Мок начисления бонуса
        rating_repo.add = AsyncMock(return_value=100)
        ledger_repo.add = AsyncMock()

        use_case = UserAddedToChatUseCase(uow_factory=uow_factory)

        tg_chat = Chat(id=-100, type="group", title="Test Chat")
        tg_user = User(id=123, is_bot=False, first_name="Test", username="testuser")
        added_by = User(id=456, is_bot=False, first_name="Admin", username="admin")

        # Act
        await use_case.execute(tg_chat=tg_chat, tg_user=tg_user, added_by=added_by)

        # Assert
        chat_repo.get_by_tg_id.assert_called_once_with(-100)
        user_repo.get_by_tg_id.assert_called_once_with(123)
        chat_user_repo.add_user_to_chat.assert_called_once_with(
            chat_id=1,
            user_id=100,
            is_admin=False,
        )
        ledger_repo.has_any_entries_for_user_in_chat.assert_called_once()
        rating_repo.add.assert_called_once_with(
            chat_id=1,
            user_id=100,
            value=100,
        )

    @pytest.mark.asyncio
    async def test_user_added_to_chat_creates_user_if_not_exists(
        self, uow_factory, mock_uow
    ):
        """Тест: пользователь создаётся если не существует."""
        # Arrange
        _, user_repo, chat_repo, _, rating_repo, ledger_repo = mock_uow

        # Пользователь не существует
        chat_dto = MagicMock()
        chat_dto.id = 1
        chat_repo.get_by_tg_id = AsyncMock(return_value=chat_dto)
        user_repo.get_by_tg_id = AsyncMock(return_value=None)

        # Мок создания пользователя
        new_user = MagicMock()
        new_user.id = 100
        user_repo.upsert = AsyncMock(return_value=new_user)

        # Мок проверки ledger (записей нет)
        ledger_repo.has_any_entries_for_user_in_chat = AsyncMock(return_value=False)
        rating_repo.add = AsyncMock(return_value=100)
        ledger_repo.add = AsyncMock()

        use_case = UserAddedToChatUseCase(uow_factory=uow_factory)

        tg_chat = Chat(id=-100, type="group", title="Test Chat")
        tg_user = User(id=123, is_bot=False, first_name="Test", username="testuser")

        # Act
        await use_case.execute(tg_chat=tg_chat, tg_user=tg_user)

        # Assert
        user_repo.get_by_tg_id.assert_called_once_with(123)
        user_repo.upsert.assert_called_once_with(tg_user)

    @pytest.mark.asyncio
    async def test_user_added_to_chat_creates_chat_if_not_exists(
        self, uow_factory, mock_uow
    ):
        """Тест: чат создаётся если не существует."""
        # Arrange
        _, user_repo, chat_repo, _, rating_repo, ledger_repo = mock_uow

        # Чат не существует
        chat_repo.get_by_tg_id = AsyncMock(return_value=None)
        chat_dto = MagicMock()
        chat_dto.id = 1
        chat_repo.upsert = AsyncMock(return_value=chat_dto)

        user_dto = MagicMock()
        user_dto.id = 100
        user_repo.get_by_tg_id = AsyncMock(return_value=user_dto)

        # Мок проверки ledger (записей нет)
        ledger_repo.has_any_entries_for_user_in_chat = AsyncMock(return_value=False)
        rating_repo.add = AsyncMock(return_value=100)
        ledger_repo.add = AsyncMock()

        use_case = UserAddedToChatUseCase(uow_factory=uow_factory)

        tg_chat = Chat(id=-100, type="group", title="Test Chat")
        tg_user = User(id=123, is_bot=False, first_name="Test", username="testuser")

        # Act
        await use_case.execute(tg_chat=tg_chat, tg_user=tg_user)

        # Assert
        chat_repo.get_by_tg_id.assert_called_once_with(-100)
        chat_repo.upsert.assert_called_once_with(tg_chat)

    @pytest.mark.asyncio
    async def test_user_added_no_bonus_if_already_has_entries(
        self, uow_factory, mock_uow
    ):
        """Тест: бонус не начисляется если уже есть записи в ledger."""
        # Arrange
        _, user_repo, chat_repo, chat_user_repo, rating_repo, ledger_repo = mock_uow

        chat_dto = MagicMock()
        chat_dto.id = 1
        chat_repo.get_by_tg_id = AsyncMock(return_value=chat_dto)

        user_dto = MagicMock()
        user_dto.id = 100
        user_repo.get_by_tg_id = AsyncMock(return_value=user_dto)

        # Мок проверки ledger (записи есть!)
        ledger_repo.has_any_entries_for_user_in_chat = AsyncMock(return_value=True)

        use_case = UserAddedToChatUseCase(uow_factory=uow_factory)

        tg_chat = Chat(id=-100, type="group", title="Test Chat")
        tg_user = User(id=123, is_bot=False, first_name="Test", username="testuser")

        # Act
        await use_case.execute(tg_chat=tg_chat, tg_user=tg_user)

        # Assert
        chat_user_repo.add_user_to_chat.assert_called_once()
        ledger_repo.has_any_entries_for_user_in_chat.assert_called_once()
        # Бонус не должен быть начислен
        rating_repo.add.assert_not_called()
        ledger_repo.add.assert_not_called()
