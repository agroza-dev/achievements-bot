from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from bot.handlers.middleware.ensure_context import ensure_context


async def ensure_context_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    await ensure_context(
        update=update,
        context=context
    )
