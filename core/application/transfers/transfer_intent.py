from dataclasses import dataclass
from enum import Enum


class TransferDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass(frozen=True)
class TransferIntent:
    amount: int
    direction: TransferDirection
