"""
Worker для обработки пакетов периодических зачислений.

Постоянный цикл:
1. Берёт следующий pending/processing batch
2. Обрабатывает пользователей батчами по 50
3. Обновляет cursor
4. Помечает batch как done когда все пользователи обработаны

Надёжность:
- Idempotency через Ledger (UNIQUE(user_id, operation_type, operation_key))
- Resume через cursor_user_id
- Crash-safe: при падении batch остаётся processing и продолжается
"""

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

import asyncpg

from core.config import periodic_award_config
from core.infrastructure.repositories.award_batch_repository import AwardBatchRepository
from core.infrastructure.repositories.chat_settings_repository import ChatSettingsRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository

if TYPE_CHECKING:
    from core.infrastructure.database import DatabaseManager

logger = logging.getLogger(__name__)


class AwardWorker:
    """
    Worker для обработки периодических зачислений.

    Запускается как фоновая задача и обрабатывает batch из БД.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
    ):
        self.db_manager = db_manager
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Запустить worker в фоновом режиме."""
        if self._running:
            logger.warning("Worker уже запущен")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Award worker запущен")

    async def stop(self) -> None:
        """Остановить worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Award worker остановлен")

    async def _run_loop(self) -> None:
        """Основной цикл worker."""
        logger.info("Worker цикл запущен")

        # Восстанавливаем stuck batch при старте
        async with self.db_manager.pool.acquire() as conn:
            batch_repo = AwardBatchRepository(conn)
            await batch_repo.recover_stuck_batches(timeout_minutes=5)

        # Счётчик для периодического recovery
        iteration_count = 0
        recovery_interval = 60  # Каждые 60 итераций (30 минут при 30 сек poll interval)

        while self._running:
            try:
                await self._process_next_batch()

                # Периодически восстанавливаем stuck batch
                iteration_count += 1
                if iteration_count >= recovery_interval:
                    async with self.db_manager.pool.acquire() as conn:
                        batch_repo = AwardBatchRepository(conn)
                        await batch_repo.recover_stuck_batches(timeout_minutes=5)
                    iteration_count = 0

            except asyncio.CancelledError:
                logger.info("Worker цикл остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в worker цикле: {e}", exc_info=True)
                # Пауза после ошибки перед следующей попыткой
                await asyncio.sleep(periodic_award_config.WORKER_POLL_INTERVAL)

    async def _process_next_batch(self) -> None:
        """
        Обработать следующий batch.

        Сначала ищем processing batch (для recovery),
        затем pending batch.
        """
        async with self.db_manager.pool.acquire() as conn:
            batch_repo = AwardBatchRepository(conn)

            # Сначала ищем processing batch (recovery после падения)
            batch = await batch_repo.get_next_processing_batch()

            # Если нет processing, ищем pending
            if not batch:
                batch = await batch_repo.get_next_pending_batch()

            if not batch:
                # Нет batch для обработки
                await asyncio.sleep(periodic_award_config.WORKER_POLL_INTERVAL)
                return

            # Помечаем pending batch как processing
            if batch.status == "pending":
                await batch_repo.mark_processing(batch.id)
                logger.info(f"Начата обработка batch {batch.id} для чата {batch.chat_id}, период {batch.period_key}")

            # Обрабатываем пользователей
            await self._process_batch(batch, conn)

    async def _process_batch(
        self,
        batch,  # AwardBatch
        conn: asyncpg.Connection,
    ) -> None:
        """
        Обработать batch пользователей.

        Args:
            batch: Batch для обработки
            conn: Подключение к БД
        """
        batch_repo = AwardBatchRepository(conn)
        settings_repo = ChatSettingsRepository(conn)
        rating_repo = DbRatingRepository(conn)
        ledger_repo = DbRatingLedgerRepository(conn)

        # Получаем пользователей для обработки
        user_ids = await batch_repo.get_users_for_batch(
            batch=batch,
            limit=periodic_award_config.BATCH_SIZE,
        )

        if not user_ids:
            # Все пользователи обработаны
            await batch_repo.mark_done(batch.id)
            logger.info(f"Batch {batch.id} завершён: все пользователи обработаны")
            return

        # Получаем настройки чата для определения суммы
        db_settings = await settings_repo.get_or_create_settings(batch.chat_id)
        amount = db_settings.periodic_award_amount if db_settings.periodic_award_amount is not None else periodic_award_config.DEFAULT_AMOUNT

        logger.debug(
            f"Обработка {len(user_ids)} пользователей в batch {batch.id} "
            f"(чат {batch.chat_id}, сумма {amount})"
        )

        # Обрабатываем каждого пользователя
        last_user_id = None
        for user_id in user_ids:
            await self._award_to_user(
                conn=conn,
                chat_id=batch.chat_id,
                user_id=user_id,
                amount=amount,
                period_key=batch.period_key,
                rating_repo=rating_repo,
                ledger_repo=ledger_repo,
            )

            last_user_id = user_id

            # Небольшая пауза чтобы не перегружать БД
            await asyncio.sleep(0.01)

        # Обновляем cursor
        if last_user_id:
            await batch_repo.update_cursor(batch.id, last_user_id)
            logger.debug(f"Batch {batch.id}: обновлён cursor до пользователя {last_user_id}")

    async def _award_to_user(
        self,
        *,
        conn: asyncpg.Connection,
        chat_id: int,
        user_id: int,
        amount: int,
        period_key: str,
        rating_repo: DbRatingRepository,
        ledger_repo: DbRatingLedgerRepository,
    ) -> bool:
        """
        Зачислить пользователю в рамках batch.

        Idempotency обеспечивается Ledger:
        - UNIQUE(user_id, operation_type, operation_key)
        - operation_key = period_key

        Args:
            conn: Подключение к БД
            chat_id: ID чата
            user_id: ID пользователя
            amount: Сумма зачисления
            period_key: Ключ периода ("2026-W09")
            rating_repo: Репозиторий рейтинга
            ledger_repo: Ledger репозиторий

        Returns:
            True если зачисление успешно, False если уже было
        """
        try:
            # Пробуем создать запись в Ledger
            # Если уже есть — будет конфликт и запись не создастся
            # Partial UNIQUE индекс: uq_rating_ledger_periodic_award
            #   ON (chat_id, user_id, operation_key) WHERE operation_type='award' AND operation_subtype='periodic_award'
            # Для partial unique index нужно использовать ON CONFLICT (columns) WHERE predicate
            query = """
                INSERT INTO rating_ledger
                    (chat_id, user_id, initiator_user_id, counterparty_user_id,
                     amount, balance_after, operation_type, operation_subtype,
                     source_type, source_id, meta, operation_key, created_at)
                VALUES ($1, $2, NULL, NULL, $3, NULL, 'award', 'periodic_award',
                        'system', NULL, $4, $5, NOW())
                ON CONFLICT (chat_id, user_id, operation_key)
                WHERE operation_type = 'award' AND operation_subtype = 'periodic_award'
                DO NOTHING
                RETURNING id
            """
            record = await conn.fetchrow(
                query,
                chat_id,
                user_id,
                amount,
                '{"reason": "periodic_award"}',
                period_key,
            )

            if not record:
                # Уже было зачисление в этом периоде
                logger.debug(f"Пользователь {user_id} уже получил зачисление за период {period_key}")
                return True

            # Обновляем рейтинг
            new_balance = await rating_repo.add(
                chat_id=chat_id,
                user_id=user_id,
                value=amount,
            )

            # Обновляем balance_after в ledger
            await conn.execute(
                """
                UPDATE rating_ledger
                SET balance_after = $1
                WHERE user_id = $2 AND operation_key = $3
                """,
                new_balance,
                user_id,
                period_key,
            )

            logger.debug(
                f"Зачислено {amount} очков пользователю {user_id} "
                f"в чате {chat_id} (баланс: {new_balance}, период: {period_key})"
            )

            return True

        except Exception as e:
            logger.error(
                f"Ошибка зачисления пользователю {user_id} в чате {chat_id}: {e}",
                exc_info=True,
            )
            return False
