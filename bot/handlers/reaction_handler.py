from telegram import Update
from telegram.ext import ContextTypes

from core.models import ReactionData


async def reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mr = update.message_reaction
    if not mr:
        return

    # Extract reaction data using the dataclass
    reaction_data = ReactionData.from_update(update)

    print("=== REACTION DATA ===")
    print(f"Chat ID: {reaction_data.chat_id}")
    print(f"Message ID: {reaction_data.message_id}")
    print(f"User ID: {reaction_data.user_id}")
    print(f"User: {reaction_data.first_name} (@{reaction_data.username})")
    print(f"Action: {reaction_data.action}")
    print(f"Old reactions: {[r.emoji for r in reaction_data.old_reactions]}")
    print(f"New reactions: {[r.emoji for r in reaction_data.new_reactions]}")
    print(reaction_data)

    # This is where we would save to database in the future
    # For now, we just have the structured data ready to be saved
