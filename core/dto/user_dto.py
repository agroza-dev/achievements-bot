from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class UserDTO:
    id: int
    tg_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    is_bot: bool
    timezone: str
    created_at: datetime
    updated_at: datetime
