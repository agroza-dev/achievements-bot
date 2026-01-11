import asyncpg


class DbRatingRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def add(
        self,
        chat_id: int,
        user_id: int,
        value: int,
    ) -> None:
        """
        Добавить значение к рейтингу пользователя в чате.
        Если записи не существует, создает её с начальным рейтингом.
        """
        await self.conn.execute(
            """
            INSERT INTO chat_users (chat_id, user_id, rating, is_active)
            VALUES ($2, $3, $1, true)
            ON CONFLICT (chat_id, user_id) 
            DO UPDATE SET 
                rating = chat_users.rating + $1,
                is_active = true
            """,
            value,
            chat_id,
            user_id,
        )
