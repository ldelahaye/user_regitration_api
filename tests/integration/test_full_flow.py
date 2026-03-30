"""End-to-end integration test — full registration flow.

Covers: register → send activation code → activate with Basic Auth.
"""

import base64
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_email_service
from app.domain.ports import EmailService
from app.main import app

pytestmark = pytest.mark.integration

_EMAIL = "fullflow@example.com"
_PASSWORD = "securepassword123"


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


def _basic_auth_header(username: str, password: str) -> dict[str, str]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


async def test_register_activate_should_activate_user_when_valid_code(
    _setup_db: None,
    _capturing_email_service: dict[str, str],
) -> None:
    """Register → send activation code → activate with Basic Auth."""
    captured = _capturing_email_service

    transport = ASGITransport(app=app)
    with patch("app.main.load_templates"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Register user
            register_resp = await client.post(
                "/users",
                json={"email": _EMAIL, "password": _PASSWORD, "lang": "fr"},
            )
            assert register_resp.status_code == 201
            user_id = register_resp.json()["id"]

            # Step 2: Request activation code (captured by mock email service)
            code_resp = await client.post(f"/users/{user_id}/activation-code")
            assert code_resp.status_code == 201
            assert "code" in captured

            # Step 3: Activate account with Basic Auth + captured code
            activate_resp = await client.post(
                "/users/activate",
                json={"code": captured["code"]},
                headers=_basic_auth_header(_EMAIL, _PASSWORD),
            )
            assert activate_resp.status_code == 200
            assert activate_resp.json()["detail"] == "Account activated successfully"

    # Verify user is active in database
    pool: asyncpg.Pool = app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT is_active FROM users WHERE id = $1::uuid", user_id)
    assert row is not None
    assert row["is_active"] is True
