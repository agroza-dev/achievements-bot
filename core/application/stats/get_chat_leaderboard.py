from collections.abc import Callable

from core.dto.leaderboard_row_dto import LeaderboardRowDTO
from core.infrastructure.database import DbUnitOfWork

UowFactory = Callable[[], DbUnitOfWork]

class GetChatLeaderboardUseCase:
    def __init__(self, uow_factory: UowFactory):
        self._uow_factory = uow_factory

    async def execute(
        self,
        *,
        chat_id: int,
        limit: int,
    ) -> list[LeaderboardRowDTO]:
        async with self._uow_factory() as uow:
            ratings = await uow.rating_repo.get_top(
                chat_id=chat_id,
                limit=limit,
            )

            users = await uow.user_repo.get_by_ids(
                [r.user_id for r in ratings]
            )
        ...
