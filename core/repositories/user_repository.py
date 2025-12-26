from core.repositories.mappers.user_mapper import map_user


class UserRepository:
    def __init__(self, db):
        self.db = db

    async def get_or_create(self, user):
        query = """
            INSERT INTO users (tg_id, username, first_name, last_name, is_bot)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tg_id) DO UPDATE
            SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                is_bot = EXCLUDED.is_bot
            RETURNING *
        """
        async with self.db.get_connection() as conn:
            record = await conn.fetchrow(
                query,
                user.id,
                user.username,
                user.first_name,
                user.last_name,
                user.is_bot,
            )
        return map_user(record)
