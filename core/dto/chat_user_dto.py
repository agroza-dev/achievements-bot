from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ChatUserDTO:
    id: int
    chat_id: int
    user_id: int
    is_admin: bool
    is_active: bool
    joined_at: datetime


@dataclass(frozen=True)
class UserChatDTO:
    id: int
    chat_id: int
    title: str
