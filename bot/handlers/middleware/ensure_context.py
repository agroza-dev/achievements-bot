from core.database import db_manager
from core.dto.bot_context import BotContextDTO
from core.repositories.chat_repository import ChatRepository
from core.repositories.chat_user_repository import ChatUserRepository
from core.repositories.user_repository import UserRepository


async def ensure_context(update, context):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    user_dto = await UserRepository(db_manager).get_or_create(user)
    chat_dto = await ChatRepository(db_manager).get_or_create(chat)
    await ChatUserRepository(db_manager).get_or_create(chat_dto.id, user_dto.id)

    context.bot_data['ctx'] = BotContextDTO(
        user=user_dto,
        chat=chat_dto,
    )
