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
        await self.conn.execute(
            """
            UPDATE chat_users
            SET rating = rating + $1
            WHERE chat_id = $2 AND user_id = $3
            """,
            value,
            chat_id,
            user_id,
        )
