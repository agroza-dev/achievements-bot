import json
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class PostgreSQLBotPersistenceRepository:
    """PostgreSQL реализация репозитория для хранения данных персистентности бота."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_bot_data(self) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            query = """
                SELECT bot_data FROM bot_persistence
                WHERE id = 0
            """
            record = await conn.fetchrow(query)
            if record is None:
                return {}
            return record["bot_data"] or {}

    async def set_bot_data(self, data: dict[str, Any]) -> None:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO bot_persistence (id, bot_data)
                VALUES (0, $1)
                ON CONFLICT (id) DO UPDATE
                SET bot_data = EXCLUDED.bot_data, updated_at = NOW()
            """
            await conn.execute(query, json.dumps(data))

    async def get_chat_data(self, chat_id: int) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            query = """
                SELECT chat_data FROM bot_persistence
                WHERE chat_id = $1
            """
            record = await conn.fetchrow(query, chat_id)
            if record is None:
                return {}
            return record["chat_data"] or {}

    async def set_chat_data(self, chat_id: int, data: dict[str, Any]) -> None:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO bot_persistence (chat_id, chat_data)
                VALUES ($1, $2)
                ON CONFLICT (chat_id) DO UPDATE
                SET chat_data = EXCLUDED.chat_data, updated_at = NOW()
                WHERE bot_persistence.user_id IS NULL
            """
            await conn.execute(query, chat_id, json.dumps(data))

    async def get_user_data(self, user_id: int) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            query = """
                SELECT user_data FROM bot_persistence
                WHERE user_id = $1
            """
            record = await conn.fetchrow(query, user_id)
            if record is None:
                return {}
            return record["user_data"] or {}

    async def set_user_data(self, user_id: int, data: dict[str, Any]) -> None:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO bot_persistence (user_id, user_data)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET user_data = EXCLUDED.user_data, updated_at = NOW()
                WHERE bot_persistence.chat_id IS NULL
            """
            await conn.execute(query, user_id, json.dumps(data))

    async def drop_chat_data(self, chat_id: int) -> None:
        async with self.pool.acquire() as conn:
            query = """
                DELETE FROM bot_persistence
                WHERE chat_id = $1
            """
            await conn.execute(query, chat_id)

    async def drop_user_data(self, user_id: int) -> None:
        async with self.pool.acquire() as conn:
            query = """
                DELETE FROM bot_persistence
                WHERE user_id = $1
            """
            await conn.execute(query, user_id)

    async def get_all_chat_ids(self) -> list[int]:
        async with self.pool.acquire() as conn:
            query = """
                SELECT chat_id FROM bot_persistence
                WHERE chat_id IS NOT NULL
            """
            records = await conn.fetch(query)
            return [r["chat_id"] for r in records]

    async def get_all_user_ids(self) -> list[int]:
        async with self.pool.acquire() as conn:
            query = """
                SELECT user_id FROM bot_persistence
                WHERE user_id IS NOT NULL
            """
            records = await conn.fetch(query)
            return [r["user_id"] for r in records]
