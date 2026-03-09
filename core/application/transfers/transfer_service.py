import logging
from datetime import UTC, datetime

from core.application.rating_ledger.rating_ledger_service import RatingLedgerService
from core.application.transfers.apply_transfer_result import ApplyTransferResult
from core.application.transfers.transfer_intent import TransferDirection, TransferIntent
from core.domain.transfers.transfer_policy import TransferPolicy
from core.infrastructure.repositories.rating_repository import DbRatingRepository

logger = logging.getLogger(__name__)


class TransferService:
    def __init__(
        self,
        *,
        rating_repo: DbRatingRepository,
        ledger_service: RatingLedgerService,
        policy: TransferPolicy,
    ):
        self.rating_repo = rating_repo
        self.ledger_service = ledger_service
        self.policy = policy

    async def apply(
        self,
        *,
        chat_id: int,
        initiator_user_id: int,
        recipient_user_id: int,
        intent: TransferIntent,
        tax: int,
    ) -> ApplyTransferResult:

        # Генерируем source_id для связи записей о переводе и налоге
        # Используем текущий timestamp в миллисекундах как уникальный ID
        source_id = int(datetime.now(UTC).timestamp() * 1000)

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

        # Ledger инициатора: запись о переводе (без налога)
        await self.ledger_service.record_transfer(
            chat_id=chat_id,
            user_id=initiator_user_id,
            initiator_user_id=initiator_user_id,
            counterparty_user_id=recipient_user_id,
            amount=-intent.amount,
            balance_after=initiator_balance + tax,
            direction=str(intent.direction.value),
            source_id=source_id,
            tax=tax,
        )

        # Ledger инициатора: запись о налоге (отдельная операция)
        if tax > 0:
            await self.ledger_service.record_transfer_tax(
                chat_id=chat_id,
                user_id=initiator_user_id,
                initiator_user_id=initiator_user_id,
                amount=-tax,
                balance_after=initiator_balance,
                source_id=source_id,
            )

        # Ledger получателя
        await self.ledger_service.record_transfer(
            chat_id=chat_id,
            user_id=recipient_user_id,
            initiator_user_id=initiator_user_id,
            counterparty_user_id=initiator_user_id,
            amount=recipient_delta,
            balance_after=recipient_balance,
            direction=str(intent.direction.value),
            source_id=source_id,
            tax=tax,
        )

        return ApplyTransferResult(
            amount=intent.amount,
            tax=tax,
            initiator_balance_after=initiator_balance,
            recipient_balance_after=recipient_balance,
        )
