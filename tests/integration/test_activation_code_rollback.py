"""Integration test — activation code is rolled back when email send fails."""

import os
from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_email_service
from app.core.exceptions import EmailSendError
from app.domain.ports import EmailService
from app.infrastructure.database.migrations import SCHEMA_SQL
from app.main import app

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/registration_test",
)


@pytest.fixture
async def _setup_db() -> AsyncIterator[None]:
    """Apply schema before tests, clean up after."""
    pool = await asyncpg.create_pool(dsn=DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    app.state.db_pool = pool
    yield
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM activation_codes")
        await conn.execute("DELETE FROM users")
    await pool.close()


@pytest.fixture
def _failing_email_service() -> Iterator[None]:
    """Override email service with one that always fails."""
    mock_service = AsyncMock(spec=EmailService)
    mock_service.send_activation_code.side_effect = EmailSendError
    app.dependency_overrides[get_email_service] = lambda: mock_service
    yield
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def _success_email_service() -> Iterator[None]:
    """Override email service with one that always succeeds."""
    mock_service = AsyncMock(spec=EmailService)
    app.dependency_overrides[get_email_service] = lambda: mock_service
    yield
    app.dependency_overrides.pop(get_email_service, None)


async def test_activation_code_rolled_back_on_email_failure(
    _setup_db: None,
    _failing_email_service: None,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a user
        with patch("app.main.load_templates"):
            register_resp = await client.post(
                "/users", json={"email": "rollback@example.com", "password": "securepassword123", "lang": "fr"}
            )
        assert register_resp.status_code == 201
        user_id = register_resp.json()["id"]

        # Attempt to send activation code — email fails
        with patch("app.main.load_templates"):
            code_resp = await client.post(f"/users/{user_id}/activation-code")
        assert code_resp.status_code == 502

    # Verify no activation code was persisted
    pool = app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT count(*) AS cnt FROM activation_codes")
        assert row["cnt"] == 0


async def test_activation_code_committed_on_email_success(
    _setup_db: None,
    _success_email_service: None,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.main.load_templates"):
            register_resp = await client.post(
                "/users", json={"email": "commit@example.com", "password": "securepassword123", "lang": "fr"}
            )
        assert register_resp.status_code == 201
        user_id = register_resp.json()["id"]

        with patch("app.main.load_templates"):
            code_resp = await client.post(f"/users/{user_id}/activation-code")
        assert code_resp.status_code == 201

    # Verify activation code was persisted
    pool = app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT count(*) AS cnt FROM activation_codes")
        assert row["cnt"] == 1
