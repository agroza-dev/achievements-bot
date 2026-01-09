from telegram import Update
from telegram.ext import ContextTypes

from core.infrastructure.database import DbUnitOfWork, db_manager
from core.domain.reactions.default_reaction_policy import DefaultReactionPolicy
from core.dto.bot_context import BotContextDTO
from core.application.reactions.process_reaction import ProcessReactionUseCase


async def reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx: BotContextDTO = context.bot_data["ctx"]


    use_case = ProcessReactionUseCase(
        uow_factory=lambda: DbUnitOfWork(db_manager.pool),
        reaction_policy=DefaultReactionPolicy(),
    )

    # await use_case.execute(
        # ctx = ctx,
    # )

