from asyncpg import Record

from core.dto.chat_user_dto import ChatUserDTO


def map_chat_user(record: Record) -> ChatUserDTO:
    return ChatUserDTO(
        id=record["id"],
        chat_id=record["chat_id"],
        user_id=record["user_id"],
        is_admin=record["is_admin"],
        is_active=record["is_active"],
        joined_at=record["joined_at"],
    )
