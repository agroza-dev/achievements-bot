"""Тесты для new_chat_title_handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat

from bot.handlers.new_chat_title_handler import new_chat_title_handler


@pytest.fixture
def mock_context():
    """Создать мок context."""
    context = MagicMock()

    # Мок контейнера
    container = MagicMock()
    use_case = AsyncMock()  # Мок UseCase
    container.get_update_chat_title_use_case = MagicMock(return_value=use_case)
    context.bot_data = {"container": container}

    return context, use_case


@pytest.fixture
def mock_update_with_new_title():
    """Создать мок update с новым названием чата."""
    update = MagicMock()

    # Создаём чат
    chat = Chat(
        id=-1001234567890,
        type="supergroup",
        title="New Chat Title",
    )

    # Создаём сообщение с new_chat_title
    message = MagicMock()
    message.chat = chat
    message.new_chat_title = "New Chat Title"
    message.from_user = None

    update.message = message

    return update


class TestNewChatTitleHandler:
    """Тесты для обработчика изменения названия чата."""

    @pytest.mark.asyncio
    async def test_new_title_calls_use_case(
        self,
        mock_context,
        mock_update_with_new_title,
    ):
        """Тест: при изменении названия вызывается UseCase."""
        # Arrange
        context, use_case = mock_context
        update = mock_update_with_new_title

        # Act
        await new_chat_title_handler(update, context)

        # Assert
        use_case.execute.assert_called_once()
        call_args = use_case.execute.call_args
        assert call_args[1]["tg_chat"].id == -1001234567890
        assert call_args[1]["tg_chat"].title == "New Chat Title"

    @pytest.mark.asyncio
    async def test_handler_ignores_no_new_title(
        self,
        mock_context,
    ):
        """Тест: обработчик игнорирует сообщения без new_chat_title."""
        # Arrange
        context, use_case = mock_context
        update = MagicMock()

        message = MagicMock()
        message.new_chat_title = None  # Нет нового названия
        update.message = message

        # Act
        await new_chat_title_handler(update, context)

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
        await new_chat_title_handler(update, context)

        # Assert
        # UseCase не должен быть вызван
        use_case.execute.assert_not_called()
