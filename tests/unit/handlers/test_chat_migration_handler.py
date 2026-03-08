"""Тесты для chat_migration_handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat

from bot.handlers.chat_migration_handler import chat_migration_handler


@pytest.fixture
def mock_context():
    """Создать мок context."""
    context = MagicMock()

    # Мок контейнера
    container = MagicMock()
    use_case = AsyncMock()  # Мок UseCase
    container.get_migrate_chat_use_case = MagicMock(return_value=use_case)
    context.bot_data = {"container": container}

    return context, use_case


@pytest.fixture
def mock_update_with_migrate_to():
    """Создать мок update с событием migrate_to_chat_id."""
    update = MagicMock()

    # Создаём старый чат (группа)
    old_chat = Chat(
        id=-100,
        type="group",
        title="Test Chat",
        username="testchat",
    )

    # Создаём сообщение с migrate_to_chat_id
    message = MagicMock()
    message.chat = old_chat
    message.migrate_to_chat_id = -1001234567890  # Новый ID супергруппы
    message.migrate_from_chat_id = None
    message.from_user = None

    update.message = message

    return update


@pytest.fixture
def mock_update_with_migrate_from():
    """Создать мок update с событием migrate_from_chat_id."""
    update = MagicMock()

    # Создаём новый чат (супергруппа)
    new_chat = Chat(
        id=-1001234567890,
        type="supergroup",
        title="Test Chat",
        username="testchat",
    )

    # Создаём сообщение с migrate_from_chat_id
    message = MagicMock()
    message.chat = new_chat
    message.migrate_to_chat_id = None
    message.migrate_from_chat_id = -100  # Старый ID группы
    message.from_user = None

    update.message = message

    return update


class TestChatMigrationHandler:
    """Тесты для обработчика миграции чата."""

    @pytest.mark.asyncio
    async def test_migration_with_migrate_to(
        self,
        mock_context,
        mock_update_with_migrate_to,
    ):
        """Тест: миграция с migrate_to_chat_id."""
        # Arrange
        context, use_case = mock_context
        update = mock_update_with_migrate_to

        # Act
        await chat_migration_handler(update, context)

        # Assert
        use_case.execute.assert_called_once()
        call_args = use_case.execute.call_args
        assert call_args[1]["old_chat"].id == -100
        assert call_args[1]["new_chat"].id == -1001234567890

    @pytest.mark.asyncio
    async def test_migration_with_migrate_from(
        self,
        mock_context,
        mock_update_with_migrate_from,
    ):
        """Тест: миграция с migrate_from_chat_id."""
        # Arrange
        context, use_case = mock_context
        update = mock_update_with_migrate_from

        # Act
        await chat_migration_handler(update, context)

        # Assert
        use_case.execute.assert_called_once()
        call_args = use_case.execute.call_args
        assert call_args[1]["old_chat"].id == -100
        assert call_args[1]["new_chat"].id == -1001234567890

    @pytest.mark.asyncio
    async def test_handler_ignores_no_migration(
        self,
        mock_context,
    ):
        """Тест: обработчик игнорирует сообщения без миграции."""
        # Arrange
        context, use_case = mock_context
        update = MagicMock()

        message = MagicMock()
        message.migrate_to_chat_id = None
        message.migrate_from_chat_id = None
        update.message = message

        # Act
        await chat_migration_handler(update, context)

        # Assert
        # UseCase не должен быть вызван
        use_case.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_handler_ignores_no_message(
        self,
        mock_context,
    ):
        """Тест: обработчик игнорирует отсутствие сообщения."""
        # Arrange
        context, use_case = mock_context
        update = MagicMock()
        update.message = None  # Нет сообщения

        # Act
        await chat_migration_handler(update, context)

        # Assert
        # UseCase не должен быть вызван
        use_case.execute.assert_not_called()
