#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""
Скрипт для разовых зачислений (award) пользователям в чатах.

Использование:
    uv run python scripts/award_one_time.py --chat-id <tg_chat_id> --user-id <tg_user_id> --amount <сумма> --comment "Баг-баунти"

Примеры:
    # Зачислить 500 очков пользователю за баг-баунти
    uv run python scripts/award_one_time.py --chat-id -1001234567890 --user-id 123456789 --amount 500 --comment "Баг-баунти за уязвимость"

    # Зачислить 100 очков за участие в ивенте
    uv run python scripts/award_one_time.py --chat-id -1001234567890 --user-id 123456789 --amount 100 --comment "Ивент 2026-03-01"

    # Массовое зачисление из JSON файла
    uv run python scripts/award_one_time.py --bulk awards.json
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from core.application.rating_ledger.rating_ledger_service import RatingLedgerService
from core.infrastructure.database import DatabaseManager
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository

# Добавляем корень проекта в path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def award_one_time(
    chat_id: int,
    user_id: int,
    amount: int,
    comment: str,
    conn,
) -> bool:
    """
    Зачислить очки пользователю разово.

    Args:
        chat_id: Telegram ID чата
        user_id: Telegram ID пользователя
        amount: Сумма зачисления
        comment: Комментарий к зачислению
        conn: Подключение к БД

    Returns:
        True если успешно
    """
    try:
        # Получаем внутренний ID чата
        chat_record = await conn.fetchrow(
            "SELECT id FROM chats WHERE tg_id = $1",
            chat_id,
        )
        if not chat_record:
            logger.error(f"Чат {chat_id} не найден в БД")
            return False

        internal_chat_id = chat_record["id"]

        # Получаем или создаём пользователя
        user_record = await conn.fetchrow(
            """
            INSERT INTO users (tg_id, username, is_active)
            VALUES ($1, $2, true)
            ON CONFLICT (tg_id) DO UPDATE SET is_active = true
            RETURNING id
            """,
            user_id,
            None,  # username можно добавить позже
        )
        internal_user_id = user_record["id"]

        # Получаем или создаём запись chat_user
        await conn.execute(
            """
            INSERT INTO chat_users (chat_id, user_id, is_active)
            VALUES ($1, $2, true)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET is_active = true
            """,
            internal_chat_id,
            internal_user_id,
        )

        # Зачисляем очки
        rating_repo = DbRatingRepository(conn)
        new_balance = await rating_repo.add(
            chat_id=internal_chat_id,
            user_id=internal_user_id,
            value=amount,
        )

        # Создаём запись в ledger
        ledger_repo = DbRatingLedgerRepository(conn)
        rating_service = RatingLedgerService(ledger_repo)

        await rating_service.record_one_time_award(
            chat_id=internal_chat_id,
            user_id=internal_user_id,
            amount=amount,
            balance_after=new_balance,
            comment=comment,
        )

        logger.info(
            f"✅ Зачислено {amount} очков пользователю {user_id} в чате {chat_id} "
            f"(баланс: {new_balance}, комментарий: {comment})"
        )
        return True

    except Exception as e:
        logger.error(f"Ошибка при зачислении: {e}", exc_info=True)
        return False


async def bulk_award(file_path: str, conn) -> None:
    """
    Массовое зачисление из JSON файла.

    Формат JSON:
    [
        {"chat_id": -1001234567890, "user_id": 123456789, "amount": 500, "comment": "Баг-баунти"},
        {"chat_id": -1001234567890, "user_id": 987654321, "amount": 100, "comment": "Ивент"}
    ]
    """
    with open(file_path) as f:
        awards = json.load(f)

    logger.info(f"Массовое зачисление: {len(awards)} записей")

    successful = 0
    failed = 0

    for award in awards:
        chat_id = award.get("chat_id")
        user_id = award.get("user_id")
        amount = award.get("amount", 50)
        comment = award.get("comment", "one_time_award")

        if not chat_id or not user_id:
            logger.warning(f"Пропущена запись: {award}")
            failed += 1
            continue

        success = await award_one_time(chat_id, user_id, amount, comment, conn)
        if success:
            successful += 1
        else:
            failed += 1

    logger.info(f"Готово: успешно {successful}, ошибок {failed}")


async def main():
    parser = argparse.ArgumentParser(
        description="Разовые зачисления пользователям (баг-баунти, ивенты)"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--chat-id",
        type=int,
        help="Telegram ID чата",
    )
    group.add_argument(
        "--bulk",
        type=str,
        help="Путь к JSON файлу с массовыми зачислениями",
    )

    parser.add_argument(
        "--user-id",
        type=int,
        help="Telegram ID пользователя (для одиночного зачисления)",
    )
    parser.add_argument(
        "--amount",
        type=int,
        default=50,
        help="Сумма зачисления (по умолчанию: 50)",
    )
    parser.add_argument(
        "--comment",
        type=str,
        default="one_time_award",
        help="Комментарий к зачислению (по умолчанию: one_time_award)",
    )

    args = parser.parse_args()

    # Инициализация БД
    db_manager = DatabaseManager()
    await db_manager.init_pool()

    try:
        async with db_manager.pool.acquire() as conn:
            if args.bulk:
                # Массовое зачисление
                await bulk_award(args.bulk, conn)
            else:
                # Одиночное зачисление
                if not args.user_id:
                    logger.error("Для одиночного зачисления нужен --user-id")
                    sys.exit(1)

                success = await award_one_time(
                    chat_id=args.chat_id,
                    user_id=args.user_id,
                    amount=args.amount,
                    comment=args.comment,
                    conn=conn,
                )
                sys.exit(0 if success else 1)

    finally:
        await db_manager.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
