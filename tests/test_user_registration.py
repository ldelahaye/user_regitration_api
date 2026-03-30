"""Tests for POST /users — user registration endpoint."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_user_service
from app.core.exceptions import UserAlreadyExistsError
from app.domain.models import User
from app.domain.services import UserService
from app.main import app


@pytest.fixture
async def mock_user_service() -> AsyncIterator[AsyncMock]:
    service = AsyncMock(spec=UserService)
    service.register.return_value = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed",  # noqa: S106
        is_active=False,
        lang="fr",
        created_at=datetime.now(tz=UTC),
    )
    app.dependency_overrides[get_user_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_user_service, None)


async def test_register_user_returns_201(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post(
        "/users", json={"email": "test@example.com", "password": "securepassword123", "lang": "fr"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["is_active"] is False
    assert body["lang"] == "fr"
    assert "id" in body
    assert "created_at" in body
    mock_user_service.register.assert_called_once_with("test@example.com", "securepassword123", "fr")


async def test_register_user_duplicate_email_returns_409(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    mock_user_service.register.side_effect = UserAlreadyExistsError

    response = await client.post(
        "/users", json={"email": "taken@example.com", "password": "securepassword123", "lang": "en"}
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "USER_ALREADY_EXISTS"


async def test_register_user_invalid_email_returns_422(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post(
        "/users", json={"email": "not-an-email", "password": "securepassword123", "lang": "fr"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"


async def test_register_user_short_password_returns_422(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post("/users", json={"email": "test@example.com", "password": "short", "lang": "fr"})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"


async def test_register_user_missing_fields_returns_422(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post("/users", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"


async def test_register_user_invalid_lang_returns_422(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post(
        "/users", json={"email": "test@example.com", "password": "securepassword123", "lang": "ja"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
