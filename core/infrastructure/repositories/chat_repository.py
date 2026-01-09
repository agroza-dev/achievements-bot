import asyncpg
from telegram import Chat

from core.dto.chat_dto import ChatDTO
from core.infrastructure.repositories.mappers.chat_mapper import map_chat


class ChatRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_by_tg_id(self, tg_id: int) -> ChatDTO | None:
        query = "SELECT * FROM chats WHERE tg_id = $1"

        record = await self.conn.fetchrow(query, tg_id)

        return map_chat(record) if record else None

    async def upsert(self, chat: Chat) -> ChatDTO:
        query = """
            INSERT INTO chats (tg_id, type, title, is_active, settings)
            VALUES ($1, $2, $3, true, '{}')
            ON CONFLICT (tg_id) DO UPDATE
            SET
                type = EXCLUDED.type,
                title = EXCLUDED.title,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """
        record = await self.conn.fetchrow(
            query,
            chat.id,
            chat.type,
            chat.title,
        )

        return map_chat(record)
