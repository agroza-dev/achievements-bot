from asyncpg import Record

from core.dto.user_dto import UserDTO


def map_user(record: Record) -> UserDTO:
    return UserDTO(
        id=record["id"],
        tg_id=record["tg_id"],
        username=record["username"],
        first_name=record["first_name"],
        last_name=record["last_name"],
        is_bot=record["is_bot"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )
