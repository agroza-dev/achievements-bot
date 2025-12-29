from core.repositories.mappers.chat_user_mapper import map_chat_user


class ChatUserRepository:
    def __init__(self, db):
        self.db = db

    async def get_or_create(self, chat_id: int, user_id: int):
        query = """
            INSERT INTO chat_users (chat_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT (chat_id, user_id) DO UPDATE
            SET is_active = true
            RETURNING *
        """
        async with self.db.get_connection() as conn:
            record = await conn.fetchrow(
                query,
                chat_id,
                user_id,
            )
        return map_chat_user(record)

    async def add_user_to_chat(self, chat_id: int, user_id: int, is_admin: bool = False):
        query = """
            INSERT INTO chat_users (chat_id, user_id, is_admin)
            VALUES ($1, $2, $3)
            ON CONFLICT (chat_id, user_id) DO UPDATE
            SET is_active = true, is_admin = $3
            RETURNING *
        """
        async with self.db.get_connection() as conn:
            record = await conn.fetchrow(
                query,
                chat_id,
                user_id,
                is_admin,
            )
        return map_chat_user(record)

    async def remove_user_from_chat(self, chat_id: int, user_id: int):
        query = """
            UPDATE chat_users
            SET is_active = false
            WHERE chat_id = $1 AND user_id = $2
            RETURNING *
        """
        async with self.db.get_connection() as conn:
            record = await conn.fetchrow(
                query,
                chat_id,
                user_id,
            )
        return map_chat_user(record) if record else None

    async def get_chat_user(self, chat_id: int, user_id: int):
        query = """
            SELECT * FROM chat_users
            WHERE chat_id = $1 AND user_id = $2 AND is_active = true
        """
        async with self.db.get_connection() as conn:
            record = await conn.fetchrow(
                query,
                chat_id,
                user_id,
            )
        return map_chat_user(record) if record else None
