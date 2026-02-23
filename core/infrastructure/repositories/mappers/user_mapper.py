import logging

from asyncpg import Record

from core.dto.user_dto import UserDTO
from utils.logger import prettify

logger = logging.getLogger(__name__)

def map_user(record: Record) -> UserDTO:
    dto = UserDTO(
        id=record["id"],
        tg_id=record["tg_id"],
        username=record["username"],
        first_name=record["first_name"],
        last_name=record["last_name"],
        is_bot=record["is_bot"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )
    logger.debug(f"Mapped user {prettify(dto)}")
    return dto
