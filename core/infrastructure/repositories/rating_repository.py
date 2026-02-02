import asyncpg


class DbRatingRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def add(
        self,
        chat_id: int,
        user_id: int,
        value: int,
    ) -> int:
        """
        Добавить значение к рейтингу пользователя в чате.
        Если записи не существует, создает её с начальным рейтингом.

        Returns:
            Новый баланс рейтинга после изменения
        """
        result = await self.conn.fetchval(
            """
            INSERT INTO chat_users (chat_id, user_id, rating, is_active)
            VALUES ($2, $3, $1, true)
            ON CONFLICT (chat_id, user_id)
            DO UPDATE SET
                rating = chat_users.rating + $1,
                is_active = true
            RETURNING rating
            """,
            value,
            chat_id,
            user_id,
        )
        return result or 0

    async def get_current(
        self,
        chat_id: int,
        user_id: int,
    ) -> int:
        result = await self.conn.fetchval(
            """
            SELECT rating FROM chat_users
            where chat_id = $1 and user_id = $2
            """,
            chat_id,
            user_id,
        )
        return result or 0
