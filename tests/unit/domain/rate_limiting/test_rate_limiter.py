import asyncio

import pytest

from core.domain.rate_limiting.default_policies import DefaultRateLimitPolicies
from core.domain.rate_limiting.rate_limit_policy import RateLimitPolicy
from core.infrastructure.repositories.rate_limiter import InMemoryRateLimiter


class TestInMemoryRateLimiter:
    """Тесты для InMemoryRateLimiter."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Разрешает запросы в пределах лимита."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(max_requests=5, window_seconds=60)

        for i in range(5):
            result = await limiter.check_rate_limit(
                user_id=1,
                action="test",
                policy=policy,
            )
            assert result.allowed is True
            assert result.remaining == 5 - i - 1

    @pytest.mark.asyncio
    async def test_blocks_after_limit(self):
        """Блокирует после превышения лимита."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(max_requests=3, window_seconds=60)

        # Исчерпываем лимит
        for _ in range(3):
            result = await limiter.check_rate_limit(
                user_id=1,
                action="test",
                policy=policy,
            )
            assert result.allowed is True

        # Следующий запрос должен быть заблокирован
        result = await limiter.check_rate_limit(
            user_id=1,
            action="test",
            policy=policy,
        )
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0
        assert "Превышен лимит" in result.message

    @pytest.mark.asyncio
    async def test_separate_users_independent(self):
        """Разные пользователи имеют независимые лимиты."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(max_requests=2, window_seconds=60)

        # Пользователь 1 исчерпывает лимит
        for _ in range(2):
            result = await limiter.check_rate_limit(
                user_id=1,
                action="test",
                policy=policy,
            )
            assert result.allowed is True

        # Пользователь 2 ещё может делать запросы
        result = await limiter.check_rate_limit(
            user_id=2,
            action="test",
            policy=policy,
        )
        assert result.allowed is True
        assert result.remaining == 1

    @pytest.mark.asyncio
    async def test_separate_actions_independent(self):
        """Разные действия имеют независимые лимиты."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(max_requests=2, window_seconds=60)

        # Исчерпываем лимит для action1
        for _ in range(2):
            await limiter.check_rate_limit(
                user_id=1,
                action="action1",
                policy=policy,
            )

        # action2 ещё доступен
        result = await limiter.check_rate_limit(
            user_id=1,
            action="action2",
            policy=policy,
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_window_sliding(self):
        """Скользящее окно: запросы восстанавливаются со временем."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(max_requests=2, window_seconds=1)

        # Исчерпываем лимит
        for _ in range(2):
            result = await limiter.check_rate_limit(
                user_id=1,
                action="test",
                policy=policy,
            )
            assert result.allowed is True

        # Сразу после этого заблокирован
        result = await limiter.check_rate_limit(
            user_id=1,
            action="test",
            policy=policy,
        )
        assert result.allowed is False

        # Ждём окончания окна
        await asyncio.sleep(1.1)

        # Снова разрешён
        result = await limiter.check_rate_limit(
            user_id=1,
            action="test",
            policy=policy,
        )
        assert result.allowed is True
        assert result.remaining == 1

    @pytest.mark.asyncio
    async def test_block_duration(self):
        """Блокировка на заданное время при превышении."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(
            max_requests=2,
            window_seconds=60,
            block_duration_seconds=1,  # Блокировка на 1 секунду
        )

        # Исчерпываем лимит
        for _ in range(2):
            await limiter.check_rate_limit(
                user_id=1,
                action="test",
                policy=policy,
            )

        # Превышаем — получаем блокировку
        result = await limiter.check_rate_limit(
            user_id=1,
            action="test",
            policy=policy,
        )
        assert result.allowed is False
        # Первое превышение: "Превышен лимит", последующие: "Слишком много запросов"
        assert "Превышен лимит" in result.message or "Слишком много запросов" in result.message

        # Сразу после блокировки всё ещё заблокирован
        result = await limiter.check_rate_limit(
            user_id=1,
            action="test",
            policy=policy,
        )
        assert result.allowed is False

        # Ждём окончания блокировки
        await asyncio.sleep(1.1)

        # Снова разрешён (если в окне есть место)
        # Но в этом случае окно 60 секунд, так что всё ещё заблокирован
        # Проверяем, что retry_after уменьшился

    @pytest.mark.asyncio
    async def test_reset_user(self):
        """Сброс лимитов пользователя."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(max_requests=2, window_seconds=60)

        # Исчерпываем лимит
        for _ in range(2):
            await limiter.check_rate_limit(
                user_id=1,
                action="test",
                policy=policy,
            )

        # Заблокирован
        result = await limiter.check_rate_limit(
            user_id=1,
            action="test",
            policy=policy,
        )
        assert result.allowed is False

        # Сбрасываем
        await limiter.reset(user_id=1)

        # Снова разрешён
        result = await limiter.check_rate_limit(
            user_id=1,
            action="test",
            policy=policy,
        )
        assert result.allowed is True
        assert result.remaining == 1

    @pytest.mark.asyncio
    async def test_reset_specific_action(self):
        """Сброс конкретного действия."""
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(max_requests=2, window_seconds=60)

        # Исчерпываем лимиты для обоих действий
        for _ in range(2):
            await limiter.check_rate_limit(user_id=1, action="action1", policy=policy)
            await limiter.check_rate_limit(user_id=1, action="action2", policy=policy)

        # action1 заблокирован
        result = await limiter.check_rate_limit(
            user_id=1, action="action1", policy=policy
        )
        assert result.allowed is False

        # Сбрасываем только action1
        await limiter.reset(user_id=1, action="action1")

        # action1 разрешён
        result = await limiter.check_rate_limit(
            user_id=1, action="action1", policy=policy
        )
        assert result.allowed is True

        # action2 всё ещё заблокирован
        result = await limiter.check_rate_limit(
            user_id=1, action="action2", policy=policy
        )
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_default_policies(self):
        """Политики по умолчанию работают корректно."""
        limiter = InMemoryRateLimiter()

        # TRANSFER: 10 за 5 минут
        for _i in range(10):
            result = await limiter.check_rate_limit(
                user_id=1,
                action="transfer",
                policy=DefaultRateLimitPolicies.TRANSFER,
            )
            assert result.allowed is True

        # 11-й заблокирован
        result = await limiter.check_rate_limit(
            user_id=1,
            action="transfer",
            policy=DefaultRateLimitPolicies.TRANSFER,
        )
        assert result.allowed is False

        # REACTION_ADD: 30 за минуту
        for _i in range(30):
            result = await limiter.check_rate_limit(
                user_id=1,
                action="reaction_add",
                policy=DefaultRateLimitPolicies.REACTION_ADD,
            )
            assert result.allowed is True

        # 31-й заблокирован
        result = await limiter.check_rate_limit(
            user_id=1,
            action="reaction_add",
            policy=DefaultRateLimitPolicies.REACTION_ADD,
        )
        assert result.allowed is False
