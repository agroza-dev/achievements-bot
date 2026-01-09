from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ChatMessageDTO:
    id: int
    chat_id: int
    tg_message_id: int

    author_user_id: int | None

    message_type: str
    message_meta: dict
    created_at: datetime
    stored_at: datetime | None
