from telegram import Chat, Update, User
from telegram.ext import CallbackContext

from core.application.context.ensure_chat import EnsureChatUseCase
from core.application.context.ensure_chat_user import EnsureChatUserUseCase
from core.application.context.ensure_user import EnsureUserUseCase
from core.dto.bot_context import BotContextDTO
from core.infrastructure.database import DbUnitOfWork, db_manager


async def ensure_context(update: Update, context: CallbackContext):
    user: User = update.effective_user
    chat: Chat = update.effective_chat

    if not user or not chat:
        return

    def uow_factory():
        return DbUnitOfWork(db_manager.pool)

    user_dto = await EnsureUserUseCase(uow_factory).execute(user)
    chat_dto = await EnsureChatUseCase(uow_factory).execute(chat)
    chat_user_dto = await EnsureChatUserUseCase(uow_factory).execute(chat_dto.id, user_dto.id)

    context.bot_data['ctx'] = BotContextDTO(
        user= user_dto,
        chat= chat_dto,
        chat_user= chat_user_dto,
    )
