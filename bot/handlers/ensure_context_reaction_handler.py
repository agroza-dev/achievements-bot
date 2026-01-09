from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from bot.handlers.middleware.ensure_context import ensure_context
from bot.ptb_models.reactions import ReactionData

import pprint

from core.dto.bot_context import BotContextDTO


async def ensure_context_reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reaction = update.message_reaction
    if not reaction:
        return


    reaction_data = ReactionData.from_update(update, context)
    
    await ensure_context(
        update=update,
        context=context
    )

    ctx: BotContextDTO = context.bot_data["ctx"]

    

    # user_dto = await UserRepository(db_manager).get_or_create(user)
# 
    # context.bot_data['reaction_ctx'] = BotContextDTO(
        # user=user_dto,
        # chat=chat_dto,
    # )

