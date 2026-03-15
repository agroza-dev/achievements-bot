import logging
from typing import TYPE_CHECKING

from core.application.rating_ledger.rating_ledger_service import RatingLedgerService
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository

if TYPE_CHECKING:
    from core.infrastructure.database import DbUnitOfWork

logger = logging.getLogger(__name__)

# TODO: нужно вынести это в конфиг
WELCOME_BONUS_AMOUNT = 500


class AwardWelcomeBonusUseCase:
    """
    UseCase для начисления приветственного бонуса пользователю при первом добавлении в чат.

    Бонус начисляется только если у пользователя ещё не было записей в rating_ledger
    для данного чата (Вариант А).
    """

    def __init__(
        self,
        rating_service: RatingLedgerService,
        rating_repo: DbRatingRepository,
        ledger_repo: DbRatingLedgerRepository,
    ):
        self.rating_service = rating_service
        self.rating_repo = rating_repo
        self.ledger_repo = ledger_repo

    async def execute(self, *, uow: DbUnitOfWork, chat_id: int, user_id: int) -> bool:
        """
        Начислить приветственный бонус пользователю, если это его первое добавление в чат.

        Args:
            uow: Активный UnitOfWork (для работы в существующей транзакции)
            chat_id: ID чата (внутренний)
            user_id: ID пользователя (внутренний)

        Returns:
            True если бонус был начислен, False если уже был начислен ранее
        """
        # Проверяем, есть ли уже записи в ledger для этого пользователя в чате
        has_entries = await self.ledger_repo.has_any_entries_for_user_in_chat(
            user_id=user_id,
            chat_id=chat_id,
        )

        if has_entries:
            logger.debug(
                f"Пользователь {user_id} уже имеет записи в ledger чата {chat_id}, "
                f"пропускаем начисление приветственного бонуса"
            )
            return False

        # Сначала обновляем рейтинг в chat_users, получаем новый баланс
        new_balance = await self.rating_repo.add(
            chat_id=chat_id,
            user_id=user_id,
            value=WELCOME_BONUS_AMOUNT,
        )

        # Затем создаём запись в ledger
        await self.rating_service.record_welcome_bonus(
            chat_id=chat_id,
            user_id=user_id,
            amount=WELCOME_BONUS_AMOUNT,
            balance_after=new_balance,
        )

        logger.info(
            f"Начислен приветственный бонус {WELCOME_BONUS_AMOUNT} очков "
            f"пользователю {user_id} в чате {chat_id} (баланс: {new_balance})"
        )
        return True
