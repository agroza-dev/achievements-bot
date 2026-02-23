from typing import Protocol

from core.domain.rate_limiting.rate_limit_policy import RateLimitPolicy, RateLimitResult


class RateLimiter(Protocol):
    """Интерфейс для rate limiter."""

    async def check_rate_limit(
        self,
        user_id: int,
        action: str,
        policy: RateLimitPolicy,
    ) -> RateLimitResult:
        """
        Проверить, может ли пользователь выполнить действие.

        Args:
            user_id: ID пользователя
            action: Идентификатор действия (например, 'transfer', 'reaction_add')
            policy: Политика rate limiting

        Returns:
            Результат проверки
        """
        ...

    async def reset(self, user_id: int, action: str | None = None) -> None:
        """
        Сбросить лимиты для пользователя.

        Args:
            user_id: ID пользователя
            action: Конкретное действие или None для всех действий
        """
        ...
