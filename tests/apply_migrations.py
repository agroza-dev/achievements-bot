"""Apply alembic migrations to a given database URL."""

import sys
from alembic import command
from alembic.config import Config
from sqlalchemy import engine_from_config, pool


def apply_migrations(db_url: str) -> None:
    """Apply all migrations to the database using Alembic."""
    # Создаём sync engine
    sync_url = db_url.replace("+asyncpg", "postgresql://")

    # Инициализируем Alembic config
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    # Важно: transaction_per_migration=False чтобы все миграции были в одной транзакции
    alembic_cfg.set_main_option("transaction_per_migration", "false")

    # Применяем все миграции
    print(f"Applying migrations to {sync_url}")
    command.upgrade(alembic_cfg, "head")
    print("Migrations applied successfully")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m tests.apply_migrations <database_url>")
        sys.exit(1)

    db_url = sys.argv[1]
    apply_migrations(db_url)
