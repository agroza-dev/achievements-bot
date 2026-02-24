import logging
from datetime import UTC, datetime

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
        await self.ledger_repo.add(
            RatingLedgerEntryDTO(
                chat_id=chat_id,
                user_id=initiator_user_id,
                initiator_user_id=initiator_user_id,
                amount=-intent.amount,  # только сумма перевода
                balance_after=initiator_balance + tax,  # баланс до вычета налога
                operation_type="transfer",
                operation_subtype=str(intent.direction.value),
                source_type="manual",
                source_id=source_id,
                meta={"recipient_user_id": recipient_user_id, "tax": tax},
            )
        )

        # Ledger инициатора: запись о налоге (отдельная операция)
        if tax > 0:
            await self.ledger_repo.add(
                RatingLedgerEntryDTO(
                    chat_id=chat_id,
                    user_id=initiator_user_id,
                    initiator_user_id=initiator_user_id,
                    amount=-tax,  # сумма налога
                    balance_after=initiator_balance,  # финальный баланс после налога
                    operation_type="tax",
                    operation_subtype="transfer_tax",
                    source_type="manual",
                    source_id=source_id,  # тот же source_id для связи с переводом
                    meta={"reason": "transfer_tax", "transfer_source_id": source_id},
                )
            )

        # Ledger получателя
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
                source_id=source_id,
                meta={"from_user_id": initiator_user_id, "tax": tax},
            )
        )
