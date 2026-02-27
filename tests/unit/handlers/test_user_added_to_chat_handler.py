"""Тесты для user_added_to_chat_handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, User

from bot.handlers.user_added_to_chat_handler import user_added_to_chat_handler


@pytest.fixture
def mock_context():
    """Создать мок context."""
    context = MagicMock()

    # Мок контейнера
    container = MagicMock()
    use_case = AsyncMock()  # Мок UseCase
    container.get_user_added_to_chat_use_case = MagicMock(return_value=use_case)
    context.bot_data = {"container": container}

    return context, use_case


@pytest.fixture
def mock_update_with_new_user():
    """Создать мок update с новым пользователем."""
    update = MagicMock()

    # Создаём пользователя
    new_user = User(
        id=12345,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
    )

    # Создаём чат
    chat = Chat(
        id=-1001234567890,
        type="group",
        title="Test Chat",
    )

    # Создаём сообщение
    message = MagicMock()
    message.new_chat_members = [new_user]
    message.chat = chat
    message.from_user = User(
        id=67890,
        is_bot=False,
        first_name="Admin",
        username="admin",
    )

    update.message = message

    return update


class TestUserAddedToChatHandler:
    """Тесты для обработчика добавления пользователя в чат."""

    @pytest.mark.asyncio
    async def test_user_added_calls_use_case(
        self,
        mock_context,
        mock_update_with_new_user,
    ):
        """Тест: при добавлении пользователя вызывается UseCase."""
        # Arrange
        context, use_case = mock_context
        update = mock_update_with_new_user

        # Act
        await user_added_to_chat_handler(update, context)

        # Assert
        use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handler_ignores_bots(
        self,
        mock_context,
    ):
        """Тест: обработчик игнорирует ботов."""
        # Arrange
        context, use_case = mock_context
        update = MagicMock()

        # Создаём бота (не обычного пользователя)
        bot_user = User(
            id=99999,
            is_bot=True,  # Это бот
            first_name="Bot",
            username="bot",
        )

        message = MagicMock()
        message.new_chat_members = [bot_user]
        update.message = message

        # Act
        await user_added_to_chat_handler(update, context)

        # Assert
        # UseCase не должен быть вызван
        use_case.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_handler_multiple_users(
        self,
        mock_context,
    ):
        """Тест: обработчик корректно обрабатывает нескольких пользователей."""
        # Arrange
        context, use_case = mock_context
        update = MagicMock()

        # Создаём нескольких пользователей
        user1 = User(id=1, is_bot=False, first_name="User1", username="user1")
        user2 = User(id=2, is_bot=False, first_name="User2", username="user2")
        user3 = User(id=3, is_bot=False, first_name="User3", username="user3")

        chat = Chat(id=-100, type="group", title="Test")
        message = MagicMock()
        message.new_chat_members = [user1, user2, user3]
        message.chat = chat
        message.from_user = User(id=999, is_bot=False, first_name="Admin", username="admin")
        update.message = message

        # Act
        await user_added_to_chat_handler(update, context)

        # Assert
        # UseCase должен быть вызван 3 раза (для каждого пользователя)
        assert use_case.execute.call_count == 3
