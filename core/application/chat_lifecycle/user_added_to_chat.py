import logging

from telegram import Chat, User

from core.application.chat_lifecycle.award_welcome_bonus import AwardWelcomeBonusUseCase
from core.application.rating_ledger.rating_ledger_service import RatingLedgerService
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.chat_user_repository import ChatUserRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository
from core.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserAddedToChatUseCase:
    """
    UseCase для добавления пользователя в чат.

    Выполняет все необходимые операции при добавлении пользователя в чат:
    - Создаёт чат если не существует
    - Создаёт пользователя если не существует
    - Добавляет пользователя в чат
    - Начисляет приветственный бонус (если это первое добавление)
    """

    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, *, tg_chat: Chat, tg_user: User, added_by: User | None = None):
        """
        Добавить пользователя в чат.

        Args:
            tg_chat: Telegram чат
            tg_user: Telegram пользователь для добавления
            added_by: Пользователь, который добавил (если есть)
        """
        async with self.uow_factory() as uow:
            user_repo: UserRepository = uow.get_repo(UserRepository)
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)
            chat_user_repo: ChatUserRepository = uow.get_repo(ChatUserRepository)
            rating_repo: DbRatingRepository = uow.get_repo(DbRatingRepository)
            ledger_repo: DbRatingLedgerRepository = uow.get_repo(DbRatingLedgerRepository)

            # Получаем или создаём чат
            chat = await chat_repo.get_by_tg_id(tg_chat.id)
            if not chat:
                chat = await chat_repo.upsert(tg_chat)

            # Получаем или создаём пользователя
            user = await user_repo.get_by_tg_id(tg_user.id)
            if not user:
                user = await user_repo.upsert(tg_user)

            # Добавляем пользователя в чат
            await chat_user_repo.add_user_to_chat(
                chat_id=chat.id,
                user_id=user.id,
                is_admin=False,
            )

            # Начисляем приветственный бонус
            rating_service = RatingLedgerService(ledger_repo)
            welcome_bonus_use_case = AwardWelcomeBonusUseCase(
                rating_service=rating_service,
                rating_repo=rating_repo,
                ledger_repo=ledger_repo,
            )
            bonus_awarded = await welcome_bonus_use_case.execute(
                uow=uow,
                chat_id=chat.id,
                user_id=user.id,
            )

            if bonus_awarded:
                logger.info(
                    f"Начислен приветственный бонус пользователю {tg_user.username} ({tg_user.id}) в чате {tg_chat.title}",
                    extra={
                        "tg_chat_id": tg_chat.id,
                        "user_id": user.id,
                        "bonus_amount": 100,
                    }
                )
