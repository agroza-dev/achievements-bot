from telegram import Update
from telegram.ext import ContextTypes

from core.dto.bot_context import BotContextDTO


async def reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mr = update.message_reaction
    if not mr:
        return
    context: BotContextDTO = context.application.bot_data["ctx"]

