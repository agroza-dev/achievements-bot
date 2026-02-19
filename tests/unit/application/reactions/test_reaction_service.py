import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.application.reactions.reaction_intent import ReactionKind
from core.application.reactions.reaction_service import ReactionService
from core.domain.reactions.reaction_policy import ReactionPolicy
from core.dto.bot_context import BotContextDTO
from core.dto.chat_dto import ChatDTO
from core.dto.chat_user_dto import ChatUserDTO
from core.dto.rating_ledger_dto import RatingLedgerEntryDTO
from core.dto.reaction_dto import ReactionDTO
from core.dto.user_dto import UserDTO


@pytest.fixture
def mock_policy():
    """Мок политики реакций"""
    policy = MagicMock(spec=ReactionPolicy)
    policy.can_add.return_value = True
    policy.rating_delta.return_value = 1
    policy.tax.return_value = 0
    return policy


@pytest.fixture
def mock_reaction_repo():
    """Мок репозитория реакций"""
    repo = AsyncMock()
    repo.list_for_update = AsyncMock(return_value=[])
    repo.add = AsyncMock()
    repo.delete_if_exists = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_rating_repo():
    """Мок репозитория рейтинга"""
    repo = AsyncMock()
    repo.add = AsyncMock(return_value=100)
    return repo


@pytest.fixture
def mock_ledger_repo():
    """Мок репозитория ledger"""
    repo = AsyncMock()
    repo.add = AsyncMock()
    repo.mark_as_reverted_by_emoji = AsyncMock()
    return repo


