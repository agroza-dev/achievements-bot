from dataclasses import dataclass
from datetime import datetime

from telegram import ReactionTypeEmoji


@dataclass
class ReactionData:
    """Dataclass for storing reaction information to be saved to database"""
    chat_id: int
    message_id: int
    user_id: int
    username: str | None
    first_name: str
    last_name: str | None
    is_bot: bool
    is_premium: bool
    language_code: str | None
    timestamp: datetime
    new_reactions: list[ReactionTypeEmoji]
    old_reactions: list[ReactionTypeEmoji]
    action: str  # 'added', 'removed', 'updated'

    @classmethod
    def from_update(cls, update):
        """Create ReactionData instance from Telegram Update object"""
        mr = update.message_reaction
        if not mr:
            raise ValueError("Update does not contain message_reaction data")

        user = mr.user
        chat = mr.chat
        old_reactions = list(mr.old_reaction) if mr.old_reaction else []
        new_reactions = list(mr.new_reaction) if mr.new_reaction else []

        # Determine the action based on old and new reactions
        action = cls._determine_action(old_reactions, new_reactions)

        return cls(
            chat_id=chat.id,
            message_id=mr.message_id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_bot=user.is_bot,
            is_premium=user.is_premium,
            language_code=user.language_code,
            timestamp=mr.date,
            new_reactions=new_reactions,
            old_reactions=old_reactions,
            action=action
        )

    @staticmethod
    def _determine_action(old_reactions: list[ReactionTypeEmoji], new_reactions: list[ReactionTypeEmoji]) -> str:
        """Determine the type of action based on old and new reactions"""
        old_emojis = {r.emoji for r in old_reactions}
        new_emojis = {r.emoji for r in new_reactions}

        if not old_reactions and new_reactions:
            return 'added'
        elif old_reactions and not new_reactions:
            return 'removed'
        elif old_reactions and new_reactions:
            if old_emojis == new_emojis:
                return 'unchanged'
            else:
                return 'updated'
        else:
            return 'unknown'
