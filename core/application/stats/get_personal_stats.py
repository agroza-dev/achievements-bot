import logging
from collections.abc import Callable

from core.dto.personal_stats_dto import PersonalStatsDTO
from core.infrastructure.database import DbUnitOfWork
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.user_repository import UserRepository
from utils.logger import prettify

logger = logging.getLogger(__name__)
UowFactory = Callable[[], DbUnitOfWork]

class GetPersonalStatsUseCase:
    def __init__(self, uow_factory: UowFactory):
        self._uow_factory = uow_factory

    async def execute(
        self,
        *,
        tg_user_id: int,
        tg_chat_id: int | None,
        limit: int,
        offset: int,
    ) -> PersonalStatsDTO:
        logger.info(f"Getting personal stats for user {tg_user_id} chat {tg_chat_id} count {limit} offset {offset}")
        async with self._uow_factory() as uow:
            rating_ledger_repo = uow.get_repo(DbRatingLedgerRepository)
            user_repo: UserRepository = uow.get_repo(UserRepository)
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)

            chat_dto = await chat_repo.get_by_tg_id(tg_chat_id)

            # Получаем timezone пользователя
            user_dto = await user_repo.get_by_tg_id(tg_user_id)
            user_timezone = user_dto.timezone if user_dto else "UTC"

            logger.debug(f"User stats: {prettify(user_dto)}")
            internal_user_id = user_dto.id
            entries = await rating_ledger_repo.list_for_user(
                user_id=internal_user_id,
                chat_id=chat_dto.id,
                limit=limit,
                offset=offset,
            )
        balance = entries[0].balance_after if entries else 0

        return PersonalStatsDTO(
            balance=balance,
            entries=entries,
            chat_title=chat_dto.title if chat_dto else None,
            user_timezone=user_timezone,
        )
