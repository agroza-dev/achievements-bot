"""Alembic env.py для тестов — использует переданный URL напрямую."""

import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the project root to the path
sys.path.insert(0, (context.config.config_file_name and
                context.config.config_file_name.split('/')[0]) or '.')

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import model metadata
from core.models import (  # noqa: E402, F401
    chat_message_model,
    chat_model,
    chat_user_model,
    rating_ledger,
    reaction_model,
    user_model,
)
from core.models.metadata import metadata  # noqa: E402

target_metadata = metadata


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
