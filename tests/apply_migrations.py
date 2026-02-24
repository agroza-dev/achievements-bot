"""Apply alembic migrations to a given database URL."""

import sys

from sqlalchemy import engine_from_config, pool


def apply_migrations(db_url: str) -> None:
    """Apply all migrations to the database by creating all tables."""
    # Import model metadata
    from core.models import (  # noqa: F401
        chat_message_model,
        chat_model,
        chat_user_model,
        rating_ledger,
        reaction_model,
        user_model,
    )
    from core.models.metadata import metadata

    # Создаём sync engine
    sync_url = db_url.replace("+asyncpg", "postgresql://")

    engine = engine_from_config(
        {"sqlalchemy.url": sync_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Создаём все таблицы
    metadata.create_all(engine)
    engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m tests.apply_migrations <database_url>")
        sys.exit(1)

    db_url = sys.argv[1]
    apply_migrations(db_url)
    print("Migrations applied successfully")
