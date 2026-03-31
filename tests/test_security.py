"""Unit tests for UserService.authenticate and _hash_code — timing-safe auth and code hashing."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import bcrypt
import pytest

from app.domain.exceptions import UserNotFoundError
from app.domain.models import AuthenticatedUser, User
from app.domain.services import UserService
from app.infrastructure.database.repositories import _hash_code

_PASSWORD = "correctpassword"
_PASSWORD_HASH = bcrypt.hashpw(_PASSWORD.encode(), bcrypt.gensalt()).decode()

_USER = User(
    id=uuid4(),
    email="user@example.com",
    password_hash=_PASSWORD_HASH,
    is_active=True,
    lang="fr",
    created_at=datetime.now(tz=UTC),
)


@pytest.fixture
def user_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_email.return_value = _USER
    return repo


@pytest.fixture
def service(user_repository: AsyncMock) -> UserService:
    return UserService(user_repository, AsyncMock(), AsyncMock())


async def test_authenticate_valid_returns_authenticated_user(service: UserService) -> None:
    result = await service.authenticate(_USER.email, _PASSWORD)

    assert isinstance(result, AuthenticatedUser)
    assert result.id == _USER.id
    assert result.email == _USER.email
    assert result.is_active == _USER.is_active
    assert not hasattr(result, "password_hash")


async def test_authenticate_wrong_password_raises(service: UserService) -> None:
    with pytest.raises(UserNotFoundError):
        await service.authenticate(_USER.email, "wrongpassword")


async def test_authenticate_unknown_email_raises(user_repository: AsyncMock) -> None:
    user_repository.get_by_email.return_value = None
    svc = UserService(user_repository, AsyncMock(), AsyncMock())

    with pytest.raises(UserNotFoundError):
        await svc.authenticate("ghost@example.com", "any")


async def test_authenticate_unknown_email_still_runs_bcrypt() -> None:
    """Timing-safe: bcrypt must be called even when the user doesn't exist."""
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    svc = UserService(repo, AsyncMock(), AsyncMock())

    with (
        patch("app.domain.services.bcrypt.checkpw", return_value=False) as mock_checkpw,
        pytest.raises(UserNotFoundError),
    ):
        await svc.authenticate("ghost@example.com", "any")

    mock_checkpw.assert_called_once()


# --- _hash_code ---

_SECRET = "test-hmac-secret"


def test_hash_code_is_deterministic() -> None:
    user_id = uuid4()
    assert _hash_code(_SECRET, user_id, "1234") == _hash_code(_SECRET, user_id, "1234")


def test_hash_code_differs_for_different_codes() -> None:
    user_id = uuid4()
    assert _hash_code(_SECRET, user_id, "1234") != _hash_code(_SECRET, user_id, "5678")


def test_hash_code_differs_for_different_users() -> None:
    code = "1234"
    assert _hash_code(_SECRET, uuid4(), code) != _hash_code(_SECRET, uuid4(), code)


def test_hash_code_differs_for_different_secrets() -> None:
    user_id = uuid4()
    assert _hash_code("secret-a", user_id, "1234") != _hash_code("secret-b", user_id, "1234")


def test_hash_code_returns_hex_string() -> None:
    result = _hash_code(_SECRET, uuid4(), "0000")
    assert len(result) == 64  # SHA-256 hex digest
    assert all(c in "0123456789abcdef" for c in result)
