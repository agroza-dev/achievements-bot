from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from bot.handlers.middleware.ensure_context import ensure_context


async def ensure_context_reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reaction = update.message_reaction
    if not reaction:
        return

    await ensure_context(
        update=update,
        context=context
    )
