#!/usr/bin/env python3
"""
Скрипт для нагрузочного тестирования бота с использованием FakeBotGateway.

Этот скрипт эмулирует действия пользователей без реального Telegram API,
что позволяет проверять:
- Работу rate limiter
- Производительность системы
- Поведение при высокой нагрузке

Примеры использования:
    python -m scripts.load_test
    python -m scripts.load_test --users 50 --requests-per-user 20
    python -m scripts.load_test --scenario burst
"""

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from core.domain.rate_limiting.rate_limit_policy import RateLimitPolicy
from core.infrastructure.bot.fake_bot_gateway import FakeBotGateway
from core.infrastructure.repositories.rate_limiter import InMemoryRateLimiter


@dataclass
class LoadTestResult:
    """Результаты нагрузочного теста."""
    total_users: int
    requests_per_user: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    requests_per_second: float
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def p50_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.5)
        return sorted_latencies[idx]

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_users": self.total_users,
            "requests_per_user": self.requests_per_user,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_time_seconds": round(self.total_time_seconds, 2),
            "requests_per_second": round(self.requests_per_second, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
        }


async def simulate_user(
    user_id: int,
    requests_count: int,
    gateway: FakeBotGateway,
    rate_limiter: InMemoryRateLimiter,
    policy: RateLimitPolicy,
    delay_seconds: float = 0,
) -> tuple[list[float], int, int]:
    """
    Симуляция действий пользователя.

    Returns:
        Кортеж (latencies, allowed_count, blocked_count)
    """
    latencies = []
    allowed_count = 0
    blocked_count = 0

    for i in range(requests_count):
        start = time.perf_counter()

        # Проверка rate limit
        rate_result = await rate_limiter.check_rate_limit(
            user_id=user_id,
            action="send_message",
            policy=policy,
        )

        if rate_result.allowed:
            await gateway.send_message(
                chat_id=user_id,
                text=f"Message {i + 1} from user {user_id}",
            )
            allowed_count += 1
        else:
            blocked_count += 1

        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

    return latencies, allowed_count, blocked_count


async def run_load_test(
    num_users: int,
    requests_per_user: int,
    policy: RateLimitPolicy,
    delay_between_requests: float = 0,
) -> LoadTestResult:
    """Запуск нагрузочного теста."""
    gateway = FakeBotGateway(simulate_delay=False)
    rate_limiter = InMemoryRateLimiter()

    start_time = time.time()

    # Запуск симуляции для всех пользователей
    tasks = [
        simulate_user(
            user_id=user_id,
            requests_count=requests_per_user,
            gateway=gateway,
            rate_limiter=rate_limiter,
            policy=policy,
            delay_seconds=delay_between_requests,
        )
        for user_id in range(1, num_users + 1)
    ]

    results = await asyncio.gather(*tasks)

    # Распаковываем результаты
    all_latencies = []
    total_allowed = 0
    total_blocked = 0
    for latencies, allowed, blocked in results:
        all_latencies.extend(latencies)
        total_allowed += allowed
        total_blocked += blocked

    total_time = time.time() - start_time

    # successful_requests = разрешённые rate limiter (они же отправленные gateway)
    # failed_requests = заблокированные rate limiter
    successful = total_allowed
    failed = total_blocked

    return LoadTestResult(
        total_users=num_users,
        requests_per_user=requests_per_user,
        total_requests=num_users * requests_per_user,
        successful_requests=successful,
        failed_requests=failed,
        total_time_seconds=total_time,
        requests_per_second=(successful + failed) / total_time if total_time > 0 else 0,
        latencies_ms=all_latencies,
    )


async def run_burst_test(
    num_requests: int,
    policy: RateLimitPolicy,
) -> LoadTestResult:
    """Тест всплеска трафика (burst)."""
    gateway = FakeBotGateway(simulate_delay=False)
    rate_limiter = InMemoryRateLimiter()

    start_time = time.time()

    async def make_request(request_id: int):
        start = time.perf_counter()

        rate_result = await rate_limiter.check_rate_limit(
            user_id=1,  # Один пользователь
            action="send_message",
            policy=policy,
        )

        if rate_result.allowed:
            await gateway.send_message(
                chat_id=1,
                text=f"Burst message {request_id}",
            )

        end = time.perf_counter()
        return (end - start) * 1000, rate_result.allowed

    # Все запросы одновременно
    tasks = [make_request(i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks)

    latencies = [r[0] for r in results]
    successful = sum(1 for r in results if r[1])
    failed = sum(1 for r in results if not r[1])

    total_time = time.time() - start_time

    return LoadTestResult(
        total_users=1,
        requests_per_user=num_requests,
        total_requests=num_requests,
        successful_requests=successful,
        failed_requests=failed,
        total_time_seconds=total_time,
        requests_per_second=num_requests / total_time if total_time > 0 else 0,
        latencies_ms=list(latencies),
    )


def print_results(result: LoadTestResult) -> None:
    """Вывод результатов теста."""
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"Пользователей:           {result.total_users}")
    print(f"Запросов на пользователя: {result.requests_per_user}")
    print(f"Всего запросов:          {result.total_requests}")
    print(f"Успешных запросов:       {result.successful_requests}")
    print(f"Заблокировано (rate limit): {result.failed_requests}")
    print("-" * 60)
    print(f"Общее время:             {result.total_time_seconds:.2f} сек")
    print(f"Запросов в секунду:      {result.requests_per_second:.2f} req/s")
    print("-" * 60)
    print("Задержки (latency):")
    print(f"  Средняя:               {result.avg_latency_ms:.2f} мс")
    print(f"  P50 (медиана):         {result.p50_latency_ms:.2f} мс")
    print(f"  P95:                   {result.p95_latency_ms:.2f} мс")
    print(f"  P99:                   {result.p99_latency_ms:.2f} мс")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Нагрузочное тестирование бота с FakeBotGateway"
    )
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Количество пользователей (по умолчанию: 10)",
    )
    parser.add_argument(
        "--requests-per-user",
        type=int,
        default=10,
        help="Запросов на пользователя (по умолчанию: 10)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Задержка между запросами в секундах (по умолчанию: 0)",
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "burst"],
        default="normal",
        help="Сценарий теста (по умолчанию: normal)",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=5,
        help="Лимит запросов на пользователя (по умолчанию: 5)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=60,
        help="Окно rate limit в секундах (по умолчанию: 60)",
    )

    args = parser.parse_args()

    policy = RateLimitPolicy(
        max_requests=args.rate_limit,
        window_seconds=args.window,
        block_duration_seconds=0,
    )

    print("\nЗапуск нагрузочного теста...")
    print(f"Сценарий: {args.scenario}")
    print(f"Пользователей: {args.users}")
    print(f"Запросов на пользователя: {args.requests_per_user}")
    print(f"Rate limit: {args.rate_limit} запросов за {args.window} сек")

    if args.scenario == "burst":
        total_requests = args.users * args.requests_per_user
        result = asyncio.run(run_burst_test(total_requests, policy))
    else:
        result = asyncio.run(
            run_load_test(
                num_users=args.users,
                requests_per_user=args.requests_per_user,
                policy=policy,
                delay_between_requests=args.delay,
            )
        )

    print_results(result)

    # Вывод в JSON формате для парсинга
    print("\nJSON output:")
    import json
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
