"""Тесты для rate limiter с использованием FakeBotGateway."""

import asyncio

import pytest

from core.domain.rate_limiting.rate_limit_policy import RateLimitPolicy
from core.infrastructure.bot.fake_bot_gateway import FakeBotGateway
from core.infrastructure.repositories.rate_limiter import InMemoryRateLimiter


@pytest.fixture
def rate_limiter():
    """Создать InMemoryRateLimiter для тестов."""
    return InMemoryRateLimiter()


@pytest.fixture
def fake_gateway():
    """Создать FakeBotGateway для тестов."""
    return FakeBotGateway()


class TestRateLimiterWithFakeGateway:
    """Тесты rate limiter с FakeBotGateway."""

    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self, rate_limiter: InMemoryRateLimiter):
        """Тест: запросы в пределах лимита разрешены."""
        policy = RateLimitPolicy(
            max_requests=5,
            window_seconds=60,
            block_duration_seconds=0,
        )

        # Первые 5 запросов должны пройти
        for i in range(5):
            result = await rate_limiter.check_rate_limit(
                user_id=123,
                action="send_message",
                policy=policy,
            )
            assert result.allowed is True
            assert result.remaining == 4 - i

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter: InMemoryRateLimiter):
        """Тест: превышение лимита блокирует запросы."""
        policy = RateLimitPolicy(
            max_requests=3,
            window_seconds=60,
            block_duration_seconds=0,
        )

        # Первые 3 запроса проходят
        for _ in range(3):
            result = await rate_limiter.check_rate_limit(
                user_id=123,
                action="send_message",
                policy=policy,
            )
            assert result.allowed is True

        # 4-й запрос блокируется
        result = await rate_limiter.check_rate_limit(
            user_id=123,
            action="send_message",
            policy=policy,
        )
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_rate_limit_with_blocking(
        self,
        rate_limiter: InMemoryRateLimiter,
    ):
        """Тест: блокировка при превышении лимита."""
        policy = RateLimitPolicy(
            max_requests=2,
            window_seconds=60,
            block_duration_seconds=5,  # Блокировка на 5 секунд
        )

        # Первые 2 запроса проходят
        await rate_limiter.check_rate_limit(123, "send_message", policy)
        await rate_limiter.check_rate_limit(123, "send_message", policy)

        # 3-й запрос вызывает блокировку
        result = await rate_limiter.check_rate_limit(123, "send_message", policy)
        assert result.allowed is False
        assert result.retry_after is not None

        # Следующий запрос также блокируется (block_until активен)
        result = await rate_limiter.check_rate_limit(123, "send_message", policy)
        assert result.allowed is False
        assert "Попробуйте через" in result.message

    @pytest.mark.asyncio
    async def test_rate_limit_per_user_isolation(
        self,
        rate_limiter: InMemoryRateLimiter,
    ):
        """Тест: лимиты изолированы между пользователями."""
        policy = RateLimitPolicy(
            max_requests=2,
            window_seconds=60,
            block_duration_seconds=0,
        )

        # Пользователь 1 исчерпывает лимит
        for _ in range(2):
            await rate_limiter.check_rate_limit(111, "send_message", policy)
        result = await rate_limiter.check_rate_limit(111, "send_message", policy)
        assert result.allowed is False

        # Пользователь 2 ещё может делать запросы
        result = await rate_limiter.check_rate_limit(222, "send_message", policy)
        assert result.allowed is True
        assert result.remaining == 1

    @pytest.mark.asyncio
    async def test_rate_limit_per_action_isolation(
        self,
        rate_limiter: InMemoryRateLimiter,
    ):
        """Тест: лимиты изолированы между действиями."""
        policy = RateLimitPolicy(
            max_requests=2,
            window_seconds=60,
            block_duration_seconds=0,
        )

        # Пользователь исчерпывает лимит на send_message
        for _ in range(2):
            await rate_limiter.check_rate_limit(123, "send_message", policy)
        result = await rate_limiter.check_rate_limit(123, "send_message", policy)
        assert result.allowed is False

        # Но ещё может делать set_reaction
        result = await rate_limiter.check_rate_limit(123, "set_reaction", policy)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, rate_limiter: InMemoryRateLimiter):
        """Тест: сброс лимита."""
        policy = RateLimitPolicy(
            max_requests=2,
            window_seconds=60,
            block_duration_seconds=0,
        )

        # Исчерпать лимит
        for _ in range(2):
            await rate_limiter.check_rate_limit(123, "send_message", policy)
        result = await rate_limiter.check_rate_limit(123, "send_message", policy)
        assert result.allowed is False

        # Сбросить лимит
        await rate_limiter.reset(123, "send_message")

        # Теперь запрос снова разрешён
        result = await rate_limiter.check_rate_limit(123, "send_message", policy)
        assert result.allowed is True
        assert result.remaining == 1

    @pytest.mark.asyncio
    async def test_reset_all_user_limits(self, rate_limiter: InMemoryRateLimiter):
        """Тест: сброс всех лимитов пользователя."""
        policy = RateLimitPolicy(
            max_requests=2,
            window_seconds=60,
            block_duration_seconds=0,
        )

        # Исчерпать лимиты на разные действия
        for _ in range(2):
            await rate_limiter.check_rate_limit(123, "send_message", policy)
            await rate_limiter.check_rate_limit(123, "set_reaction", policy)

        # Сбросить все лимиты пользователя
        await rate_limiter.reset(123)

        # Теперь все действия снова разрешены
        result1 = await rate_limiter.check_rate_limit(123, "send_message", policy)
        result2 = await rate_limiter.check_rate_limit(123, "set_reaction", policy)
        assert result1.allowed is True
        assert result2.allowed is True


