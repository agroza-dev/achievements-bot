"""Fixtures для интеграционных тестов с PostgreSQL через testcontainers.

Поддерживает два режима:
1. Testcontainers (по умолчанию) — изолированный PostgreSQL в Docker
2. Локальная БД (TEST_DB_URL env var) — для быстрой разработки
"""

import os
from collections.abc import AsyncGenerator, Generator
from urllib.parse import urlparse

import pytest
from testcontainers.postgres import PostgresContainer

from core.config import Settings
from core.infrastructure.database import DatabaseManager
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.user_repository import UserRepository


def _is_local_db_mode() -> bool:
    """Проверить используется ли локальная БД вместо testcontainers."""
    return "TEST_DB_URL" in os.environ


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """
    Создать PostgreSQL контейнер для тестов.

    Контейнер запускается один раз на всю сессию тестов.
    Не используется если задан TEST_DB_URL.
    """
    if _is_local_db_mode():
        pytest.skip("Using local database, skipping testcontainers")

    with PostgresContainer("postgres:15", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def test_db_url(postgres_container: PostgresContainer) -> str:
    """
    Получить URL базы данных для тестов.
    """
    if _is_local_db_mode():
        return os.environ["TEST_DB_URL"]
    else:
        host = postgres_container.get_container_host_ip()
        port = int(postgres_container.get_exposed_port(5432))
        user = postgres_container.username
        password = postgres_container.password
        dbname = postgres_container.dbname
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


@pytest.fixture(scope="session")
def test_settings(test_db_url: str) -> Settings:
    """
    Создать настройки для тестов с использованием тестового PostgreSQL.
    """
    settings = Settings()

    # Парсим TEST_DB_URL (убираем +asyncpg если есть)
    url = urlparse(test_db_url.replace("+asyncpg", ""))
    settings.db.host = url.hostname or "localhost"
    settings.db.port = url.port or 5432
    settings.db.login = url.username or ""
    settings.db.password = url.password or ""
    settings.db.name = url.path.lstrip("/") or "test"

    return settings


@pytest.fixture(scope="session")
def applied_db(test_settings: Settings) -> Settings:
    """
    Применить миграции к тестовой БД.

    Этот fixture зависит от test_settings и гарантирует что миграции
    применены перед использованием.
    """
    from tests.apply_migrations import apply_migrations

    db_url = (
        f"postgresql://{test_settings.db.login}:{test_settings.db.password}"
        f"@{test_settings.db.host}:{test_settings.db.port}/{test_settings.db.name}"
    )
    apply_migrations(db_url)

    return test_settings


@pytest.fixture
async def db_manager(applied_db: Settings) -> AsyncGenerator[DatabaseManager]:
    """
    Создать DatabaseManager с тестовым PostgreSQL.

    Инициализирует пул подключений. Миграции уже применены в applied_db.
    """
    manager = DatabaseManager()

    # Временно подменяем settings для manager
    original_settings = manager.settings
    manager.settings = applied_db

    try:
        await manager.init_pool()
        yield manager

    finally:
        await manager.close_pool()
        manager.settings = original_settings


@pytest.fixture
async def db_connection(db_manager: DatabaseManager) -> AsyncGenerator:
    """
    Получить подключение из пула для тестов.
    """
    async with db_manager.get_connection() as conn:
        yield conn


@pytest.fixture
def user_repo(db_connection):
    """Создать UserRepository с тестовым подключением."""
    return UserRepository(db_connection)


@pytest.fixture
def chat_repo(db_connection):
    """Создать ChatRepository с тестовым подключением."""
    return ChatRepository(db_connection)


@pytest.fixture
def rating_ledger_repo(db_connection):
    """Создать DbRatingLedgerRepository с тестовым подключением."""
    return DbRatingLedgerRepository(db_connection)
