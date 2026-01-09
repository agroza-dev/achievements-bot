import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

from core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.pool = None
        self.settings = settings

    async def init_pool(self):
        """Initialize the connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.settings.db.host,
                port=self.settings.db.port,
                database=self.settings.db.name,
                user=self.settings.db.login,
                password=self.settings.db.password,
                min_size=self.settings.db.pool_min_size,
                max_size=self.settings.db.pool_max_size,
                command_timeout=60,
            )
            logger.info(f"Database pool initialized with {self.settings.db.pool_min_size}-{self.settings.db.pool_max_size} connections")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def close_pool(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection]:
        """Get a connection from the pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[asyncpg.Connection]:
        """Get a connection with transaction context"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as conn, conn.transaction():
            yield conn

    async def acquire(self) -> asyncpg.Connection:
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        return await self.pool.acquire()

    async def release(self, conn: asyncpg.Connection):
        await self.pool.release(conn)


class DbUnitOfWork:
    def __init__(self, pool: asyncpg.Pool):
        if not isinstance(pool, asyncpg.Pool):
            raise TypeError(
                f"DbUnitOfWork expects asyncpg.Pool, got {type(pool)!r}"
            )

        self.pool = pool
        self.conn = None
        self._repos = {}

    async def __aenter__(self):
        self.conn = await self.pool.acquire()
        self.tx = self.conn.transaction()
        await self.tx.start()
        return self

    def get_repo(self, repo_cls):
        """
        Ленивая инициализация репозиториев.
        Позволяет use case самому решать,
        какие репозитории участвуют в транзакции.
        """
        if repo_cls not in self._repos:
            self._repos[repo_cls] = repo_cls(self.conn)
        return self._repos[repo_cls]

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                await self.tx.rollback()
            else:
                await self.tx.commit()
        finally:
            await self.pool.release(self.conn)



db_manager = DatabaseManager()
