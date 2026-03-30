"""Tests for POST /users/{user_id}/activation-code — send activation code endpoint."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_user_service
from app.core.exceptions import UserNotFoundError
from app.domain.models import ActivationCode
from app.domain.services import UserService
from app.main import app

_USER_ID = uuid4()


@pytest.fixture
async def mock_user_service() -> AsyncIterator[AsyncMock]:
    service = AsyncMock(spec=UserService)
    service.send_activation_code.return_value = ActivationCode(
        id=uuid4(),
        user_id=_USER_ID,
        code="1234",
        expires_at=datetime.now(tz=UTC),
        used_at=None,
    )
    app.dependency_overrides[get_user_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_user_service, None)


async def test_send_activation_code_returns_201(client: AsyncClient, mock_user_service: AsyncMock) -> None:
    response = await client.post(f"/users/{_USER_ID}/activation-code")

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(_USER_ID)
    assert "id" in body
    assert "expires_at" in body
    mock_user_service.send_activation_code.assert_called_once_with(_USER_ID)


async def test_send_activation_code_user_not_found_returns_404(
    client: AsyncClient, mock_user_service: AsyncMock
) -> None:
    mock_user_service.send_activation_code.side_effect = UserNotFoundError

    response = await client.post(f"/users/{uuid4()}/activation-code")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "USER_NOT_FOUND"
