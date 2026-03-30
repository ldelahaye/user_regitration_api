"""Fixtures for integration tests requiring a real PostgreSQL database."""

import os
from collections.abc import AsyncIterator

import asyncpg
import pytest

from app.infrastructure.database.migrations import SCHEMA_SQL

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
        await conn.execute("DROP TABLE IF EXISTS activation_codes CASCADE")
        await conn.execute("DROP TABLE IF EXISTS users CASCADE")
    await pool.close()


@pytest.fixture
async def db_conn(db_pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:
    async with db_pool.acquire() as conn:
        yield conn
