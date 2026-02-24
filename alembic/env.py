import os
import sys
from logging.config import fileConfig
from urllib.parse import quote

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context
from core.config import settings

# Load environment variables
load_dotenv()

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Construct the database URL from settings

encoded_password = quote(settings.db.password, safe='')
database_url = f"postgresql://{settings.db.login}:{encoded_password}@{settings.db.host}:{settings.db.port}/{settings.db.name}"

# Set the sqlalchemy.url in the config
config.set_main_option('sqlalchemy.url', database_url.replace('%', '%%'))

# Add your model's MetaData object here for 'autogenerate' support
# This will be updated when we create the models
from core.models import (  # noqa: E402, F401
    bot_persistence_model,
    chat_message_model,
    chat_model,
    chat_user_model,
    rating_ledger,
    reaction_model,
    user_model,
)
from core.models.metadata import metadata  # noqa: E402

target_metadata = metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def process_revision_directives(context, revision, directives):
    if context.config.cmd_opts.autogenerate:
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print("No changes in schema detected.")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
