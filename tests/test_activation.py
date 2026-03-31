"""Tests for POST /users/activate — account activation with Basic Auth."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_authenticated_user, get_user_service
from app.core.exceptions import (
    ActivationCodeExpiredError,
    ActivationCodeLockedError,
    InvalidActivationCodeError,
    UserAlreadyActiveError,
)
from app.domain.models import AuthenticatedUser
from app.domain.services import UserService
from app.main import app
from tests.helpers import basic_auth_header as _basic_auth_header

_USER = AuthenticatedUser(
    id=uuid4(),
    email="activate@example.com",
    is_active=False,
    lang="fr",
    created_at=datetime.now(tz=UTC),
)


@pytest.fixture
async def mock_user_service() -> AsyncIterator[AsyncMock]:
    service = AsyncMock(spec=UserService)
    app.dependency_overrides[get_user_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_user_service, None)


@pytest.fixture
async def mock_authenticated_user() -> AsyncIterator[None]:
    app.dependency_overrides[get_authenticated_user] = lambda: _USER
    yield
    app.dependency_overrides.pop(get_authenticated_user, None)


async def test_activate_user_returns_200(
    client: AsyncClient, mock_user_service: AsyncMock, mock_authenticated_user: None
) -> None:
    response = await client.post(
        "/users/activate",
        json={"code": "1234"},
        headers=_basic_auth_header("activate@example.com", "password123"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["detail"] == "Account activated successfully"
    mock_user_service.activate_user.assert_called_once_with(_USER, "1234")


async def test_activate_user_expired_code_returns_400(
    client: AsyncClient, mock_user_service: AsyncMock, mock_authenticated_user: None
) -> None:
    mock_user_service.activate_user.side_effect = ActivationCodeExpiredError

    response = await client.post(
        "/users/activate",
        json={"code": "1234"},
        headers=_basic_auth_header("activate@example.com", "password123"),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "ACTIVATION_CODE_EXPIRED"


async def test_activate_user_wrong_code_returns_400(
    client: AsyncClient, mock_user_service: AsyncMock, mock_authenticated_user: None
) -> None:
    mock_user_service.activate_user.side_effect = InvalidActivationCodeError

    response = await client.post(
        "/users/activate",
        json={"code": "9999"},
        headers=_basic_auth_header("activate@example.com", "password123"),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "INVALID_ACTIVATION_CODE"


async def test_activate_user_invalid_code_format_returns_422(
    client: AsyncClient, mock_user_service: AsyncMock, mock_authenticated_user: None
) -> None:
    response = await client.post(
        "/users/activate",
        json={"code": "abc"},
        headers=_basic_auth_header("activate@example.com", "password123"),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"


async def test_activate_user_already_active_returns_409(
    client: AsyncClient, mock_user_service: AsyncMock, mock_authenticated_user: None
) -> None:
    mock_user_service.activate_user.side_effect = UserAlreadyActiveError

    response = await client.post(
        "/users/activate",
        json={"code": "1234"},
        headers=_basic_auth_header("activate@example.com", "password123"),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "USER_ALREADY_ACTIVE"


async def test_activate_user_locked_returns_429(
    client: AsyncClient, mock_user_service: AsyncMock, mock_authenticated_user: None
) -> None:
    mock_user_service.activate_user.side_effect = ActivationCodeLockedError

    response = await client.post(
        "/users/activate",
        json={"code": "1234"},
        headers=_basic_auth_header("activate@example.com", "password123"),
    )

    assert response.status_code == 429
    assert response.json()["error_code"] == "ACTIVATION_CODE_LOCKED"


async def test_activate_user_no_credentials_returns_401(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post("/users/activate", json={"code": "1234"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"
