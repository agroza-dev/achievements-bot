from collections.abc import Callable

from core.domain.reactions.reaction_policy import ReactionPolicy
from core.dto.bot_context import BotContextDTO
from core.dto.rating_ledger_dto import RatingLedgerEntryDTO
from core.dto.reaction_dto import ReactionDTO
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
        old_emojis = set(old_reactions)
        new_emojis = set(new_reactions)

        # Определяем, какие реакции добавлены, а какие удалены
        added = new_emojis - old_emojis
        removed = old_emojis - new_emojis

        # Если изменений нет, пропускаем
        if not added and not removed:
            logger.debug(
                f"No reaction changes detected for message {tg_message_id} "
                f"in chat {tg_chat_id} by user {ctx.user.id}"
            )
            return

        # Обрабатываем все изменения в одной транзакции
        async with self.uow_factory() as uow:
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)
            chat_message_repo = uow.get_repo(DbChatMessageRepository)
            reaction_repo = uow.get_repo(DbReactionRepository)
            rating_repo = uow.get_repo(DbRatingRepository)
            rating_ledger_repo = uow.get_repo(DbRatingLedgerRepository)
            chat_dto = await chat_repo.get_by_tg_id(tg_chat_id)

            # Находим сообщение один раз для всех изменений
            message = await chat_message_repo.get_by_tg_id(chat_dto.id, tg_message_id)

            if not message:
                logger.debug(
                    f"Message not found in database: chat_id={chat_dto.id}, "
                    f"tg_message_id={tg_message_id}. Skipping reaction processing."
                )
                return

            if not message.author_user_id:
                logger.debug(
                    f"Message has no author: chat_id={chat_dto.id}, "
                    f"tg_message_id={tg_message_id}. Skipping reaction processing."
                )
                return

            target_user_id = message.author_user_id

            # Реакции на свои сообщения не учитываем
            if ctx.user.id == target_user_id:
                logger.debug(
                    f"User {ctx.user.id} reacted to their own message. Skipping rating update."
                )
                return

            # Обрабатываем каждое удаление
            for emoji in removed:
                await self._process_single_reaction_in_transaction(
                    reaction_repo=reaction_repo,
                    rating_repo=rating_repo,
                    rating_ledger_repo=rating_ledger_repo,
                    ctx=ctx,
                    chat_id=chat_dto.id,
                    message_id=message.id,
                    tg_message_id=tg_message_id,
                    reaction=emoji,
                    action='removed',
                    target_user_id=target_user_id,
                )

            # Обрабатываем каждое добавление
            for emoji in added:
                await self._process_single_reaction_in_transaction(
                    reaction_repo=reaction_repo,
                    rating_repo=rating_repo,
                    rating_ledger_repo=rating_ledger_repo,
                    ctx=ctx,
                    chat_id=chat_dto.id,
                    message_id=message.id,
                    tg_message_id=tg_message_id,
                    reaction=emoji,
                    action='added',
                    target_user_id=target_user_id,
                )

    async def _process_single_reaction_in_transaction(
        self,
        reaction_repo: DbReactionRepository,
        rating_repo: DbRatingRepository,
        rating_ledger_repo: DbRatingLedgerRepository,
        ctx: BotContextDTO,
        chat_id: int,
        message_id: int,
        tg_message_id: int,
        reaction: str,
        action: str,  # 'added' или 'removed'
        target_user_id: int,
    ):
        """
        Обработать одну реакцию (добавление или удаление) в рамках существующей транзакции.

        Args:
            reaction_repo: Репозиторий реакций
            rating_repo: Репозиторий рейтингов
            rating_ledger_repo: Репозиторий rating_ledger
            ctx: Контекст бота с информацией о пользователе, который ставит реакцию
            chat_id: ID чата
            message_id: ID сообщения (внутренний)
            tg_message_id: ID сообщения в Telegram
            reaction: Эмодзи реакции (например, '👍')
            action: Действие - 'added' или 'removed'
            target_user_id: ID пользователя-автора сообщения
        """
        # Обрабатываем удаление реакции
        if action == 'removed':
            existing = await reaction_repo.list_for_update(
                chat_id=chat_id,
                message_id=tg_message_id,
                from_user_id=ctx.user.id,
            )

            # Если такая реакция есть в базе, удаляем её
            if any(r.reaction == reaction for r in existing):
                await reaction_repo.delete(
                    chat_id=chat_id,
                    message_id=tg_message_id,
                    from_user_id=ctx.user.id,
                    reaction=reaction,
                )

                # Уменьшаем рейтинг автора
                delta = self.policy.rating_delta(reaction)
                if delta != 0:
                    # Помечаем исходную запись как отмененную по эмодзи
                    await rating_ledger_repo.mark_as_reverted_by_emoji(
                        source_type="message",
                        source_id=message_id,
                        chat_id=chat_id,
                        user_id=target_user_id,
                        reverted_by_id=ctx.user.id,
                        emoji=reaction
                    )

                    # Находим предыдущую запись в ledger для этой реакции для получения ID
                    ledger_entries = await rating_ledger_repo.find_by_source(
                        source_type="message",
                        source_id=message_id,
                        chat_id=chat_id,
                        user_id=target_user_id
                    )
                    print(ledger_entries)
                    # Находим соответствующую запись о добавлении реакции
                    original_entry = None
                    for entry in ledger_entries:
                        if (entry.is_reverted and  # Ищем уже отмененную запись
                            entry.operation_type == 'reaction' and
                            entry.operation_subtype == 'added' and
                            entry.amount == delta and
                            entry.meta.get('emoji') == reaction):
                            original_entry = entry
                            break

                    new_balance = await rating_repo.add(
                        chat_id,
                        target_user_id,
                        -delta,
                    )

                    # Записываем компенсирующую запись в ledger
                    await rating_ledger_repo.add(
                        RatingLedgerEntryDTO(
                            chat_id=chat_id,
                            user_id=target_user_id,
                            initiator_user_id=ctx.user.id,
                            amount=-delta,
                            balance_after=new_balance,
                            operation_type="adjustment",
                            operation_subtype="reaction_revert",
                            source_type="message",
                            source_id=message_id,
                            meta={
                                "emoji": reaction,
                                "original_ledger_entry_id": original_entry.id if original_entry else None
                            },
                        )
                    )

                    logger.info(
                        f"Reaction '{reaction}' removed: "
                        f"user {ctx.user.id} removed reaction from message by user {target_user_id} "
                        f"in chat {chat_id}. Rating changed by {-delta}"
                    )
            return

        # Обрабатываем добавление реакции
        if action == 'added':
            existing = await reaction_repo.list_for_update(
                chat_id=chat_id,
                message_id=tg_message_id,
                from_user_id=ctx.user.id,
            )

            # Проверяем лимиты и правила по policy
            if not self.policy.can_add(existing, reaction):
                logger.debug(
                    f"Cannot add reaction '{reaction}': "
                    f"policy restrictions for user {ctx.user.id} on message {tg_message_id}"
                )
                return

            # Проверяем, нет ли уже такой реакции
            if any(r.reaction == reaction for r in existing):
                logger.debug(
                    f"Reaction '{reaction}' already exists: "
                    f"user {ctx.user.id} on message {tg_message_id}"
                )
                return

            # Добавляем реакцию в базу
            await reaction_repo.add(
                ReactionDTO(
                    chat_id=chat_id,
                    message_id=tg_message_id,
                    from_user_id=ctx.user.id,
                    to_user_id=target_user_id,
                    reaction=reaction,
                )
            )

            # Начисляем рейтинг автору сообщения
            delta = self.policy.rating_delta(reaction)
            if delta != 0:
                new_balance = await rating_repo.add(
                    chat_id,
                    target_user_id,
                    delta,
                )

                # Записываем в ledger
                await rating_ledger_repo.add(
                    RatingLedgerEntryDTO(
                        chat_id=chat_id,
                        user_id=target_user_id,
                        initiator_user_id=ctx.user.id,
                        amount=delta,
                        balance_after=new_balance,
                        operation_type="reaction",
                        operation_subtype="added",
                        source_type="message",
                        source_id=message_id,
                        meta={"emoji": reaction},
                    )
                )

                logger.info(
                    f"Reaction '{reaction}' added: "
                    f"user {ctx.user.id} reacted to message by user {target_user_id} "
                    f"in chat {chat_id}. Rating changed by {delta}"
                )

            # Налог (пока 0, но архитектурно готов)
            tax = self.policy.tax(reaction)
            if tax > 0:
                tax_balance = await rating_repo.add(
                    chat_id,
                    ctx.user.id,
                    -tax,
                )

                # Записываем налог в ledger
                await rating_ledger_repo.add(
                    RatingLedgerEntryDTO(
                        chat_id=chat_id,
                        user_id=ctx.user.id,
                        initiator_user_id=ctx.user.id,
                        amount=-tax,
                        balance_after=tax_balance,
                        operation_type="tax",
                        operation_subtype="reaction_tax",
                        source_type="message",
                        source_id=message_id,
                        meta={"reaction": reaction, "emoji": reaction},
                    )
                )

                logger.info(
                    f"Reaction tax applied: user {ctx.user.id} paid tax {tax} "
                    f"for reaction '{reaction}'"
                )
            return

        logger.warning(f"Unexpected action '{action}' for reaction '{reaction}'")
