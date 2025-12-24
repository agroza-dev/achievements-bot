import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.models import ReactionData
from core.repositories import ReactionRepository

# Initialize repository
reaction_repo = ReactionRepository()
logger = logging.getLogger(__name__)


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

    # Save to database
    try:
        reaction_id = await reaction_repo.save_reaction(reaction_data)
        print(f"Reaction saved to database with ID: {reaction_id}")
    except Exception as e:
        logger.error(f"Failed to save reaction to database: {e}")
        print(f"Failed to save reaction to database: {e}")
