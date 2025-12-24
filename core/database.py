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


# Global database manager instance
db_manager = DatabaseManager()
