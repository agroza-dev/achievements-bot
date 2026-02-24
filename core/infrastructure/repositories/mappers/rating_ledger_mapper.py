import json
from typing import Any

from asyncpg import Record

from core.dto.rating_ledger_dto import RatingLedgerEntryDTO, RatingLedgerHistoryEntryDTO, RatingLedgerRecordDTO


def map_rating_ledger_entry(record: Record) -> RatingLedgerEntryDTO:
    """Map database record to RatingLedgerEntryDTO"""
    meta = record["meta"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    elif meta is None:
        meta = {}

    return RatingLedgerEntryDTO(
        chat_id=record["chat_id"],
        user_id=record["user_id"],
        initiator_user_id=record["initiator_user_id"],
        amount=record["amount"],
        balance_after=record["balance_after"],
        operation_type=record["operation_type"],
        operation_subtype=record["operation_subtype"],
        source_type=record["source_type"],
        source_id=record["source_id"],
        meta=meta,
    )

def map_rating_ledger_history_entry(record: Record) -> RatingLedgerHistoryEntryDTO:
    meta = record["meta"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    elif meta is None:
        meta = {}

    return RatingLedgerHistoryEntryDTO(
        chat_id=record["chat_id"],
        user_id=record["user_id"],
        initiator_user_id=record["initiator_user_id"],
        amount=record["amount"],
        balance_after=record["balance_after"],
        operation_type=record["operation_type"],
        operation_subtype=record["operation_subtype"],
        source_type=record["source_type"],
        source_id=record["source_id"],
        meta=meta,
        created_at=record["created_at"],
        initiator_username=record.get("initiator_username"),
    )


def map_rating_ledger_record_to_dto(record: Record) -> RatingLedgerRecordDTO:
    """Map database record to RatingLedgerRecordDTO"""
    meta = record["meta"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    elif meta is None:
        meta = {}

    return RatingLedgerRecordDTO(
        id=record["id"],
        amount=record["amount"],
        operation_type=record["operation_type"],
        operation_subtype=record["operation_subtype"],
        is_reverted=record["is_reverted"],
        meta=meta,
    )


def map_rating_ledger_record_to_dict(record: Record) -> dict[str, Any]:
    """Map database record to dictionary with parsed meta"""
    meta = record["meta"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    elif meta is None:
        meta = {}

    result = dict(record)
    result["meta"] = meta
    return result
