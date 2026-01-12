from core.domain.reactions.reaction_policy import ReactionPolicy
from core.dto.bot_context import BotContextDTO
from core.dto.rating_ledger_dto import RatingLedgerEntryDTO
from core.dto.reaction_dto import ReactionDTO
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository
from core.infrastructure.repositories.reaction_repository import DbReactionRepository
from utils.logger import logger


class ReactionService:
    def __init__(
        self,
        reaction_repo: DbReactionRepository,
        rating_repo: DbRatingRepository,
        ledger_repo: DbRatingLedgerRepository,
        policy: ReactionPolicy,
    ):
        self.reaction_repo = reaction_repo
        self.rating_repo = rating_repo
        self.ledger_repo = ledger_repo
        self.policy = policy

    async def add_reaction(self, *, ctx: BotContextDTO, chat_id: int, message, emoji: str):
        """
        Добавить реакцию и применить соответствующие изменения рейтинга.

        Args:
            ctx: Контекст бота
            chat_id: ID чата
            message: Объект сообщения
            emoji: Эмодзи реакции
        """
        existing = await self.reaction_repo.list_for_update(
            chat_id=chat_id,
            message_id=message.tg_message_id,
            from_user_id=ctx.user.id,
        )

        # Проверяем политику на возможность добавления
        if not self.policy.can_add(existing, emoji):
            logger.debug(
                f"Cannot add reaction '{emoji}': "
                f"policy restrictions for user {ctx.user.id} on message {message.tg_message_id}"
            )
            return

        # Проверяем, нет ли уже такой реакции
        if any(r.reaction == emoji for r in existing):
            logger.debug(f"Reaction '{emoji}' already exists: user {ctx.user.id} on message {message.tg_message_id}")
            return

        # Добавляем реакцию в базу
        await self.reaction_repo.add(
            ReactionDTO(
                chat_id=chat_id,
                message_id=message.tg_message_id,
                from_user_id=ctx.user.id,
                to_user_id=message.author_user_id,
                reaction=emoji,
            )
        )

        # Применяем изменения рейтинга
        await self._apply_rating_for_reaction(
            ctx=ctx,
            chat_id=chat_id,
            message=message,
            emoji=emoji,
        )

    async def remove_reaction(self, *, ctx: BotContextDTO, chat_id: int, message, emoji: str):
        """
        Удалить реакцию и отменить соответствующие изменения рейтинга.

        Args:
            ctx: Контекст бота
            chat_id: ID чата
            message: Объект сообщения
            emoji: Эмодзи реакции
        """
        # Удаляем реакцию из базы
        removed = await self.reaction_repo.delete_if_exists(
            chat_id=chat_id,
            message_id=message.tg_message_id,
            from_user_id=ctx.user.id,
            reaction=emoji,
        )

        if not removed:
            logger.debug(
                f"Reaction '{emoji}' not found for removal: user {ctx.user.id} on message {message.tg_message_id}"
            )
            return

        # Получаем дельту рейтинга для этой реакции
        delta = self._get_delta(emoji)
        if delta == 0:
            logger.debug(f"No rating change for removing reaction '{emoji}': delta is zero")
            return

        # Отмечаем соответствующую запись в ledger как отмененную
        await self.ledger_repo.mark_as_reverted_by_emoji(
            source_type="message",
            source_id=message.id,
            chat_id=chat_id,
            user_id=message.author_user_id,
            reverted_by_id=ctx.user.id,
            emoji=emoji,
        )

        # Обновляем рейтинг автора сообщения (уменьшаем на delta)
        new_balance = await self.rating_repo.add(
            chat_id,
            message.author_user_id,
            -delta,
        )

        # Записываем компенсирующую запись в ledger
        await self.ledger_repo.add(
            RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=message.author_user_id,
                initiator_user_id=ctx.user.id,
                amount=-delta,
                balance_after=new_balance,
                operation_type="adjustment",
                operation_subtype="reaction_revert",
                source_type="message",
                source_id=message.id,
                meta={"emoji": emoji},
            )
        )

        logger.info(
            f"Reaction '{emoji}' removed: "
            f"user {ctx.user.id} removed reaction from message by user {message.author_user_id} "
            f"in chat {chat_id}. Rating changed by {-delta}"
        )

    async def _apply_rating_for_reaction(self, *, ctx: BotContextDTO, chat_id: int, message, emoji: str):
        """
        Применить изменения рейтинга для добавленной реакции.

        Args:
            ctx: Контекст бота
            chat_id: ID чата
            message: Объект сообщения
            emoji: Эмодзи реакции
        """
        delta = self._get_delta(emoji)
        if delta == 0:
            logger.debug(f"No rating change for reaction '{emoji}': delta is zero")
            return

        # Обновляем рейтинг автора сообщения
        new_balance = await self.rating_repo.add(
            chat_id,
            message.author_user_id,
            delta,
        )

        # Записываем в ledger
        await self.ledger_repo.add(
            RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=message.author_user_id,
                initiator_user_id=ctx.user.id,
                amount=delta,
                balance_after=new_balance,
                operation_type="reaction",
                operation_subtype="added",
                source_type="message",
                source_id=message.id,
                meta={"emoji": emoji},
            )
        )

        logger.info(
            f"Reaction '{emoji}' added: "
            f"user {ctx.user.id} reacted to message by user {message.author_user_id} "
            f"in chat {chat_id}. Rating changed by {delta}"
        )

        # Применяем налог, если он положительный
        await self._apply_tax_if_needed(ctx, chat_id, message, emoji)

    async def _apply_tax_if_needed(self, ctx: BotContextDTO, chat_id: int, message, emoji: str):
        """
        Применить налог к пользователю за реакцию, если налог положительный.

        Args:
            ctx: Контекст бота
            chat_id: ID чата
            message: Объект сообщения
            emoji: Эмодзи реакции
        """
        tax = self.policy.tax(emoji)
        if tax <= 0:
            return

        # Обновляем рейтинг пользователя, который поставил реакцию
        tax_balance = await self.rating_repo.add(
            chat_id,
            ctx.user.id,
            -tax,
        )

        # Записываем налог в ledger
        await self.ledger_repo.add(
            RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=ctx.user.id,
                initiator_user_id=ctx.user.id,
                amount=-tax,
                balance_after=tax_balance,
                operation_type="tax",
                operation_subtype="reaction_tax",
                source_type="message",
                source_id=message.id,
                meta={"reaction": emoji, "emoji": emoji},
            )
        )

        logger.info(f"Reaction tax applied: user {ctx.user.id} paid tax {tax} for reaction '{emoji}'")

    def _get_delta(self, emoji: str) -> int:
        return self.policy.rating_delta(emoji)
