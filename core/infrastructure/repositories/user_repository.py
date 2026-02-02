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
