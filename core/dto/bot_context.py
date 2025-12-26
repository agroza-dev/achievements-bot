from dataclasses import dataclass

from core.dto.chat_dto import ChatDTO
from core.dto.user_dto import UserDTO


@dataclass(slots=True)
class BotContextDTO:
    user: UserDTO
    chat: ChatDTO
