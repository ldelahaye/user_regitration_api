"""Fixtures for integration tests requiring a real PostgreSQL database."""

import os
from collections.abc import AsyncIterator

import asyncpg
import pytest

from app.infrastructure.database.migrations import SCHEMA_SQL
from app.main import app

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/registration_test",
)


@pytest.fixture
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    pool = await asyncpg.create_pool(dsn=DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    yield pool
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE activation_codes, users CASCADE")
    await pool.close()


@pytest.fixture
async def db_conn(db_pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:
    async with db_pool.acquire() as conn:
        yield conn


@pytest.fixture
async def _setup_db() -> AsyncIterator[None]:
    """Apply schema before tests, clean up after."""
    pool = await asyncpg.create_pool(dsn=DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    app.state.db_pool = pool
    yield
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE activation_codes, users CASCADE")
    await pool.close()
