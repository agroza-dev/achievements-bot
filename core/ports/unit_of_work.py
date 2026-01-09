from typing import Protocol

from core.ports.repositories.rating_repository import RatingRepository
from core.ports.repositories.reaction_repository import ReactionRepository


class UnitOfWork(Protocol):
    reaction_repo: ReactionRepository
    rating_repo: RatingRepository

    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc, tb): ...
