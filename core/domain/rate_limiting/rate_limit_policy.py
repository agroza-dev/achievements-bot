from dataclasses import dataclass
from enum import Enum, auto


class RateLimitAction(Enum):
    """Действия, которые можно ограничивать."""
    TRANSFER = auto()
    REACTION_ADD = auto()
    REACTION_REMOVE = auto()
    MESSAGE = auto()
    COMMAND = auto()


@dataclass(frozen=True)
class RateLimitPolicy:
    """
    Политика rate limiting.

    Attributes:
        max_requests: Максимальное количество запросов за окно
        window_seconds: Размер окна в секундах
        block_duration_seconds: Длительность блокировки при превышении (0 = нет блокировки)
    """
    max_requests: int
    window_seconds: int
    block_duration_seconds: int = 0

    def __post_init__(self):
        if self.max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.block_duration_seconds < 0:
            raise ValueError("block_duration_seconds cannot be negative")


@dataclass(frozen=True)
class RateLimitResult:
    """Результат проверки rate limit."""
    allowed: bool
    remaining: int  # Осталось запросов в текущем окне
    retry_after: int | None = None  # Через сколько секунд можно повторить (если заблокирован)
    message: str | None = None
