import logging

from telegram import Chat, User

from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.chat_user_repository import ChatUserRepository
from core.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

class BotAddedToChatUseCase:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, *, tg_chat: Chat, bot: User, added_by: User):
        async with self.uow_factory() as uow:
            user_repo: UserRepository = uow.get_repo(UserRepository)
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)
            chat_user_repo: ChatUserRepository = uow.get_repo(ChatUserRepository)

            chat = await chat_repo.get_by_tg_id(tg_chat.id)
            if not chat:
                chat = await chat_repo.upsert(tg_chat)

            # гарантируем, что бот есть в users
            bot_user = await user_repo.get_by_tg_id(bot.id)
            if not bot_user:
                bot_user = await user_repo.upsert_bot(
                    bot_id=bot.id,
                    username=bot.username,
                    first_name='',
                    last_name='',
                    added_by=added_by.id
                )

            # и привязан к чату
            await chat_user_repo.add_user_to_chat(
                chat_id=chat.id,
                user_id=bot_user.id,
                is_admin=True,
            )

            # Добавляем пользователя, который добавил бота, как is_admin
            added_by_user = await user_repo.get_by_tg_id(added_by.id)
            if not added_by_user:
                added_by_user = await user_repo.upsert(added_by)

            await chat_user_repo.add_user_to_chat(
                chat_id=chat.id,
                user_id=added_by_user.id,
                is_admin=True,
            )
