import json

import asyncpg

from core.dto.rating_ledger_dto import RatingLedgerEntryDTO, RatingLedgerHistoryEntryDTO, RatingLedgerRecordDTO
from core.infrastructure.repositories.mappers.rating_ledger_mapper import (
    map_rating_ledger_history_entry,
    map_rating_ledger_record_to_dto,
)


class DbRatingLedgerRepository:
    """Репозиторий для работы с rating_ledger"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def add(self, entry: RatingLedgerEntryDTO) -> None:
        """Добавить запись в rating_ledger"""
        await self.conn.execute(
            """
            INSERT INTO rating_ledger (
                chat_id,
                user_id,
                initiator_user_id,
                counterparty_user_id,
                amount,
                balance_after,
                operation_type,
                operation_subtype,
                source_type,
                source_id,
                meta
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            entry.chat_id,
            entry.user_id,
            entry.initiator_user_id,
            entry.counterparty_user_id,
            entry.amount,
            entry.balance_after,
            entry.operation_type,
            entry.operation_subtype,
            entry.source_type,
            entry.source_id,
            json.dumps(entry.meta),
        )

    async def find_by_source(
        self, source_type: str, source_id: int, chat_id: int, user_id: int
    ) -> list[RatingLedgerRecordDTO] | None:
        """Найти записи в rating_ledger по source_type и source_id"""
        rows = await self.conn.fetch(
            """
            SELECT id, amount, operation_type, operation_subtype, is_reverted, meta
            FROM rating_ledger
            WHERE source_type = $1
              AND source_id = $2
              AND chat_id = $3
              AND user_id = $4
            ORDER BY created_at DESC
            LIMIT 10
            """,
            source_type,
            source_id,
            chat_id,
            user_id,
        )
        return [map_rating_ledger_record_to_dto(row) for row in rows]

    async def mark_as_reverted_by_emoji(
        self, source_type: str, source_id: int, chat_id: int, user_id: int, reverted_by_id: int, emoji: str
    ) -> None:
        """Пометить запись в rating_ledger как отмененную по эмодзи"""
        await self.conn.execute(
            """
            UPDATE rating_ledger
            SET is_reverted = true,
                reverted_at = NOW(),
                reverted_by_id = $5
            WHERE source_type = $1
              AND source_id = $2
              AND chat_id = $3
              AND user_id = $4
              AND is_reverted = false
              AND operation_type = 'reaction'
              AND operation_subtype = 'added'
              AND meta->>'emoji' = $6
            """,
            source_type,
            source_id,
            chat_id,
            user_id,
            reverted_by_id,
            emoji,
        )

    async def list_for_user(
        self,
        *,
        user_id: int,
        chat_id: int | None,
        limit: int,
        offset: int,
    ) -> list[RatingLedgerHistoryEntryDTO]:
        query = """
            SELECT
                rl.chat_id,
                rl.user_id,
                rl.initiator_user_id,
                rl.amount,
                rl.balance_after,
                rl.operation_type,
                rl.operation_subtype,
                rl.source_type,
                rl.source_id,
                rl.counterparty_user_id,
                rl.meta,
                rl.created_at,
                u.username as initiator_username,
                cu.username as counterparty_username
            FROM rating_ledger rl
            LEFT JOIN users u ON rl.initiator_user_id = u.id
            LEFT JOIN users cu ON rl.counterparty_user_id = cu.id
            WHERE rl.user_id = $1
              AND ($2::BIGINT IS NULL OR rl.chat_id = $2)
            ORDER BY rl.created_at DESC
            LIMIT $3 OFFSET $4
        """

        rows = await self.conn.fetch(
            query,
            user_id,
            chat_id,
            limit,
            offset,
        )

        return [map_rating_ledger_history_entry(row) for row in rows]
