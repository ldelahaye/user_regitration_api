"""Tests for GET /users/me — authenticated active user info endpoint."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.api.dependencies import get_active_user, get_authenticated_user
from app.domain.exceptions import InactiveUserError
from app.domain.models import AuthenticatedUser
from app.main import app
from tests.helpers import basic_auth_header as _basic_auth_header

_USER = AuthenticatedUser(
    id=uuid4(),
    email="me@example.com",
    is_active=True,
    lang="fr",
    created_at=datetime.now(tz=UTC),
)


@pytest.fixture
async def _active_user() -> AsyncIterator[None]:
    app.dependency_overrides[get_active_user] = lambda: _USER
    yield
    app.dependency_overrides.pop(get_active_user, None)


@pytest.fixture
async def _inactive_user() -> AsyncIterator[None]:
    async def _raise() -> AuthenticatedUser:
        raise InactiveUserError

    app.dependency_overrides[get_active_user] = _raise
    yield
    app.dependency_overrides.pop(get_active_user, None)


@pytest.fixture
async def _invalid_credentials() -> AsyncIterator[None]:
    async def _raise() -> AuthenticatedUser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    app.dependency_overrides[get_authenticated_user] = _raise
    yield
    app.dependency_overrides.pop(get_authenticated_user, None)


# --- Success ---


async def test_get_me_returns_200_with_user_data(client: AsyncClient, _active_user: None) -> None:
    response = await client.get("/users/me", headers=_basic_auth_header(_USER.email, "password"))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == _USER.email
    assert body["is_active"] is True
    assert body["lang"] == _USER.lang
    assert body["id"] == str(_USER.id)
    assert "created_at" in body
    assert "password_hash" not in body


# --- Auth errors ---


async def test_get_me_returns_401_without_credentials(client: AsyncClient) -> None:
    response = await client.get("/users/me")

    assert response.status_code == 401


async def test_get_me_returns_401_with_invalid_credentials(client: AsyncClient, _invalid_credentials: None) -> None:
    response = await client.get("/users/me", headers=_basic_auth_header("wrong@example.com", "wrong"))

    assert response.status_code == 401


# --- Authorization error ---


async def test_get_me_returns_403_when_user_inactive(client: AsyncClient, _inactive_user: None) -> None:
    response = await client.get("/users/me", headers=_basic_auth_header(_USER.email, "password"))

    assert response.status_code == 403
    body = response.json()
    assert body["detail"] == "Account is not activated"
    assert body["error_code"] == "INACTIVE_USER"
