from core.repositories.mappers.chat_mapper import map_chat


class ChatRepository:
    def __init__(self, db):
        self.db = db

    async def get_or_create(self, group):
        query = """
            INSERT INTO chats (tg_id, type, title)
            VALUES ($1, $2, $3)
            ON CONFLICT (tg_id) DO UPDATE
            SET
                type = EXCLUDED.type,
                title = EXCLUDED.title
            RETURNING *
        """
        async with self.db.get_connection() as conn:
            record =  await conn.fetchrow(
                query,
                group.id,
                group.type,
                group.title,
            )
        return map_chat(record)
