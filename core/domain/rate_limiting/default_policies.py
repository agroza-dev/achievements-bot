from core.domain.rate_limiting.rate_limit_policy import RateLimitPolicy


class DefaultRateLimitPolicies:
    """Политики rate limiting по умолчанию."""

    # Трансферы очков: 10 за 5 минут, блокировка на 15 минут при превышении
    TRANSFER = RateLimitPolicy(
        max_requests=10,
        window_seconds=300,  # 5 минут
        block_duration_seconds=900,  # 15 минут
    )

    # Добавление реакций: 30 за минуту, без блокировки
    REACTION_ADD = RateLimitPolicy(
        max_requests=30,
        window_seconds=60,  # 1 минута
        block_duration_seconds=0,
    )

    # Удаление реакций: 30 за минуту, без блокировки
    REACTION_REMOVE = RateLimitPolicy(
        max_requests=30,
        window_seconds=60,
        block_duration_seconds=0,
    )

    # Сообщения: 60 за минуту (защита от спама)
    MESSAGE = RateLimitPolicy(
        max_requests=60,
        window_seconds=60,
        block_duration_seconds=0,
    )

    # Команды бота: 20 за минуту
    COMMAND = RateLimitPolicy(
        max_requests=20,
        window_seconds=60,
        block_duration_seconds=0,
    )
