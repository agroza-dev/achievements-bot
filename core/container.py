"""Dependency Injection Container для управления зависимостями приложения."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from core.domain.messages.chat_message_policy import ChatMessagePolicy
from core.domain.messages.default_chat_message_policy import DefaultChatMessagePolicy
from core.domain.reactions.default_reaction_policy import DefaultReactionPolicy
from core.domain.reactions.reaction_policy import ReactionPolicy
from core.infrastructure.database import DatabaseManager, DbUnitOfWork

if TYPE_CHECKING:
    from core.application.context.ensure_chat import EnsureChatUseCase
    from core.application.context.ensure_chat_user import EnsureChatUserUseCase
    from core.application.context.ensure_context import EnsureContextUseCase
    from core.application.context.ensure_user import EnsureUserUseCase
    from core.application.messages.process_chat_message import ProcessChatMessageUseCase
    from core.application.reactions.process_reaction import ProcessReactionUseCase


UowFactory = Callable[[], DbUnitOfWork]


class Container:
    """DI контейнер для управления зависимостями."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация контейнера.

        Args:
            db_manager: Менеджер базы данных с инициализированным пулом подключений
        """
        if not db_manager.pool:
            raise ValueError("DatabaseManager pool must be initialized before creating Container")

        self._db_manager = db_manager
        self._message_policy: ChatMessagePolicy | None = None
        self._reaction_policy: ReactionPolicy | None = None

    def get_uow_factory(self) -> UowFactory:
        """
        Получить фабрику для создания UnitOfWork.

        Returns:
            Фабрика для создания UnitOfWork с текущим пулом подключений
        """
        def factory() -> DbUnitOfWork:
            return DbUnitOfWork(self._db_manager.pool)

        return factory

    def get_message_policy(self) -> ChatMessagePolicy:
        """
        Получить политику обработки сообщений (singleton).

        Returns:
            Экземпляр политики обработки сообщений
        """
        if self._message_policy is None:
            self._message_policy = DefaultChatMessagePolicy()
        return self._message_policy

    def get_ensure_user_use_case(self) -> EnsureUserUseCase:
        """Создать use case для обеспечения существования пользователя."""
        from core.application.context.ensure_user import EnsureUserUseCase
        return EnsureUserUseCase(uow_factory=self.get_uow_factory())

    def get_ensure_chat_use_case(self) -> EnsureChatUseCase:
        """Создать use case для обеспечения существования чата."""
        from core.application.context.ensure_chat import EnsureChatUseCase
        return EnsureChatUseCase(uow_factory=self.get_uow_factory())

    def get_ensure_chat_user_use_case(self) -> EnsureChatUserUseCase:
        """Создать use case для обеспечения связи пользователя и чата."""
        from core.application.context.ensure_chat_user import EnsureChatUserUseCase
        return EnsureChatUserUseCase(uow_factory=self.get_uow_factory())

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
        )

