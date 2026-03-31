"""Integration tests — activation code transactional behavior."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import asyncpg
import pytest
from httpx import AsyncClient

from app.api.dependencies import get_email_service
from app.core.exceptions import NotificationError
from app.domain.ports import EmailService
from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def _failing_email_service() -> Iterator[None]:
    """Override email service with one that always fails."""
    mock_service = AsyncMock(spec=EmailService)
    mock_service.send_activation_code.side_effect = NotificationError
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


async def test_register_should_rollback_when_email_fails(
    async_client: AsyncClient,
    _failing_email_service: None,
) -> None:
    """Registration returns 502 and rolls back when email send fails."""
    register_resp = await async_client.post(
        "/users",
        json={"email": "resilient@example.com", "password": "securepassword123", "lang": "fr"},
    )
    assert register_resp.status_code == 502
    assert register_resp.json()["error_code"] == "NOTIFICATION_FAILED"

    # Verify user was NOT created (transaction rolled back)
    pool: asyncpg.Pool = app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", "resilient@example.com")
    assert row is None


async def test_rerequest_returns_201_even_when_email_fails(
    async_client: AsyncClient,
    _failing_email_service: None,
) -> None:
    """Re-request endpoint returns 201 even on email failure (OWASP enumeration prevention).

    Note: register also fails with 502, so we first create a user with
    a success service, then swap to the failing one for the re-request.
    """
    # Register user with working email first
    success_service = AsyncMock(spec=EmailService)
    app.dependency_overrides[get_email_service] = lambda: success_service
    register_resp = await async_client.post(
        "/users",
        json={"email": "rollback@example.com", "password": "securepassword123", "lang": "fr"},
    )
    assert register_resp.status_code == 201

    # Switch to failing email service
    fail_service = AsyncMock(spec=EmailService)
    fail_service.send_activation_code.side_effect = NotificationError
    app.dependency_overrides[get_email_service] = lambda: fail_service

    # Re-request activation code — email fails, but 201 is returned (OWASP)
    code_resp = await async_client.post(
        "/users/activation-code",
        json={"email": "rollback@example.com"},
    )
    assert code_resp.status_code == 201


async def test_activation_code_committed_on_email_success(
    async_client: AsyncClient,
    _success_email_service: None,
) -> None:
    register_resp = await async_client.post(
        "/users",
        json={"email": "commit@example.com", "password": "securepassword123", "lang": "fr"},
    )
    assert register_resp.status_code == 201

    code_resp = await async_client.post(
        "/users/activation-code",
        json={"email": "commit@example.com"},
    )
    assert code_resp.status_code == 201

    # Verify activation code was persisted (at least 2: one from register, one from re-request)
    user_id = register_resp.json()["id"]
    pool: asyncpg.Pool = app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT count(*) AS cnt FROM activation_codes WHERE user_id = $1::uuid", user_id)
    assert row is not None
    assert row["cnt"] >= 2
