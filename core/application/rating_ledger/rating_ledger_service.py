"""Сервис для работы с rating ledger."""

from core.dto.rating_ledger_dto import RatingLedgerEntryDTO
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository


class RatingLedgerService:
    """
    Фасад для записей в rating ledger.

    Предоставляет удобные методы для создания записей о различных операциях,
    гарантируя корректное заполнение всех полей.
    """

    def __init__(self, ledger_repo: DbRatingLedgerRepository):
        self.ledger_repo = ledger_repo

    async def record_transfer(
        self,
        *,
        chat_id: int,
        user_id: int,
        initiator_user_id: int,
        counterparty_user_id: int,
        amount: int,
        balance_after: int | None,
        direction: str,
        source_id: int,
        tax: int = 0,
    ) -> None:
        """
        Записать операцию перевода.

        Args:
            chat_id: ID чата
            user_id: Владелец записи (чей баланс изменился)
            initiator_user_id: Кто инициировал перевод
            counterparty_user_id: Вторая сторона перевода
            amount: Сумма изменения (без учёта налога)
            balance_after: Баланс после операции
            direction: Направление перевода ('positive' или 'negative')
            source_id: ID источника (уникальный для пары записей перевода)
            tax: Сумма налога (для meta)
        """
        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=initiator_user_id,
            counterparty_user_id=counterparty_user_id,
            amount=amount,
            balance_after=balance_after,
            operation_type="transfer",
            operation_subtype=direction,
            source_type="manual",
            source_id=source_id,
            meta={"tax": tax} if tax > 0 else {},
        )
        await self.ledger_repo.add(entry)

    async def record_transfer_tax(
        self,
        *,
        chat_id: int,
        user_id: int,
        initiator_user_id: int,
        amount: int,
        balance_after: int | None,
        source_id: int,
    ) -> None:
        """
        Записать операцию удержания налога за перевод.

        Args:
            chat_id: ID чата
            user_id: Владелец записи (чей баланс изменился)
            initiator_user_id: Кто инициировал перевод (он же платит налог)
            amount: Сумма налога (всегда отрицательная)
            balance_after: Баланс после удержания налога
            source_id: ID источника (тот же, что у связанного перевода)
        """
        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=initiator_user_id,
            counterparty_user_id=None,  # Для налога нет второй стороны
            amount=amount,
            balance_after=balance_after,
            operation_type="tax",
            operation_subtype="transfer_tax",
            source_type="manual",
            source_id=source_id,
            meta={"reason": "transfer_tax", "transfer_source_id": source_id},
        )
        await self.ledger_repo.add(entry)

    async def record_reaction(
        self,
        *,
        chat_id: int,
        user_id: int,
        initiator_user_id: int,
        amount: int,
        balance_after: int | None,
        message_id: int,
        emoji: str,
        kind: str,
    ) -> None:
        """
        Записать операцию начисления за реакцию.

        Args:
            chat_id: ID чата
            user_id: Получатель реакции (чей баланс изменился)
            initiator_user_id: Автор реакции
            amount: Сумма изменения
            balance_after: Баланс после операции
            message_id: ID сообщения
            emoji: Эмодзи реакции
            kind: Тип реакции ('positive' или 'negative')
        """
        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=initiator_user_id,
            counterparty_user_id=None,  # Для реакции нет второй стороны
            amount=amount,
            balance_after=balance_after,
            operation_type="reaction",
            operation_subtype=kind,
            source_type="message",
            source_id=message_id,
            meta={"emoji": emoji},
        )
        await self.ledger_repo.add(entry)

    async def record_reaction_revert(
        self,
        *,
        chat_id: int,
        user_id: int,
        initiator_user_id: int,
        amount: int,
        balance_after: int | None,
        message_id: int,
        emoji: str,
        kind: str,
    ) -> None:
        """
        Записать операцию отмены реакции.

        Args:
            chat_id: ID чата
            user_id: Получатель реакции (чей баланс изменился)
            initiator_user_id: Кто отменил реакцию
            amount: Сумма изменения (отрицательная)
            balance_after: Баланс после операции
            message_id: ID сообщения
            emoji: Эмодзи реакции
            kind: Тип реакции ('positive' или 'negative')
        """
        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=initiator_user_id,
            counterparty_user_id=None,  # Для реакции нет второй стороны
            amount=amount,
            balance_after=balance_after,
            operation_type="reaction_revert",
            operation_subtype=kind,
            source_type="message",
            source_id=message_id,
            meta={"emoji": emoji},
        )
        await self.ledger_repo.add(entry)

    async def record_tax(
        self,
        *,
        chat_id: int,
        user_id: int,
        initiator_user_id: int,
        amount: int,
        balance_after: int | None,
        message_id: int,
        emoji: str,
    ) -> None:
        """
        Записать операцию удержания налога за реакцию.

        Args:
            chat_id: ID чата
            user_id: Владелец записи (чей баланс изменился)
            initiator_user_id: Кто инициировал операцию (автор реакции)
            amount: Сумма налога (всегда отрицательная)
            balance_after: Баланс после удержания налога
            message_id: ID сообщения
            emoji: Эмодзи реакции
        """
        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=initiator_user_id,
            counterparty_user_id=None,  # Для налога нет второй стороны
            amount=amount,
            balance_after=balance_after,
            operation_type="tax",
            operation_subtype="reaction",
            source_type="message",
            source_id=message_id,
            meta={"emoji": emoji},
        )
        await self.ledger_repo.add(entry)

    async def record_welcome_bonus(
        self,
        *,
        chat_id: int,
        user_id: int,
        amount: int = 100,
        balance_after: int | None,
    ) -> None:
        """
        Записать операцию начисления приветственного бонуса.

        Args:
            chat_id: ID чата
            user_id: Получатель бонуса
            amount: Сумма бонуса (по умолчанию 100)
            balance_after: Баланс после операции
        """
        entry = RatingLedgerEntryDTO(
            chat_id=chat_id,
            user_id=user_id,
            initiator_user_id=None,  # Системное начисление
            counterparty_user_id=None,
            amount=amount,
            balance_after=balance_after,
            operation_type="bonus",
            operation_subtype="welcome",
            source_type="system",
            source_id=None,
            meta={"reason": "welcome_bonus"},
        )
        await self.ledger_repo.add(entry)
