import json

import asyncpg

from core.dto.chat_message_create_dto import ChatMessageCreateDTO
from core.dto.chat_message_dto import ChatMessageDTO
from core.infrastructure.repositories.mappers.chat_message_mapper import ChatMessageMapper


class DbChatMessageRepository:

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_by_tg_id(self, chat_id: int, tg_message_id: int) -> ChatMessageDTO | None:
        row = await self.conn.fetchrow(
            """
            SELECT id, chat_id, tg_message_id, author_user_id, message_type, message_meta, created_at, stored_at
            FROM chat_messages
            WHERE chat_id = $1 AND tg_message_id = $2
            """,
            chat_id,
            tg_message_id,
        )
        if row is None:
            return None

        return ChatMessageMapper.from_record(row)

    async def add(
            self,
            message: ChatMessageCreateDTO,
    ) -> ChatMessageDTO | None:
        row = await self.conn.fetchrow(
            """
            INSERT INTO chat_messages (
                chat_id,
                tg_message_id,
                author_user_id,
                message_type,
                message_meta,
                created_at
            )
            VALUES (
                $1, $2, $3, $4, $5, $6
            )
            ON CONFLICT (chat_id, tg_message_id)
            DO NOTHING
            RETURNING
                id,
                chat_id,
                tg_message_id,
                author_user_id,
                message_type,
                message_meta,
                created_at,
                stored_at
            """,
            message.chat_id,
            message.tg_message_id,
            message.author_user_id,
            message.message_type,
            json.dumps(message.message_meta),
            message.created_at,
        )

        if not row:
            return await self.get_by_tg_id(
                message.chat_id,
                message.tg_message_id,
            )

        return ChatMessageMapper.from_record(row)
