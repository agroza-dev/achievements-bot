import logging
from collections.abc import Callable

from core.dto.leaderboard_row_dto import LeaderboardRowDTO
from core.infrastructure.database import DbUnitOfWork
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository
from core.infrastructure.repositories.user_repository import UserRepository
from utils.logger import prettify

logger = logging.getLogger(__name__)

UowFactory = Callable[[], DbUnitOfWork]


class GetChatLeaderboardUseCase:
    def __init__(self, uow_factory: UowFactory):
        self._uow_factory = uow_factory

    async def execute(
        self,
        *,
        tg_chat_id: int,
        limit: int,
    ) -> list[LeaderboardRowDTO]:
        logger.info(f"Getting leaderboard for chat {tg_chat_id} limit {limit}")
        async with self._uow_factory() as uow:
            chat_repo = uow.get_repo(ChatRepository)
            rating_repo = uow.get_repo(DbRatingRepository)
            user_repo = uow.get_repo(UserRepository)

            # Получаем внутренний chat_id по tg_chat_id
            chat_dto = await chat_repo.get_by_tg_id(tg_chat_id)
            if not chat_dto:
                logger.warning(f"Chat not found for tg_chat_id {tg_chat_id}")
                return []

            logger.debug(f"Chat DTO: {prettify(chat_dto)}")

            ratings = await rating_repo.get_top(
                chat_id=chat_dto.id,
                limit=limit,
            )
            logger.debug(f"Ratings from DB: {prettify(ratings)}")

            # Получаем данные пользователей для leaderboard
            user_ids = [r.user_id for r in ratings]
            logger.debug(f"User IDs to fetch: {user_ids}")
            users = await user_repo.get_by_ids(user_ids)
            logger.debug(f"Users from DB: {prettify(users)}")
            user_map = {u.id: u for u in users}

            result = [
                LeaderboardRowDTO(
                    user=user_map[r.user_id],
                    rating=r.rating,
                )
                for r in ratings
                if r.user_id in user_map
            ]
            logger.debug(f"Leaderboard result: {prettify(result)}")
            return result
