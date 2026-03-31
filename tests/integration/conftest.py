"""Fixtures for integration tests requiring a real PostgreSQL database."""

import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.ports import EmailService
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
        tr = conn.transaction()
        await tr.start()
        yield conn
        await tr.rollback()


@pytest.fixture
async def _setup_db(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """Wire the shared pool into app.state and clean up after each test."""
    app.state.db_pool = db_pool
    yield
    del app.state.db_pool


@pytest.fixture
async def async_client(_setup_db: None) -> AsyncIterator[AsyncClient]:
    """HTTP client wired to the app with a real database and a mock email service."""
    app.state.email_service = AsyncMock(spec=EmailService)
    transport = ASGITransport(app=app)
    with patch("app.main.load_templates"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    del app.state.email_service
