class RateLimitExceededError(Exception):
    """Превышен лимит запросов."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class InvalidRateLimitConfigError(Exception):
    """Некорректная конфигурация rate limiting."""
    pass
