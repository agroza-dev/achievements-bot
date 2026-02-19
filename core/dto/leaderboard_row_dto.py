from dataclasses import dataclass

from core.dto.user_dto import UserDTO


@dataclass(frozen=True)
class LeaderboardRowDTO:
    user: UserDTO
    rating: int
