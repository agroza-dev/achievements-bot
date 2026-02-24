"""Use case для обеспечения контекста (user, chat, chat_user) в одной транзакции."""
import logging
from collections.abc import Callable

from telegram import Chat, User

from core.dto.bot_context import BotContextDTO
from core.infrastructure.database import DbUnitOfWork
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.chat_user_repository import ChatUserRepository
from core.infrastructure.repositories.user_repository import UserRepository
from utils.logger import prettify
from utils.timezone_utils import get_timezone_by_language

logger = logging.getLogger(__name__)
UowFactory = Callable[[], DbUnitOfWork]


class EnsureContextUseCase:
    """
    Use case для обеспечения контекста бота.

    Выполняет все операции (user, chat, chat_user) в одной транзакции,
    что гарантирует атомарность и улучшает производительность.
    """

    def __init__(self, uow_factory: UowFactory):
        """
        Инициализация use case.

        Args:
            uow_factory: Фабрика для создания UnitOfWork
        """
        self._uow_factory = uow_factory

    async def execute(self, tg_user: User, tg_chat: Chat) -> BotContextDTO:
        """
        Выполнить обеспечение контекста в одной транзакции.

        Args:
            tg_user: Telegram пользователь
            tg_chat: Telegram чат

        Returns:
            DTO с контекстом бота (user, chat, chat_user)

        Raises:
            ValueError: Если пользователь или чат не указаны
        """
        if not tg_user or not tg_chat:
            raise ValueError("User and chat must be provided")
        logger.debug(f"Try to load context for User: {prettify(tg_user)}, chat: {prettify(tg_chat)}")
        # Используем одну транзакцию для всех операций
        async with self._uow_factory() as uow:
            # Получаем репозитории для работы в одной транзакции
            user_repo: UserRepository = uow.get_repo(UserRepository)
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)
            chat_user_repo: ChatUserRepository = uow.get_repo(ChatUserRepository)

            # 1. Обеспечиваем существование пользователя
            user = await user_repo.get_by_tg_id(tg_user.id)
            if not user:
                # Определяем часовой пояс по языку пользователя
                timezone = get_timezone_by_language(tg_user.language_code)
                user = await user_repo.upsert(tg_user, timezone=timezone)
            logger.debug(f"Received user: {prettify(user)} by {tg_user.id}")
            # 2. Обеспечиваем существование чата
            chat = await chat_repo.get_by_tg_id(tg_chat.id)
            if not chat:
                chat = await chat_repo.upsert(tg_chat)

            # 3. Обеспечиваем связь пользователя и чата
            chat_user = await chat_user_repo.get_chat_user(chat.id, user.id)
            if not chat_user:
                chat_user = await chat_user_repo.add_user_to_chat(chat.id, user.id, False)

            # Все операции выполнены в одной транзакции
            return BotContextDTO(
                user=user,
                chat=chat,
                chat_user=chat_user,
            )

