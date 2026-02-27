"""Dependency Injection Container для управления зависимостями приложения."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from telegram import Bot

from core.application.chat_lifecycle.bot_added_to_chat import BotAddedToChatUseCase
from core.application.chat_lifecycle.user_added_to_chat import UserAddedToChatUseCase
from core.application.chat_lifecycle.user_left_chat import UserLeftChatUseCase
from core.application.stats.get_chat_leaderboard import GetChatLeaderboardUseCase
from core.application.stats.get_personal_stats import GetPersonalStatsUseCase
from core.application.stats.get_user_chats import GetUserChatsUseCase
from core.application.transfers.transfer_points_use_case import TransferPointsUseCase
from core.domain.messages.chat_message_policy import ChatMessagePolicy
from core.domain.messages.default_chat_message_policy import DefaultChatMessagePolicy
from core.domain.reactions.default_reaction_policy import DefaultReactionPolicy
from core.domain.reactions.reaction_policy import ReactionPolicy
from core.domain.transfers.default_transfer_policy import DefaultTransferPolicy
from core.domain.transfers.transfer_policy import TransferPolicy
from core.infrastructure.bot.production_bot_gateway import ProductionBotGateway
from core.infrastructure.database import DatabaseManager, DbUnitOfWork
from core.infrastructure.repositories.rate_limiter import InMemoryRateLimiter
from core.ports.bot_gateway import BotGateway

if TYPE_CHECKING:
    from core.application.context.ensure_context import EnsureContextUseCase
    from core.application.messages.process_chat_message import ProcessChatMessageUseCase
    from core.application.reactions.process_reaction import ProcessReactionUseCase


UowFactory = Callable[[], DbUnitOfWork]


class Container:
    """DI контейнер для управления зависимостями."""

    def __init__(self, db_manager: DatabaseManager, bot: Bot | None = None):
        """
        Инициализация контейнера.

        Args:
            db_manager: Менеджер базы данных с инициализированным пулом подключений
            bot: Экземпляр telegram.Bot для ProductionBotGateway (опционально)
        """
        if not db_manager.pool:
            raise ValueError("DatabaseManager pool must be initialized before creating Container")

        self._db_manager = db_manager
        self._bot = bot
        self._bot_gateway: BotGateway | None = None
        self._message_policy: ChatMessagePolicy | None = None
        self._reaction_policy: ReactionPolicy | None = None
        self._transfer_policy: TransferPolicy | None = None
        self._rate_limiter: InMemoryRateLimiter | None = None

    def get_uow_factory(self) -> UowFactory:
        """
        Получить фабрику для создания UnitOfWork.

        Returns:
            Фабрика для создания UnitOfWork с текущим пулом подключений
        """
        def factory() -> DbUnitOfWork:
            return DbUnitOfWork(self._db_manager.pool)

        return factory

    def get_bot_gateway(self) -> BotGateway:
        """
        Получить BotGateway (singleton).

        Returns:
            Экземпляр BotGateway (ProductionBotGateway или FakeBotGateway)
        """
        if self._bot_gateway is None:
            if self._bot is not None:
                self._bot_gateway = ProductionBotGateway(self._bot)
            else:
                # Fallback на FakeBotGateway если bot не предоставлен
                from core.infrastructure.bot.fake_bot_gateway import FakeBotGateway
                self._bot_gateway = FakeBotGateway()
        return self._bot_gateway

    def set_bot_gateway(self, gateway: BotGateway) -> None:
        """
        Установить BotGateway (для тестов).

        Args:
            gateway: Экземпляр BotGateway для использования
        """
        self._bot_gateway = gateway

    def get_message_policy(self) -> ChatMessagePolicy:
        """
        Получить политику обработки сообщений (singleton).

        Returns:
            Экземпляр политики обработки сообщений
        """
        if self._message_policy is None:
            self._message_policy = DefaultChatMessagePolicy()
        return self._message_policy

    def get_ensure_context_use_case(self) -> EnsureContextUseCase:
        """Создать use case для обеспечения контекста (user, chat, chat_user в одной транзакции)."""
        from core.application.context.ensure_context import EnsureContextUseCase
        return EnsureContextUseCase(uow_factory=self.get_uow_factory())

    def get_process_message_use_case(self) -> ProcessChatMessageUseCase:
        """Создать use case для обработки сообщения чата."""
        from core.application.messages.process_chat_message import ProcessChatMessageUseCase
        return ProcessChatMessageUseCase(
            uow_factory=self.get_uow_factory(),
            message_policy=self.get_message_policy(),
        )

    def get_bot_added_to_chat_use_case(self) -> BotAddedToChatUseCase:
        return BotAddedToChatUseCase(self.get_uow_factory())

    def get_user_added_to_chat_use_case(self) -> UserAddedToChatUseCase:
        return UserAddedToChatUseCase(self.get_uow_factory())

    def get_user_left_chat_use_case(self) -> UserLeftChatUseCase:
        return UserLeftChatUseCase(self.get_uow_factory())

    def get_reaction_policy(self) -> ReactionPolicy:
        """
        Получить политику обработки реакций (singleton).

        Returns:
            Экземпляр политики обработки реакций
        """
        if self._reaction_policy is None:
            self._reaction_policy = DefaultReactionPolicy()
        return self._reaction_policy

    def get_process_reaction_use_case(self) -> ProcessReactionUseCase:
        """Создать use case для обработки реакции на сообщение."""
        from core.application.reactions.process_reaction import ProcessReactionUseCase
        return ProcessReactionUseCase(
            uow_factory=self.get_uow_factory(),
            reaction_policy=self.get_reaction_policy(),
            rate_limiter=self.get_rate_limiter(),
        )

    def get_transfer_policy(self) -> TransferPolicy:
        if self._transfer_policy is None:
            self._transfer_policy = DefaultTransferPolicy()
        return self._transfer_policy

    def get_rate_limiter(self) -> InMemoryRateLimiter:
        """Получить rate limiter (singleton)."""
        if self._rate_limiter is None:
            self._rate_limiter = InMemoryRateLimiter()
        return self._rate_limiter

    def get_transfer_points_use_case(self) -> TransferPointsUseCase:
        return TransferPointsUseCase(
            self.get_uow_factory(),
            self.get_transfer_policy(),
            self.get_rate_limiter(),
        )


    def get_personal_stats_use_case(self) -> GetPersonalStatsUseCase:
        return GetPersonalStatsUseCase(
            uow_factory=self.get_uow_factory(),
        )

    def get_chat_leaderboard_use_case(self) -> GetChatLeaderboardUseCase:
        return GetChatLeaderboardUseCase(
            uow_factory=self.get_uow_factory(),
        )

    def get_user_chats_use_case(self) -> GetUserChatsUseCase:
        return GetUserChatsUseCase(
            uow_factory=self.get_uow_factory(),
        )
