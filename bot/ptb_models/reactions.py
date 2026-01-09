import pprint
from dataclasses import dataclass
from datetime import datetime

from telegram import ReactionTypeEmoji, Update
from telegram.ext import (
    ContextTypes,
)


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
    target_reaction: str | None = None  # The specific reaction that caused the event

    @classmethod
    def from_update(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create ReactionData instance from Telegram Update object"""
        mr = update.message_reaction
        if not mr:
            raise ValueError("Update does not contain message_reaction data")


        user = mr.user
        chat = mr.chat
        old_reactions = list(mr.old_reaction) if mr.old_reaction else []
        new_reactions = list(mr.new_reaction) if mr.new_reaction else []
        pprint.pprint(update.message)
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
            action=action,
            target_reaction=cls._determine_target_reaction(old_reactions, new_reactions, action)
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
            elif new_emojis.issuperset(old_emojis):
                # New emojis contain all old emojis plus additional ones - this is an addition
                return 'added'
            elif old_emojis.issuperset(new_emojis):
                # Old emojis contain all new emojis - this is a removal
                return 'removed'
            else:
                # Mixed changes - some added, some removed - this is an update
                return 'updated'
        else:
            return 'unknown'

    @staticmethod
    def _determine_target_reaction(old_reactions: list[ReactionTypeEmoji], new_reactions: list[ReactionTypeEmoji], action: str) -> str | None:
        """Determine the target reaction that caused the event"""
        old_emojis = {r.emoji for r in old_reactions}
        new_emojis = {r.emoji for r in new_reactions}

        if action == 'added':
            # For added reactions, return the emoji(s) that were added
            added_emojis = new_emojis - old_emojis
            # If multiple emojis were added, we'll return the first one (or we could return all)
            return next(iter(added_emojis)) if added_emojis else (new_emojis.pop() if new_emojis else None)
        elif action == 'removed':
            # For removed reactions, return the emoji(s) that were removed
            removed_emojis = old_emojis - new_emojis
            return next(iter(removed_emojis)) if removed_emojis else (old_emojis.pop() if old_emojis else None)
        elif action == 'updated':
            # For updated reactions, we can return one of the changed emojis
            # Let's return one that was either added or removed
            changed_emojis = old_emojis.symmetric_difference(new_emojis)
            return next(iter(changed_emojis)) if changed_emojis else None
        elif action == 'unchanged':
            # For unchanged, there's no specific target reaction that caused an event
            # but we could return one of the reactions
            return next(iter(new_emojis)) if new_emojis else None
        else:
            # For unknown action, return None
            return None
