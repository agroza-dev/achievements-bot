import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field

from core.domain.rate_limiting.errors import InvalidRateLimitConfigError
from core.domain.rate_limiting.rate_limit_policy import RateLimitPolicy, RateLimitResult
from core.ports.repositories.rate_limiter import RateLimiter


@dataclass
class _WindowEntry:
    """Запись в скользящем окне."""
    timestamps: list[float] = field(default_factory=list)
    blocked_until: float = 0.0


class InMemoryRateLimiter(RateLimiter):
    """
    In-memory реализация rate limiting на основе скользящего окна.

    Для MVP. В production заменить на Redis-based реализацию.
    """

    def __init__(self):
        # Ключ: (user_id, action) -> WindowEntry
        self._windows: dict[tuple[int, str], _WindowEntry] = defaultdict(_WindowEntry)
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self,
        user_id: int,
        action: str,
        policy: RateLimitPolicy,
    ) -> RateLimitResult:
        """Проверить лимит с использованием скользящего окна."""
        self._validate_policy(policy)

        key = (user_id, action)
        now = time.time()

        async with self._lock:
            entry = self._windows[key]

            # Проверка блокировки
            if entry.blocked_until > now:
                retry_after = int(entry.blocked_until - now) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    message=f"Слишком много запросов. Попробуйте через {retry_after} сек.",
                )

            # Очистка старых записей за пределами окна
            window_start = now - policy.window_seconds
            entry.timestamps = [ts for ts in entry.timestamps if ts > window_start]

            # Проверка лимита
            if len(entry.timestamps) >= policy.max_requests:
                # Превышен лимит
                if policy.block_duration_seconds > 0:
                    # Блокируем пользователя
                    entry.blocked_until = now + policy.block_duration_seconds

                # Вычисляем, когда освободится место в окне
                oldest_timestamp = min(entry.timestamps) if entry.timestamps else now
                retry_after = int(oldest_timestamp + policy.window_seconds - now) + 1

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    message=f"Превышен лимит ({policy.max_requests} за {policy.window_seconds} сек.)",
                )

            # Запись текущего запроса
            entry.timestamps.append(now)
            remaining = policy.max_requests - len(entry.timestamps)

            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after=None,
                message=None,
            )

    async def reset(self, user_id: int, action: str | None = None) -> None:
        """Сбросить лимиты."""
        async with self._lock:
            if action is None:
                # Сброс всех действий пользователя
                keys_to_delete = [key for key in self._windows if key[0] == user_id]
                for key in keys_to_delete:
                    del self._windows[key]
            else:
                # Сброс конкретного действия
                key = (user_id, action)
                if key in self._windows:
                    del self._windows[key]

    def _validate_policy(self, policy: RateLimitPolicy) -> None:
        """Валидация политики."""
        if policy.max_requests <= 0:
            raise InvalidRateLimitConfigError("max_requests must be positive")
        if policy.window_seconds <= 0:
            raise InvalidRateLimitConfigError("window_seconds must be positive")
