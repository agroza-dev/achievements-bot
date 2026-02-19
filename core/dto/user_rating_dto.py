
from dataclasses import dataclass


@dataclass(slots=True)
class UserRatingDTO:
    user_id: int
    rating: int
