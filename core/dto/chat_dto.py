from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ChatDTO:
    id: int
    tg_id: int
    title: str
    type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other):
        if not isinstance(other, ChatDTO):
            return False
        return (
            self.id == other.id
            and self.tg_id == other.tg_id
            and self.title == other.title
            and self.type == other.type
            and self.is_active == other.is_active
            and self.created_at == other.created_at
            and self.updated_at == other.updated_at
        )
