from datetime import datetime

from .database import db_manager
from .models import ReactionData


class ReactionRepository:
    def __init__(self):
        pass

    async def save_reaction(self, reaction_data: ReactionData) -> int:
        """Save a reaction to the database and return the ID of the created record."""
        async with db_manager.get_connection() as conn:
            # Convert reaction emojis to string arrays
            new_reactions = [r.emoji for r in reaction_data.new_reactions] if reaction_data.new_reactions else None
            old_reactions = [r.emoji for r in reaction_data.old_reactions] if reaction_data.old_reactions else None

            query = """
            INSERT INTO reactions (
                chat_id, message_id, user_id, username, first_name, last_name,
                is_bot, is_premium, language_code, timestamp, new_reactions, old_reactions, action
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id
            """

            result = await conn.fetchval(
                query,
                reaction_data.chat_id,
                reaction_data.message_id,
                reaction_data.user_id,
                reaction_data.username,
                reaction_data.first_name,
                reaction_data.last_name,
                reaction_data.is_bot,
                reaction_data.is_premium,
                reaction_data.language_code,
                reaction_data.timestamp,
                new_reactions,
                old_reactions,
                reaction_data.action
            )

            return result

    async def get_reaction_by_id(self, reaction_id: int) -> ReactionData | None:
        """Retrieve a reaction by its ID."""
        async with db_manager.get_connection() as conn:
            query = """
            SELECT chat_id, message_id, user_id, username, first_name, last_name,
                   is_bot, is_premium, language_code, timestamp, new_reactions, old_reactions, action
            FROM reactions WHERE id = $1
            """
            row = await conn.fetchrow(query, reaction_id)

            if not row:
                return None

            # Create a simplified ReactionData-like object
            # In a real implementation, you might want to create proper data transfer objects
            return {
                'chat_id': row['chat_id'],
                'message_id': row['message_id'],
                'user_id': row['user_id'],
                'username': row['username'],
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'is_bot': row['is_bot'],
                'is_premium': row['is_premium'],
                'language_code': row['language_code'],
                'timestamp': row['timestamp'],
                'new_reactions': row['new_reactions'] or [],
                'old_reactions': row['old_reactions'] or [],
                'action': row['action']
            }

    async def get_reactions_by_chat(self, chat_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
        """Retrieve reactions for a specific chat."""
        async with db_manager.get_connection() as conn:
            query = """
            SELECT id, chat_id, message_id, user_id, username, first_name, last_name,
                   is_bot, is_premium, language_code, timestamp, new_reactions, old_reactions, action
            FROM reactions
            WHERE chat_id = $1
            ORDER BY timestamp DESC
            LIMIT $2 OFFSET $3
            """
            rows = await conn.fetch(query, chat_id, limit, offset)

            return [dict(row) for row in rows]

    async def get_reactions_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
        """Retrieve reactions made by a specific user."""
        async with db_manager.get_connection() as conn:
            query = """
            SELECT id, chat_id, message_id, user_id, username, first_name, last_name,
                   is_bot, is_premium, language_code, timestamp, new_reactions, old_reactions, action
            FROM reactions
            WHERE user_id = $1
            ORDER BY timestamp DESC
            LIMIT $2 OFFSET $3
            """
            rows = await conn.fetch(query, user_id, limit, offset)

            return [dict(row) for row in rows]

    async def get_reactions_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 100, offset: int = 0) -> list[dict]:
        """Retrieve reactions within a specific date range."""
        async with db_manager.get_connection() as conn:
            query = """
            SELECT id, chat_id, message_id, user_id, username, first_name, last_name,
                   is_bot, is_premium, language_code, timestamp, new_reactions, old_reactions, action
            FROM reactions
            WHERE timestamp BETWEEN $1 AND $2
            ORDER BY timestamp DESC
            LIMIT $3 OFFSET $4
            """
            rows = await conn.fetch(query, start_date, end_date, limit, offset)

            return [dict(row) for row in rows]

    async def get_reaction_stats(self) -> dict:
        """Get basic statistics about reactions."""
        async with db_manager.get_connection() as conn:
            # Total count
            total_query = "SELECT COUNT(*) FROM reactions"
            total_count = await conn.fetchval(total_query)

            # Count by action
            action_query = "SELECT action, COUNT(*) FROM reactions GROUP BY action"
            action_counts = await conn.fetch(action_query)

            # Recent reactions
            recent_query = "SELECT * FROM reactions ORDER BY timestamp DESC LIMIT 5"
            recent_reactions = await conn.fetch(recent_query)

            return {
                'total_count': total_count,
                'action_counts': {row['action']: row['count'] for row in action_counts},
                'recent_reactions': [dict(row) for row in recent_reactions]
            }
