import logging

from telegram import Chat, User

from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.chat_user_repository import ChatUserRepository
from core.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserLeftChatUseCase:
    """Use case для обработки выхода пользователя из чата."""

    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, *, tg_chat: Chat, user: User):
        """
        Обработать выход пользователя из чата.

        Деактивирует связь пользователя с чатом. Если пользователь вышел из чата,
        но остаётся в других чатах — сам пользователь не деактивируется.
        """
        async with self.uow_factory() as uow:
            user_repo: UserRepository = uow.get_repo(UserRepository)
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)
            chat_user_repo: ChatUserRepository = uow.get_repo(ChatUserRepository)
            logger.debug(f"Process User {user.id} left Chat {tg_chat.id}")
            # Находим чат
            chat = await chat_repo.get_by_tg_id(tg_chat.id)
            if not chat:
                logger.warning(f"Chat {tg_chat.id} not found in DB")
                return

            # Находим пользователя
            db_user = await user_repo.get_by_tg_id(user.id)
            if not db_user:
                logger.warning(f"User {user.id} not found in DB")
                return

            # Деактивируем связь пользователя с чатом
            await chat_user_repo.remove_user_from_chat(chat.id, db_user.id)

            logger.info(
                f"User {user.username} (id={user.id}) left chat {tg_chat.title} (id={tg_chat.id})",
                extra={
                    "tg_chat_id": tg_chat.id,
                    "user_id": user.id,
                }
            )
