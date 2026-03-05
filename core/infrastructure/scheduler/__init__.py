"""
Модуль планировщика задач.

Архитектура:
- Producer: создаёт batch по расписанию (cron)
- Worker: постоянный цикл обработки batch
"""

from core.infrastructure.scheduler.award_producer import AwardProducer
from core.infrastructure.scheduler.award_scheduler import AwardScheduler
from core.infrastructure.scheduler.award_worker import AwardWorker

__all__ = [
    "AwardProducer",
    "AwardScheduler",
    "AwardWorker",
]
