"""asyncpg connection pool management."""

import logging

import asyncpg

logger = logging.getLogger(__name__)


async def init_pool(
    database_url: str,
    *,
    min_size: int = 2,
    max_size: int = 10,
    timeout: float = 30.0,
    command_timeout: float = 60.0,
) -> asyncpg.Pool:
    """Create the asyncpg connection pool and verify connectivity."""
    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        command_timeout=command_timeout,
    )
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")
    logger.info("Database connection pool initialized")
    return pool


async def close_pool(pool: asyncpg.Pool) -> None:
    """Close all pool connections."""
    await pool.close()
    logger.info("Database connection pool closed")
