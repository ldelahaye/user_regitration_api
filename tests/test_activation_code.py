"""Tests for POST /users/activation-code — request activation code by email."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_user_service
from app.domain.services import UserService
from app.main import app


@pytest.fixture
async def mock_user_service() -> AsyncIterator[AsyncMock]:
    service = AsyncMock(spec=UserService)
    app.dependency_overrides[get_user_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_user_service, None)


async def test_request_activation_code_returns_201(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post("/users/activation-code", json={"email": "test@example.com"})

    assert response.status_code == 201
    body = response.json()
    assert "detail" in body
    mock_user_service.request_activation_code.assert_called_once_with("test@example.com")


async def test_request_activation_code_unknown_email_returns_201(
    client: AsyncClient, mock_user_service: AsyncMock
) -> None:
    """OWASP: no user enumeration — unknown email gets same response."""
    response = await client.post("/users/activation-code", json={"email": "unknown@example.com"})

    assert response.status_code == 201
    mock_user_service.request_activation_code.assert_called_once_with("unknown@example.com")


async def test_request_activation_code_invalid_email_returns_422(
    client: AsyncClient, mock_user_service: AsyncMock
) -> None:
    response = await client.post("/users/activation-code", json={"email": "not-an-email"})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"


async def test_request_activation_code_missing_email_returns_422(
    client: AsyncClient, mock_user_service: AsyncMock
) -> None:
    response = await client.post("/users/activation-code", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
