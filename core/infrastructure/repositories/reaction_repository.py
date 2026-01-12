import asyncpg

from core.dto.reaction_dto import ReactionDTO
from core.infrastructure.repositories.mappers.reaction_mapper import ReactionMapper


class DbReactionRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def list_for_update(
        self,
        chat_id: int,
        message_id: int,
        from_user_id: int,
    ) -> list[ReactionDTO]:
        rows = await self.conn.fetch(
            """
            SELECT
                chat_id,
                message_id,
                from_user_id,
                to_user_id,
                reaction
            FROM reactions
            WHERE chat_id = $1
              AND message_id = $2
              AND from_user_id = $3
            FOR UPDATE
            """,
            chat_id,
            message_id,
            from_user_id,
        )

        return [ReactionMapper.from_record(row) for row in rows]

    async def add(self, reaction: ReactionDTO) -> None:
        await self.conn.execute(
            """
            INSERT INTO reactions (
                chat_id,
                message_id,
                from_user_id,
                to_user_id,
                reaction
            )
            VALUES ($1, $2, $3, $4, $5)
            """,
            reaction.chat_id,
            reaction.message_id,
            reaction.from_user_id,
            reaction.to_user_id,
            reaction.reaction,
        )

    async def delete(
        self,
        chat_id: int,
        message_id: int,
        from_user_id: int,
        reaction: str,
    ) -> None:
        await self.conn.execute(
            """
            DELETE FROM reactions
            WHERE chat_id = $1
              AND message_id = $2
              AND from_user_id = $3
              AND reaction = $4
            """,
            chat_id,
            message_id,
            from_user_id,
            reaction,
        )

    async def delete_if_exists(
        self,
        chat_id: int,
        message_id: int,
        from_user_id: int,
        reaction: str,
    ) -> bool:
        """
        Удалить реакцию, если она существует. Возвращает True, если реакция была удалена.

        Args:
            chat_id: ID чата
            message_id: ID сообщения
            from_user_id: ID пользователя, который поставил реакцию
            reaction: Эмодзи реакции

        Returns:
            bool: True, если реакция была удалена, иначе False
        """
        result = await self.conn.execute(
            """
            DELETE FROM reactions
            WHERE chat_id = $1
              AND message_id = $2
              AND from_user_id = $3
              AND reaction = $4
            """,
            chat_id,
            message_id,
            from_user_id,
            reaction,
        )

        # asyncpg возвращает строку с информацией о выполнении, например "DELETE 1" или "DELETE 0"
        deleted_count = int(result.split(" ")[-1])
        return deleted_count > 0
