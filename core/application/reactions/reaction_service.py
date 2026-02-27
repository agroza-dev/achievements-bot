import logging

from core.application.rating_ledger.rating_ledger_service import RatingLedgerService
from core.application.reactions.reaction_intent import ReactionKind
from core.domain.reactions.reaction_policy import ReactionPolicy
from core.dto.bot_context import BotContextDTO
from core.dto.reaction_dto import ReactionDTO
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository
from core.infrastructure.repositories.reaction_repository import DbReactionRepository

logger = logging.getLogger(__name__)


class ReactionService:
    def __init__(
        self,
        reaction_repo: DbReactionRepository,
        rating_repo: DbRatingRepository,
        ledger_repo: DbRatingLedgerRepository,
        ledger_service: RatingLedgerService,
        policy: ReactionPolicy,
    ):
        self.reaction_repo = reaction_repo
        self.rating_repo = rating_repo
        self.ledger_repo = ledger_repo
        self.ledger_service = ledger_service
        self.policy = policy

    # ---------- PUBLIC API ----------

    async def add_reaction(self, *, ctx: BotContextDTO, chat_id: int, message, emoji: str):
        kind = self.policy.kind(emoji)
        if kind is ReactionKind.NEUTRAL:
            return

        """
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

        await self._apply_added_reaction(
            ctx=ctx,
            chat_id=chat_id,
            message=message,
            emoji=emoji,
            kind=kind,
        )

    async def remove_reaction(self, *, ctx: BotContextDTO, chat_id: int, message, emoji: str):
        kind = self.policy.kind(emoji)
        if kind is ReactionKind.NEUTRAL:
            return

        removed = await self.reaction_repo.delete_if_exists(
            chat_id=chat_id,
            message_id=message.tg_message_id,
            from_user_id=ctx.user.id,
            reaction=emoji,
        )

        if not removed:
            return

        await self._apply_removed_reaction(
            ctx=ctx,
            chat_id=chat_id,
            message=message,
            emoji=emoji,
            kind=kind,
        )

    # ---------- INTERNAL LOGIC ----------

    async def _apply_added_reaction(
        self,
        *,
        ctx: BotContextDTO,
        chat_id: int,
        message,
        emoji: str,
        kind: ReactionKind,
    ):
        delta = self.policy.rating_delta(emoji)
        if delta == 0:
            return

        new_balance = await self.rating_repo.add(
            chat_id,
            message.author_user_id,
            delta,
        )

        await self.ledger_service.record_reaction(
            chat_id=chat_id,
            user_id=message.author_user_id,
            initiator_user_id=ctx.user.id,
            amount=delta,
            balance_after=new_balance,
            message_id=message.id,
            emoji=emoji,
            kind=kind.value,
        )

        if kind is ReactionKind.POSITIVE:
            await self._apply_tax_if_needed(ctx, chat_id, message, emoji)

    async def _apply_removed_reaction(
        self,
        *,
        ctx: BotContextDTO,
        chat_id: int,
        message,
        emoji: str,
        kind: ReactionKind,
    ):
        delta = self.policy.rating_delta(emoji)
        if delta == 0:
            return

        await self.ledger_repo.mark_as_reverted_by_emoji(
            source_type="message",
            source_id=message.id,
            chat_id=chat_id,
            user_id=message.author_user_id,
            reverted_by_id=ctx.user.id,
            emoji=emoji,
        )

        new_balance = await self.rating_repo.add(
            chat_id,
            message.author_user_id,
            -delta,
        )

        await self.ledger_service.record_reaction_revert(
            chat_id=chat_id,
            user_id=message.author_user_id,
            initiator_user_id=ctx.user.id,
            amount=-delta,
            balance_after=new_balance,
            message_id=message.id,
            emoji=emoji,
            kind=kind.value,
        )

    async def _apply_tax_if_needed(self, ctx: BotContextDTO, chat_id: int, message, emoji: str):
        tax = self.policy.tax(emoji)
        if tax <= 0:
            return

        balance = await self.rating_repo.add(
            chat_id,
            ctx.user.id,
            -tax,
        )

        await self.ledger_service.record_tax(
            chat_id=chat_id,
            user_id=ctx.user.id,
            initiator_user_id=ctx.user.id,
            amount=-tax,
            balance_after=balance,
            message_id=message.id,
            emoji=emoji,
        )