class TestLoadSimulationWithFakeGateway:
    """Симуляция нагрузки с FakeBotGateway."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_rate_limit(
        self,
        rate_limiter: InMemoryRateLimiter,
    ):
        """Тест: одновременные запросы и rate limiting."""
        policy = RateLimitPolicy(
            max_requests=10,
            window_seconds=60,
            block_duration_seconds=0,
        )

        async def make_request(user_id: int, request_num: int):
            return await rate_limiter.check_rate_limit(
                user_id=user_id,
                action="send_message",
                policy=policy,
            )

        # 15 одновременных запросов от одного пользователя
        tasks = [make_request(123, i) for i in range(15)]
        results = await asyncio.gather(*tasks)

        # Первые 10 должны пройти
        allowed_count = sum(1 for r in results if r.allowed)
        blocked_count = sum(1 for r in results if not r.allowed)

        assert allowed_count == 10
        assert blocked_count == 5

    @pytest.mark.asyncio
    async def test_load_simulation_multiple_users(
        self,
        rate_limiter: InMemoryRateLimiter,
        fake_gateway: FakeBotGateway,
    ):
        """Тест: симуляция нагрузки от множества пользователей."""
        policy = RateLimitPolicy(
            max_requests=5,
            window_seconds=60,
            block_duration_seconds=0,
        )

        # Симуляция 20 пользователей, каждый делает по 10 запросов
        async def user_scenario(user_id: int):
            results = []
            for _ in range(10):
                result = await rate_limiter.check_rate_limit(
                    user_id=user_id,
                    action="send_message",
                    policy=policy,
                )
                if result.allowed:
                    await fake_gateway.send_message(user_id, f"Message from user {user_id}")
                results.append(result)
            return results

        tasks = [user_scenario(user_id) for user_id in range(1, 21)]
        all_results = await asyncio.gather(*tasks)

        # Каждый пользователь должен иметь 5 разрешённых и 5 заблокированных
        for user_id, results in enumerate(all_results, start=1):
            allowed_count = sum(1 for r in results if r.allowed)
            assert allowed_count == 5, f"User {user_id} should have 5 allowed requests"

        # FakeGateway должен был отправить 100 сообщений (20 users * 5 messages)
        assert len(fake_gateway.sent_messages) == 100

        stats = fake_gateway.get_stats()
        assert stats["send_message"] == 100
        assert stats["total_calls"] == 100

    @pytest.mark.asyncio
    async def test_burst_traffic_simulation(
        self,
        rate_limiter: InMemoryRateLimiter,
        fake_gateway: FakeBotGateway,
    ):
        """Тест: симуляция всплеска трафика."""
        policy = RateLimitPolicy(
            max_requests=100,
            window_seconds=10,
            block_duration_seconds=5,
        )

        # Симуляция burst: 150 запросов за короткое время
        async def burst_request(user_id: int):
            results = []
            for _ in range(150):
                result = await rate_limiter.check_rate_limit(
                    user_id=user_id,
                    action="send_message",
                    policy=policy,
                )
                if result.allowed:
                    await fake_gateway.send_message(user_id, "Burst message")
                results.append(result)
            return results

        results = await burst_request(123)

        allowed_count = sum(1 for r in results if r.allowed)
        blocked_count = sum(1 for r in results if not r.allowed)

        # Первые 100 запросов прошли, остальные 50 заблокированы
        assert allowed_count == 100
        assert blocked_count == 50

        # Последние заблокированные запросы должны иметь сообщение о блокировке
        blocked_results = [r for r in results if not r.allowed]
        assert any("Попробуйте через" in r.message for r in blocked_results)
