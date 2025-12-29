from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ChatDTO:
    id: int
    tg_id: int
    title: str
    type: str
    is_active: bool
    settings: str
    created_at: datetime
    updated_at: datetime
