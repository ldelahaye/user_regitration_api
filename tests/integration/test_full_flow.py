"""End-to-end integration test — full registration flow.

Covers: register (auto-sends code) → activate with Basic Auth.
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
from httpx import AsyncClient

from app.api.dependencies import get_email_service
from app.core.config import settings
from app.domain.ports import EmailService
from app.main import app
from tests.helpers import basic_auth_header as _basic_auth_header

pytestmark = pytest.mark.integration

_PASSWORD = "Securepassword123!"


@pytest.fixture
def _capturing_email_service() -> Iterator[dict[str, str]]:
    """Override email service with one that captures the activation code."""
    captured: dict[str, str] = {}

    async def capture_code(email: str, code: str, validity_minutes: int, lang: str) -> None:
        captured["code"] = code

    mock_service = AsyncMock(spec=EmailService)
    mock_service.send_activation_code.side_effect = capture_code
    app.dependency_overrides[get_email_service] = lambda: mock_service
    yield captured
    app.dependency_overrides.pop(get_email_service, None)


async def test_register_activate_should_activate_user_when_valid_code(
    async_client: AsyncClient,
    _capturing_email_service: dict[str, str],
) -> None:
    """Register (auto-sends code) → activate with Basic Auth."""
    captured = _capturing_email_service
    email = "fullflow-register@example.com"

    # Step 1: Register user (auto-sends activation code)
    register_resp = await async_client.post(
        "/users",
        json={"email": email, "password": _PASSWORD, "lang": "fr"},
    )
    assert register_resp.status_code == 201
    assert "code" in captured

    # Step 2: Activate account with Basic Auth + captured code
    activate_resp = await async_client.post(
        "/users/activate",
        json={"code": captured["code"]},
        headers=_basic_auth_header(email, _PASSWORD),
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["detail"] == "Account activated successfully"

    # Verify user is active in database
    pool: asyncpg.Pool = app.state.db_pool
    async with pool.acquire() as conn:
        user_id = register_resp.json()["id"]
        row = await conn.fetchrow("SELECT is_active FROM users WHERE id = $1::uuid", user_id)
    assert row is not None
    assert row["is_active"] is True


async def test_register_activate_get_me_returns_user_data(
    async_client: AsyncClient,
    _capturing_email_service: dict[str, str],
) -> None:
    """Register → GET /users/me (403 inactive) → activate → GET /users/me (200)."""
    captured = _capturing_email_service
    email = "meflow@example.com"

    # Step 1: Register
    register_resp = await async_client.post(
        "/users",
        json={"email": email, "password": _PASSWORD, "lang": "fr"},
    )
    assert register_resp.status_code == 201

    # Step 2: GET /users/me before activation → 403
    me_resp = await async_client.get("/users/me", headers=_basic_auth_header(email, _PASSWORD))
    assert me_resp.status_code == 403
    assert me_resp.json()["error_code"] == "INACTIVE_USER"

    # Step 3: Activate
    activate_resp = await async_client.post(
        "/users/activate",
        json={"code": captured["code"]},
        headers=_basic_auth_header(email, _PASSWORD),
    )
    assert activate_resp.status_code == 200

    # Step 4: GET /users/me after activation → 200
    me_resp = await async_client.get("/users/me", headers=_basic_auth_header(email, _PASSWORD))
    assert me_resp.status_code == 200
    body = me_resp.json()
    assert body["email"] == email
    assert body["is_active"] is True
    assert body["lang"] == "fr"
    assert body["id"] == register_resp.json()["id"]


async def test_activate_locks_after_max_failed_attempts(
    async_client: AsyncClient,
    _capturing_email_service: dict[str, str],
) -> None:
    """N wrong codes → 429 ACTIVATION_CODE_LOCKED."""
    captured = _capturing_email_service
    email = "lockout@example.com"

    register_resp = await async_client.post(
        "/users",
        json={"email": email, "password": _PASSWORD, "lang": "fr"},
    )
    assert register_resp.status_code == 201

    # Use a code that is guaranteed not to match by checking the captured one.
    valid_code = captured["code"]
    wrong_code = "0000" if valid_code != "0000" else "1111"

    max_attempts = settings.activation_max_attempts
    for _ in range(max_attempts - 1):
        resp = await async_client.post(
            "/users/activate",
            json={"code": wrong_code},
            headers=_basic_auth_header(email, _PASSWORD),
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_ACTIVATION_CODE"

    locked_resp = await async_client.post(
        "/users/activate",
        json={"code": wrong_code},
        headers=_basic_auth_header(email, _PASSWORD),
    )
    assert locked_resp.status_code == 429
    assert locked_resp.json()["error_code"] == "ACTIVATION_CODE_LOCKED"


async def test_health_returns_503_when_db_unreachable(
    async_client: AsyncClient,
) -> None:
    """Health check returns 503 when the database pool is replaced with a broken one."""
    broken_pool = MagicMock()
    broken_pool.acquire.return_value.__aenter__ = AsyncMock(side_effect=OSError("connection refused"))
    broken_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    original_pool = app.state.db_pool
    app.state.db_pool = broken_pool
    try:
        resp = await async_client.get("/health")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Database unreachable"
    finally:
        app.state.db_pool = original_pool


async def test_rerequest_activation_code_and_activate(
    async_client: AsyncClient,
    _capturing_email_service: dict[str, str],
) -> None:
    """Register → re-request code via email → activate with new code."""
    captured = _capturing_email_service
    email = "fullflow-rerequest@example.com"

    # Step 1: Register user (auto-sends code, but we ignore it)
    register_resp = await async_client.post(
        "/users",
        json={"email": email, "password": _PASSWORD, "lang": "fr"},
    )
    assert register_resp.status_code == 201

    # Step 2: Re-request activation code via email
    captured.clear()
    code_resp = await async_client.post(
        "/users/activation-code",
        json={"email": email},
    )
    assert code_resp.status_code == 201
    assert "code" in captured

    # Step 3: Activate with new code
    activate_resp = await async_client.post(
        "/users/activate",
        json={"code": captured["code"]},
        headers=_basic_auth_header(email, _PASSWORD),
    )
    assert activate_resp.status_code == 200