@pytest.fixture
def service(mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy):
    """Создаем сервис с замокированными зависимостями"""
    return ReactionService(
        reaction_repo=mock_reaction_repo,
        rating_repo=mock_rating_repo,
        ledger_repo=mock_ledger_repo,
        policy=mock_policy,
    )


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
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        ),
        chat=ChatDTO(
            id=1,
            tg_id=100,
            title="Test Chat",
            settings='{}',
            is_active=True,
            type='',
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


@pytest.fixture
def message():
    """Мок сообщения"""
    msg = MagicMock()
    msg.tg_message_id = 10
    msg.id = 100
    msg.author_user_id = 2
    return msg


class TestReactionServiceAddReaction:
    """Тесты для метода add_reaction"""

    @pytest.mark.asyncio
    async def test_add_reaction_success(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Успешное добавление реакции"""
        # Arrange
        chat_id = 1
        emoji = "👍"
        mock_policy.kind.return_value = ReactionKind.POSITIVE

        # Act
        await service.add_reaction(ctx=ctx, chat_id=chat_id, message=message, emoji=emoji)

        # Assert
        mock_reaction_repo.list_for_update.assert_called_once_with(
            chat_id=chat_id,
            message_id=message.tg_message_id,
            from_user_id=ctx.user.id,
        )

        mock_policy.can_add.assert_called_once()

        mock_reaction_repo.add.assert_called_once()
        added_reaction = mock_reaction_repo.add.call_args[0][0]
        assert added_reaction.chat_id == chat_id
        assert added_reaction.message_id == message.tg_message_id
        assert added_reaction.from_user_id == ctx.user.id
        assert added_reaction.to_user_id == message.author_user_id
        assert added_reaction.reaction == emoji

        mock_rating_repo.add.assert_called_once_with(chat_id, message.author_user_id, 1)
        mock_ledger_repo.add.assert_called_once()
        ledger_entry = mock_ledger_repo.add.call_args[0][0]
        assert isinstance(ledger_entry, RatingLedgerEntryDTO)
        assert ledger_entry.operation_type == "reaction"
        assert ledger_entry.operation_subtype == ReactionKind.POSITIVE.value

    @pytest.mark.asyncio
    async def test_add_reaction_policy_forbids(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Политика запрещает добавление реакции"""
        # Arrange
        mock_policy.can_add.return_value = False

        # Act
        await service.add_reaction(ctx=ctx, chat_id=1, message=message, emoji="👍")

        # Assert
        mock_policy.can_add.assert_called_once()
        mock_reaction_repo.add.assert_not_called()
        mock_rating_repo.add.assert_not_called()
        mock_ledger_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_reaction_already_exists(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Реакция уже существует - не добавляем дубликат"""
        # Arrange
        existing_reaction = ReactionDTO(
            chat_id=1,
            message_id=10,
            from_user_id=ctx.user.id,
            to_user_id=message.author_user_id,
            reaction="👍",
        )
        mock_reaction_repo.list_for_update.return_value = [existing_reaction]

        # Act
        await service.add_reaction(ctx=ctx, chat_id=1, message=message, emoji="👍")

        # Assert
        mock_reaction_repo.add.assert_not_called()
        mock_rating_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_reaction_max_reactions_reached(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Достигнут лимит реакций - политика запрещает"""
        # Arrange
        mock_policy.can_add.return_value = False

        # Act
        await service.add_reaction(ctx=ctx, chat_id=1, message=message, emoji="👍")

        # Assert
        mock_reaction_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_reaction_with_tax(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Добавление реакции с налогом"""
        # Arrange
        mock_policy.kind.return_value = ReactionKind.POSITIVE
        mock_policy.tax.return_value = 5

        # Act
        await service.add_reaction(ctx=ctx, chat_id=1, message=message, emoji="🔥")

        # Assert - налог списывается с того, кто поставил реакцию
        assert mock_rating_repo.add.call_count == 2

        # Первый вызов - рейтинг автора сообщения
        call1 = mock_rating_repo.add.call_args_list[0]
        assert call1[0][0] == 1  # chat_id
        assert call1[0][1] == message.author_user_id  # user_id
        assert call1[0][2] == 1  # delta

        # Второй вызов - налог с того, кто поставил реакцию
        call2 = mock_rating_repo.add.call_args_list[1]
        assert call2[0][0] == 1  # chat_id
        assert call2[0][1] == ctx.user.id  # user_id - плательщик налога
        assert call2[0][2] == -5  # tax (negative)

        # Ledger вызывается 2 раза - для рейтинга и для налога
        assert mock_ledger_repo.add.call_count == 2

    @pytest.mark.asyncio
    async def test_add_reaction_zero_delta(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Реакция с нулевой дельтой рейтинга"""
        # Arrange
        mock_policy.rating_delta.return_value = 0

        # Act
        await service.add_reaction(ctx=ctx, chat_id=1, message=message, emoji="👌")

        # Assert
        mock_reaction_repo.add.assert_called_once()  # Реакция добавляется
        mock_rating_repo.add.assert_not_called()  # Но рейтинг не меняется
        mock_ledger_repo.add.assert_not_called()


class TestReactionServiceRemoveReaction:
    """Тесты для метода remove_reaction"""

    @pytest.mark.asyncio
    async def test_remove_reaction_success(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Успешное удаление реакции"""
        # Arrange
        emoji = "👍"
        mock_policy.kind.return_value = ReactionKind.POSITIVE
        mock_rating_repo.add.return_value = 99

        # Act
        await service.remove_reaction(ctx=ctx, chat_id=1, message=message, emoji=emoji)

        # Assert
        mock_reaction_repo.delete_if_exists.assert_called_once_with(
            chat_id=1,
            message_id=message.tg_message_id,
            from_user_id=ctx.user.id,
            reaction=emoji,
        )

        mock_ledger_repo.mark_as_reverted_by_emoji.assert_called_once()
        call_args = mock_ledger_repo.mark_as_reverted_by_emoji.call_args[1]
        assert call_args["emoji"] == emoji

        mock_rating_repo.add.assert_called_once_with(1, message.author_user_id, -1)

        mock_ledger_repo.add.assert_called_once()
        ledger_entry = mock_ledger_repo.add.call_args[0][0]
        assert ledger_entry.operation_type == "reaction_revert"
        assert ledger_entry.operation_subtype == ReactionKind.POSITIVE.value

    @pytest.mark.asyncio
    async def test_remove_reaction_not_found(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Удаление несуществующей реакции"""
        # Arrange
        mock_reaction_repo.delete_if_exists.return_value = False

        # Act
        await service.remove_reaction(ctx=ctx, chat_id=1, message=message, emoji="👍")

        # Assert
        mock_reaction_repo.delete_if_exists.assert_called_once()
        mock_ledger_repo.mark_as_reverted_by_emoji.assert_not_called()
        mock_rating_repo.add.assert_not_called()
        mock_ledger_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_reaction_zero_delta(self, service, mock_reaction_repo, mock_rating_repo, mock_ledger_repo, mock_policy, ctx, message):
        """Удаление реакции с нулевой дельтой - рейтинг не меняется"""
        # Arrange
        mock_policy.rating_delta.return_value = 0

        # Act
        await service.remove_reaction(ctx=ctx, chat_id=1, message=message, emoji="👌")

        # Assert
        mock_reaction_repo.delete_if_exists.assert_called_once()
        mock_ledger_repo.mark_as_reverted_by_emoji.assert_not_called()  # Не отменяем ledger
        mock_rating_repo.add.assert_not_called()  # Не меняем рейтинг
