from asyncpg import Record

from core.dto.chat_dto import ChatDTO


def map_chat(record: Record) -> ChatDTO:
    return ChatDTO(
        id=record["id"],
        tg_id=record["tg_id"],
        title=record["title"],
        type=record["type"],
        is_active=record["is_active"],
        settings=record["settings"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )
