from collections.abc import Callable

from core.application.reactions.reaction_diff import ReactionDiff
from core.application.reactions.reaction_service import ReactionService
from core.domain.reactions.reaction_policy import ReactionPolicy
from core.dto.bot_context import BotContextDTO
from core.infrastructure.database import DbUnitOfWork
from core.infrastructure.repositories.chat_message_repository import DbChatMessageRepository
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository
from core.infrastructure.repositories.reaction_repository import DbReactionRepository
from utils.logger import logger

UowFactory = Callable[[], DbUnitOfWork]


class ProcessReactionUseCase:
    def __init__(self, uow_factory: UowFactory, reaction_policy: ReactionPolicy):
        self.uow_factory = uow_factory
        self.policy = reaction_policy

    async def execute(
        self,
        ctx: BotContextDTO,
        tg_chat_id: int,
        tg_message_id: int,
        old_reactions: list[str],
        new_reactions: list[str],
    ):
        """
        Обработать реакцию на сообщение.

        Args:
            ctx: Контекст бота с информацией о пользователе, который ставит реакцию
            tg_chat_id: ID чата
            tg_message_id: ID сообщения в Telegram
            old_reactions: Список эмодзи реакций до изменения
            new_reactions: Список эмодзи реакций после изменения
        """
        # Вычисляем изменения в реакциях
        changes = ReactionDiff(old_reactions, new_reactions)

        # Если изменений нет, пропускаем
        if not changes:
            logger.debug(
                f"No reaction changes detected for message {tg_message_id} "
                f"in chat {tg_chat_id} by user {ctx.user.id}"
            )
            return

        # Проверяем наличие чата и сообщения до начала транзакции
        async with self.uow_factory() as uow:
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)
            chat_message_repo = uow.get_repo(DbChatMessageRepository)

            # Получаем информацию о чате
            chat_dto = await chat_repo.get_by_tg_id(tg_chat_id)

            # Проверяем, что чат существует
            if not chat_dto:
                logger.debug(
                    f"Chat not found: tg_chat_id={tg_chat_id}. Skipping reaction processing."
                )
                return

            # Получаем сообщение
            message = await chat_message_repo.get_by_tg_id(chat_dto.id, tg_message_id)

            # Проверяем валидность сообщения
            if not message or not message.author_user_id:
                logger.debug(
                    f"Message validation failed: chat_id={chat_dto.id}, "
                    f"tg_message_id={tg_message_id}. Skipping reaction processing."
                )
                return

            # Проверяем, что пользователь не реагирует на свое собственное сообщение
            if ctx.user.id == message.author_user_id:
                logger.debug(
                    f"User {ctx.user.id} reacted to their own message. Skipping rating update."
                )
                return

            # Создаем сервис для работы с реакциями
            reaction_repo = uow.get_repo(DbReactionRepository)
            rating_repo = uow.get_repo(DbRatingRepository)
            rating_ledger_repo = uow.get_repo(DbRatingLedgerRepository)

            reaction_service = ReactionService(
                reaction_repo=reaction_repo,
                rating_repo=rating_repo,
                ledger_repo=rating_ledger_repo,
                policy=self.policy
            )

            # Обрабатываем каждое удаление
            for reaction in changes.removed:
                await reaction_service.remove_reaction(
                    ctx=ctx,
                    chat_id=chat_dto.id,
                    message=message,
                    emoji=reaction,
                )

            # Обрабатываем каждое добавление
            for reaction in changes.added:
                await reaction_service.add_reaction(
                    ctx=ctx,
                    chat_id=chat_dto.id,
                    message=message,
                    emoji=reaction,
                )
