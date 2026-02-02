from dataclasses import dataclass
from enum import Enum


class TransferStatus(str, Enum):
    INFO = 'info'
    SUCCESS = "success"
    INVALID = "invalid"
    FORBIDDEN = "forbidden"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    NOT_FOUND = "not_found"
    QUIET_STOP = "quiet_stop"


@dataclass(frozen=True)
class TransferResult:
    status: TransferStatus
    message: str | None = None
