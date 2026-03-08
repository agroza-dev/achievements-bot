"""Тесты для UpdateChatTitleUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat

from core.application.chat_lifecycle.update_chat_title import UpdateChatTitleUseCase


@pytest.fixture
def mock_uow():
    """Мок UnitOfWork с замокированными репозиториями."""
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    chat_repo = AsyncMock()

    def get_repo(repo_class):
        repo_map = {
            "ChatRepository": chat_repo,
        }
        repo_name = repo_class.__name__ if hasattr(repo_class, "__name__") else repo_class
        return repo_map.get(repo_name, MagicMock())

    uow.get_repo = MagicMock(side_effect=get_repo)
    return uow, chat_repo


@pytest.fixture
def uow_factory(mock_uow):
    """Фабрика для создания UoW."""
    uow, *_ = mock_uow

    def factory():
        return uow

    return factory


class TestUpdateChatTitleUseCase:
    """Тесты для UpdateChatTitleUseCase."""

    @pytest.mark.asyncio
    async def test_update_chat_title_success(self, uow_factory, mock_uow):
        """Тест: успешное обновление названия чата."""
        # Arrange
        _, chat_repo = mock_uow

        # Чат существует
        chat_dto = MagicMock()
        chat_repo.get_by_tg_id = AsyncMock(return_value=chat_dto)

        # Обновление успешно
        chat_repo.update_title = AsyncMock(return_value=True)

        use_case = UpdateChatTitleUseCase(uow_factory=uow_factory)

        tg_chat = Chat(id=-1001234567890, type="supergroup", title="New Title")

        # Act
        await use_case.execute(tg_chat=tg_chat)

        # Assert
        chat_repo.get_by_tg_id.assert_called_once_with(-1001234567890)
        chat_repo.update_title.assert_called_once_with(
            tg_id=-1001234567890,
            new_title="New Title",
        )

    @pytest.mark.asyncio
    async def test_update_chat_title_not_found(self, uow_factory, mock_uow):
        """Тест: чат не найден, обновление не выполняется."""
        # Arrange
        _, chat_repo = mock_uow

        # Чат не существует
        chat_repo.get_by_tg_id = AsyncMock(return_value=None)

        use_case = UpdateChatTitleUseCase(uow_factory=uow_factory)

        tg_chat = Chat(id=-1001234567890, type="supergroup", title="New Title")

        # Act
        await use_case.execute(tg_chat=tg_chat)

        # Assert
        chat_repo.get_by_tg_id.assert_called_once_with(-1001234567890)
        # update_title не должен быть вызван
        chat_repo.update_title.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_chat_title_update_failed(self, uow_factory, mock_uow):
        """Тест: обновление названия не удалось."""
        # Arrange
        _, chat_repo = mock_uow

        # Чат существует
        chat_dto = MagicMock()
        chat_repo.get_by_tg_id = AsyncMock(return_value=chat_dto)

        # Обновление не успешно
        chat_repo.update_title = AsyncMock(return_value=False)

        use_case = UpdateChatTitleUseCase(uow_factory=uow_factory)

        tg_chat = Chat(id=-1001234567890, type="supergroup", title="New Title")

        # Act
        await use_case.execute(tg_chat=tg_chat)

        # Assert
        chat_repo.get_by_tg_id.assert_called_once_with(-1001234567890)
        chat_repo.update_title.assert_called_once_with(
            tg_id=-1001234567890,
            new_title="New Title",
        )
