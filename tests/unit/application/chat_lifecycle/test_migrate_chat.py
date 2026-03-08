"""Тесты для MigrateChatUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat

from core.application.chat_lifecycle.migrate_chat import MigrateChatUseCase


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


class TestMigrateChatUseCase:
    """Тесты для MigrateChatUseCase."""

    @pytest.mark.asyncio
    async def test_migrate_chat_success(self, uow_factory, mock_uow):
        """Тест: успешная миграция чата."""
        # Arrange
        _, chat_repo = mock_uow

        # Чат с новым tg_id не существует
        chat_repo.get_by_tg_id = AsyncMock(side_effect=[
            None,  # new_tg_id не существует
            MagicMock()  # old_tg_id существует
        ])

        # Миграция успешна
        chat_repo.migrate_chat = AsyncMock(return_value=True)

        use_case = MigrateChatUseCase(uow_factory=uow_factory)

        old_chat = Chat(id=-100, type="group", title="Test Chat")
        new_chat = Chat(id=-1001234567890, type="supergroup", title="Test Chat")

        # Act
        await use_case.execute(old_chat=old_chat, new_chat=new_chat)

        # Assert
        assert chat_repo.get_by_tg_id.call_count == 2
        chat_repo.migrate_chat.assert_called_once_with(
            old_tg_id=-100,
            new_tg_id=-1001234567890,
        )

    @pytest.mark.asyncio
    async def test_migrate_chat_new_chat_already_exists(self, uow_factory, mock_uow):
        """Тест: чат с новым tg_id уже существует, миграция не требуется."""
        # Arrange
        _, chat_repo = mock_uow

        # Чат с новым tg_id уже существует
        existing_chat = MagicMock()
        chat_repo.get_by_tg_id = AsyncMock(return_value=existing_chat)

        use_case = MigrateChatUseCase(uow_factory=uow_factory)

        old_chat = Chat(id=-100, type="group", title="Test Chat")
        new_chat = Chat(id=-1001234567890, type="supergroup", title="Test Chat")

        # Act
        await use_case.execute(old_chat=old_chat, new_chat=new_chat)

        # Assert
        chat_repo.get_by_tg_id.assert_called_once_with(-1001234567890)
        # migrate_chat не должен быть вызван
        chat_repo.migrate_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_migrate_chat_old_chat_not_found_creates_new(self, uow_factory, mock_uow):
        """Тест: старый чат не найден, создаётся новый с новым ID."""
        # Arrange
        _, chat_repo = mock_uow

        # Чат с новым tg_id не существует, старый тоже не существует
        chat_repo.get_by_tg_id = AsyncMock(side_effect=[
            None,  # new_tg_id не существует
            None   # old_tg_id не существует
        ])

        # upsert для создания нового чата
        chat_repo.upsert = AsyncMock(return_value=MagicMock())

        use_case = MigrateChatUseCase(uow_factory=uow_factory)

        old_chat = Chat(id=-100, type="group", title="Test Chat")
        new_chat = Chat(id=-1001234567890, type="supergroup", title="Test Chat")

        # Act
        await use_case.execute(old_chat=old_chat, new_chat=new_chat)

        # Assert
        assert chat_repo.get_by_tg_id.call_count == 2
        # migrate_chat не должен быть вызван
        chat_repo.migrate_chat.assert_not_called()
        # upsert должен быть вызван для создания нового чата
        chat_repo.upsert.assert_called_once()
        call_args = chat_repo.upsert.call_args[0][0]
        assert call_args.id == -1001234567890

    @pytest.mark.asyncio
    async def test_migrate_chat_migration_failed(self, uow_factory, mock_uow):
        """Тест: миграция не удалась (возврат False)."""
        # Arrange
        _, chat_repo = mock_uow

        # Чат с новым tg_id не существует, старый существует
        chat_repo.get_by_tg_id = AsyncMock(side_effect=[
            None,  # new_tg_id не существует
            MagicMock()  # old_tg_id существует
        ])

        # Миграция не успешна
        chat_repo.migrate_chat = AsyncMock(return_value=False)

        use_case = MigrateChatUseCase(uow_factory=uow_factory)

        old_chat = Chat(id=-100, type="group", title="Test Chat")
        new_chat = Chat(id=-1001234567890, type="supergroup", title="Test Chat")

        # Act
        await use_case.execute(old_chat=old_chat, new_chat=new_chat)

        # Assert
        assert chat_repo.get_by_tg_id.call_count == 2
        chat_repo.migrate_chat.assert_called_once_with(
            old_tg_id=-100,
            new_tg_id=-1001234567890,
        )
