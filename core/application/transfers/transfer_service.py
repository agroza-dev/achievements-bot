import logging

from core.application.transfers.transfer_intent import TransferDirection, TransferIntent
from core.application.transfers.transfer_result import TransferResult
from core.domain.transfers.transfer_policy import TransferPolicy
from core.dto.rating_ledger_dto import RatingLedgerEntryDTO
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository

logger = logging.getLogger(__name__)


class TransferService:
    def __init__(
        self,
        *,
        rating_repo: DbRatingRepository,
        ledger_repo: DbRatingLedgerRepository,
        policy: TransferPolicy,
    ):
        self.rating_repo = rating_repo
        self.ledger_repo = ledger_repo
        self.policy = policy

    async def apply(
        self,
        *,
        chat_id: int,
        initiator_user_id: int,
        recipient_user_id: int,
        intent: TransferIntent,
    ) -> TransferResult|None:
        tax = self.policy.tax(intent.amount, intent.direction)
        # инициатор всегда платит
        initiator_delta = -(intent.amount + tax)
        initiator_balance = await self.rating_repo.add(
            chat_id,
            initiator_user_id,
            initiator_delta,
        )

        # получатель
        recipient_delta = (
            intent.amount
            if intent.direction == TransferDirection.POSITIVE
            else -intent.amount
        )

        recipient_balance = await self.rating_repo.add(
            chat_id,
            recipient_user_id,
            recipient_delta,
        )

        # ledger инициатора
        await self.ledger_repo.add(
            RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=initiator_user_id,
                initiator_user_id=initiator_user_id,
                amount=initiator_delta,
                balance_after=initiator_balance,
                operation_type="transfer",
                operation_subtype=str(intent.direction.value),
                source_type="manual",
                source_id=None,
                meta={"tax": tax},
            )
        )

        # ledger получателя
        await self.ledger_repo.add(
            RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=recipient_user_id,
                initiator_user_id=initiator_user_id,
                amount=recipient_delta,
                balance_after=recipient_balance,
                operation_type="transfer",
                operation_subtype=str(intent.direction.value),
                source_type="manual",
                source_id=None,
                meta={},
            )
        )
