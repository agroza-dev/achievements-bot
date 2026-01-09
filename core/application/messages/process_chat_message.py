from collections.abc import Callable

from core.domain.messages.chat_message_policy import ChatMessagePolicy
from core.dto.bot_context import BotContextDTO
from core.dto.chat_message_create_dto import ChatMessageCreateDTO
from core.infrastructure.database import DbUnitOfWork
from core.infrastructure.repositories.chat_message_repository import DbChatMessageRepository

UowFactory = Callable[[], DbUnitOfWork]

class ProcessChatMessageUseCase:
    def __init__(self, uow_factory: UowFactory, message_policy: ChatMessagePolicy):
        self.uow_factory = uow_factory
        self.policy = message_policy

    async def execute(
        self,
        ctx: BotContextDTO,
        message_dto: ChatMessageCreateDTO
    ):
        async with self.uow_factory() as uow:
            chat_message_repo: DbChatMessageRepository = uow.get_repo(DbChatMessageRepository)

            await chat_message_repo.add(message_dto)
