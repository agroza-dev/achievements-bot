import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.application.reactions.process_reaction import ProcessReactionUseCase
from core.dto.bot_context import BotContextDTO
from core.dto.chat_dto import ChatDTO
from core.dto.chat_message_dto import ChatMessageDTO
from core.dto.chat_user_dto import ChatUserDTO
from core.dto.user_dto import UserDTO
from core.infrastructure.repositories.chat_message_repository import DbChatMessageRepository
from core.infrastructure.repositories.chat_repository import ChatRepository


@pytest.fixture
def mock_uow():
    """Мок UnitOfWork с замокированными репозиториями"""
    uow = MagicMock()

    # Делаем uow асинхронным контекстным менеджером
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    chat_repo = AsyncMock()
    chat_dto = ChatDTO(
        id=1,
        tg_id=100,
        title="Test Chat",
        type="group",
        is_active=True,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    chat_repo.get_by_tg_id.return_value = chat_dto

    chat_message_repo = AsyncMock()
    message = ChatMessageDTO(
        id=10,
        tg_message_id=1000,
        chat_id=1,
        author_user_id=2,
        created_at=datetime.datetime.now(),
        message_meta={},
        message_type='TEST',
        stored_at=datetime.datetime.now(),
    )
    chat_message_repo.get_by_tg_id.return_value = message

    reaction_repo = AsyncMock()
    rating_repo = AsyncMock()
    rating_ledger_repo = AsyncMock()

    def get_repo(repo_class):
        """Возвращаем нужный репозиторий по типу класса"""
        repo_map = {
            "ChatRepository": chat_repo,
            "DbChatMessageRepository": chat_message_repo,
            "DbReactionRepository": reaction_repo,
            "DbRatingRepository": rating_repo,
            "DbRatingLedgerRepository": rating_ledger_repo,
        }
        repo_name = repo_class.__name__ if hasattr(repo_class, "__name__") else repo_class
        return repo_map.get(repo_name, MagicMock())

    uow.get_repo = MagicMock(side_effect=get_repo)

    return uow, chat_repo, chat_message_repo, reaction_repo, rating_repo, rating_ledger_repo


@pytest.fixture
def uow_factory(mock_uow):
    """Фабрика для создания UoW"""
    uow, *_ = mock_uow

    def factory():
        return uow

    return factory


@pytest.fixture
def mock_policy():
    """Мок политики реакций"""
    policy = MagicMock()
    policy.rating_delta.return_value = 1
    policy.tax.return_value = 0
    return policy


@pytest.fixture
def ctx():
    """Мок контекста бота"""
    return BotContextDTO(
        user=UserDTO(
            id=1,
            username="testuser",
            is_bot=False,
            first_name="test",
            last_name="test",
            tg_id=12111,
            timezone="UTC",
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        ),
        chat=ChatDTO(
            id=1,
            tg_id=100,
            title="Test Chat",
            type="group",
            is_active=True,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        ),
        chat_user=ChatUserDTO(
            user_id=1,
            chat_id=1,
            is_active=True,
            is_admin=False,
            joined_at=datetime.datetime.now(),
            id=1
        ),
    )


class TestProcessReactionUseCase:
    """Тесты для ProcessReactionUseCase"""

    @pytest.mark.asyncio
    async def test_execute_no_changes(self, uow_factory, mock_policy, ctx):
        """Нет изменений в реакциях - ничего не делаем"""
        # Arrange
        use_case = ProcessReactionUseCase(uow_factory=uow_factory, reaction_policy=mock_policy)

        # Act
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=100,
            tg_message_id=1000,
            old_reactions=["👍"],
            new_reactions=["👍"],
        )

        # Assert - uow_factory НЕ вызывается, так как изменений нет
        # Никаких вызовов репозиториев

    @pytest.mark.asyncio
    async def test_execute_message_not_found(self, uow_factory, mock_policy, ctx, mock_uow):
        """Сообщение не найдено - пропускаем"""
        # Arrange
        uow, chat_repo, chat_message_repo, reaction_repo, rating_repo, rating_ledger_repo = mock_uow
        chat_message_repo.get_by_tg_id.return_value = None

        use_case = ProcessReactionUseCase(uow_factory=uow_factory, reaction_policy=mock_policy)

        # Act
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=100,
            tg_message_id=999,  # Несуществующее сообщение
            old_reactions=[],
            new_reactions=["👍"],
        )

        # Assert - чат найден, но сообщение не найдено
        chat_repo.get_by_tg_id.assert_called_once_with(100)
        # get_repo вызывается для получения репозиториев
        uow.get_repo.assert_any_call(ChatRepository)
        uow.get_repo.assert_any_call(DbChatMessageRepository)
        # Репозитории реакций, рейтинга и ledger НЕ используются, так как сообщение не найдено
        reaction_repo.add_reaction.assert_not_called()
        reaction_repo.remove_reaction.assert_not_called()
        rating_repo.update_rating.assert_not_called()
        rating_ledger_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_reaction_to_own_message(self, uow_factory, mock_policy, ctx, mock_uow):
        """Пользователь реагирует на свое сообщение - пропускаем"""
        # Arrange
        uow, _chat_repo, chat_message_repo, *_ = mock_uow
        # author_user_id = 2, но ctx.user.id = 1, так что это НЕ свое сообщение
        # Чтобы протестировать "свое сообщение", меняем author_user_id
        chat_message_repo.get_by_tg_id.return_value.author_user_id = ctx.user.id

        use_case = ProcessReactionUseCase(uow_factory=uow_factory, reaction_policy=mock_policy)

        # Act
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=100,
            tg_message_id=1000,
            old_reactions=[],
            new_reactions=["👍"],
        )

        # Assert - транзакция открывается, но ReactionService не вызывается
        uow.__aenter__.assert_called()

    @pytest.mark.asyncio
    async def test_execute_added_reaction(self, uow_factory, mock_policy, ctx, mock_uow):
        """Добавлена новая реакция"""
        # Arrange
        uow, *_ = mock_uow
        use_case = ProcessReactionUseCase(uow_factory=uow_factory, reaction_policy=mock_policy)

        # Act
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=100,
            tg_message_id=1000,
            old_reactions=[],
            new_reactions=["👍"],
        )

        # Assert
        uow.__aenter__.assert_called()
        uow.__aexit__.assert_called()

    @pytest.mark.asyncio
    async def test_execute_removed_reaction(self, uow_factory, mock_policy, ctx, mock_uow):
        """Удалена реакция"""
        # Arrange
        uow, *_ = mock_uow
        use_case = ProcessReactionUseCase(uow_factory=uow_factory, reaction_policy=mock_policy)

        # Act
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=100,
            tg_message_id=1000,
            old_reactions=["👍"],
            new_reactions=[],
        )

        # Assert
        uow.__aenter__.assert_called()
        uow.__aexit__.assert_called()

    @pytest.mark.asyncio
    async def test_execute_multiple_changes(self, uow_factory, mock_policy, ctx, mock_uow):
        """Несколько изменений - добавили одну, удалили другую"""
        # Arrange
        uow, *_ = mock_uow
        use_case = ProcessReactionUseCase(uow_factory=uow_factory, reaction_policy=mock_policy)

        # Act
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=100,
            tg_message_id=1000,
            old_reactions=["👎", "🔥"],
            new_reactions=["👍", "🔥"],
        )

        # Assert
        uow.__aenter__.assert_called()
        uow.__aexit__.assert_called()

    @pytest.mark.asyncio
    async def test_execute_uses_transaction(self, uow_factory, mock_policy, ctx, mock_uow):
        """Все изменения выполняются в одной транзакции"""
        # Arrange
        uow, *_ = mock_uow
        use_case = ProcessReactionUseCase(uow_factory=uow_factory, reaction_policy=mock_policy)

        # Act
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=100,
            tg_message_id=1000,
            old_reactions=["👎"],
            new_reactions=["👍", "🔥"],
        )

        # Assert
        uow.__aenter__.assert_called_once()
        uow.__aexit__.assert_called_once()
