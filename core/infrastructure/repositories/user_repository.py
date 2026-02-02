import logging

import asyncpg
from telegram import User

from core.dto.user_dto import UserDTO
from core.infrastructure.repositories.mappers.user_mapper import map_user

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_by_tg_id(self, tg_id: int) -> UserDTO | None:
        query = "SELECT * FROM users WHERE tg_id = $1"

        record = await self.conn.fetchrow(query, tg_id)
        return map_user(record) if record else None

    async def upsert(self, user: User) -> UserDTO:
        query = """
            INSERT INTO users (tg_id, username, first_name, last_name, is_bot)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tg_id) DO UPDATE
            SET
                username   = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name  = EXCLUDED.last_name,
                is_bot     = EXCLUDED.is_bot
            RETURNING *
        """
        record = await self.conn.fetchrow(
            query,
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            user.is_bot,
        )

        return map_user(record)

    async def get_by_username(self, chat_id, username) -> UserDTO | None:
        query = """
            SELECT
                users.id,
                users.tg_id,
                users.username,
                users.first_name,
                users.last_name,
                users.is_bot,
                users.created_at,
                users.updated_at
            FROM users
            left join chat_users on users.id = chat_users.user_id
            LEFT JOIN chats On chats.id = chat_users.chat_id
            WHERE username = $1 AND chats.id = $2
        """

        record = await self.conn.fetchrow(
            query,
            username,
            chat_id,
        )
        logger.debug(f"Resolved row by {username} - {record}")
        return map_user(record)

    async def get_by_internal_id(self, user_id) -> UserDTO | None:
        query = "SELECT * FROM users WHERE id = $1"

        record = await self.conn.fetchrow(query, user_id)
        return map_user(record) if record else None

    async def upsert_bot(self, bot_id: int, username: str, first_name: str, last_name: str, added_by: int) -> UserDTO:
        query = """
                INSERT INTO users (tg_id, username, first_name, last_name, is_bot, added_by_user)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tg_id) DO UPDATE
                    SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        is_bot = EXCLUDED.is_bot,
                        added_by_user = EXCLUDED.added_by_user
                RETURNING *
                """
        record = await self.conn.fetchrow(
            query,
            bot_id,
            username,
            first_name,
            last_name,
            True,
            added_by,
        )

        return map_user(record)
