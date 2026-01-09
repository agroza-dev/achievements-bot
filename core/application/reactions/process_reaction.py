from collections.abc import Callable

from core.infrastructure.database import DbUnitOfWork
from core.domain.reactions.reaction_policy import ReactionPolicy
from core.dto.bot_context import BotContextDTO
from core.dto.reaction_dto import ReactionDTO
from core.infrastructure.repositories.rating_repository import DbRatingRepository
from core.infrastructure.repositories.reaction_repository import DbReactionRepository

UowFactory = Callable[[], DbUnitOfWork]

class ProcessReactionUseCase:
    def __init__(self, uow_factory: UowFactory, reaction_policy: ReactionPolicy):
        self.uow_factory = uow_factory
        self.policy = reaction_policy

    async def execute(
        self,
        ctx: BotContextDTO,
    ):
        # реакции на свои сообщения не учитываем
        if ctx.user.tg_id == target_user_id:
            return

        async with self.uow_factory() as uow:
            reaction_repo = uow.get_repo(DbReactionRepository)
            rating_repo = uow.get_repo(DbRatingRepository)

            existing = await reaction_repo.list_for_update(
                chat_id=chat_id,
                message_id=message_id,
                from_user_id=ctx.user.id,
            )

            # toggle: такая реакция уже есть → удаляем
            if any(r.reaction == reaction for r in existing):
                await reaction_repo.delete(
                    chat_id=chat_id,
                    message_id=message_id,
                    from_user_id=ctx.user.id,
                    reaction=reaction,
                )

                await rating_repo.add(
                    target_user_id,
                    -self.policy.rating_delta(reaction),
                )
                return

            # лимит или запрет по policy
            if not self.policy.can_add(existing, reaction):
                return

            # добавление реакции
            await reaction_repo.add(
                ReactionDTO(
                    chat_id=chat_id,
                    message_id=message_id,
                    from_user_id=ctx.user.id,
                    to_user_id=target_user_id,
                    reaction=reaction,
                )
            )

            # начисление рейтинга
            await rating_repo.add(
                chat_id,
                target_user_id,
                self.policy.rating_delta(reaction),
            )

            # налог (пока 0, но архитектурно готов)
            tax = self.policy.tax(reaction)
            if tax:
                await rating_repo.add(ctx.user.id, -tax)
