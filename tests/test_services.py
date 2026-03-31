"""Unit tests for UserService domain logic."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.exceptions import (
    ActivationCodeExpiredError,
    ActivationCodeLockedError,
    InvalidActivationCodeError,
    NotificationError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    WeakPasswordError,
)
from app.domain.models import ActivationCode, AuthenticatedUser, User
from app.domain.ports import DuplicateEntryError
from app.domain.services import PasswordPolicy, UserService, UserServiceConfig

_USER = User(
    id=uuid4(),
    email="test@example.com",
    password_hash="hashed",  # noqa: S106
    is_active=False,
    lang="fr",
    created_at=datetime.now(tz=UTC),
)

_ACTIVATION_CODE = ActivationCode(
    id=uuid4(),
    user_id=_USER.id,
    code="1234",
    expires_at=datetime.now(tz=UTC),
    used_at=None,
)


@pytest.fixture
def user_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    repo.create.return_value = _USER
    return repo


@pytest.fixture
def activation_code_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.create.return_value = _ACTIVATION_CODE
    repo.record_failed_attempt.return_value = False  # not locked by default
    return repo


@pytest.fixture
def email_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    user_repository: AsyncMock,
    activation_code_repository: AsyncMock,
    email_service: AsyncMock,
) -> UserService:
    return UserService(user_repository, activation_code_repository, email_service)


# --- register() ---


async def test_register_should_raise_when_user_already_exists(
    service: UserService,
    user_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _USER

    with pytest.raises(UserAlreadyExistsError):
        await service.register("test@example.com", "Securepassword123!", "fr")


async def test_register_should_send_activation_code(
    service: UserService,
    activation_code_repository: AsyncMock,
    email_service: AsyncMock,
) -> None:
    user = await service.register("test@example.com", "Securepassword123!", "fr")

    assert user == _USER
    activation_code_repository.create.assert_called_once()
    email_service.send_activation_code.assert_called_once()


async def test_register_should_raise_when_duplicate_entry_race_condition(
    service: UserService,
    user_repository: AsyncMock,
) -> None:
    user_repository.create.side_effect = DuplicateEntryError("email")

    with pytest.raises(UserAlreadyExistsError):
        await service.register("test@example.com", "Securepassword123!", "fr")


async def test_register_should_raise_email_send_error_when_email_fails(
    service: UserService,
    email_service: AsyncMock,
) -> None:
    email_service.send_activation_code.side_effect = NotificationError

    with pytest.raises(NotificationError):
        await service.register("test@example.com", "Securepassword123!", "fr")


# --- _validate_password() ---


async def test_register_should_raise_when_password_too_short(service: UserService) -> None:
    with pytest.raises(WeakPasswordError, match="at least 12 characters"):
        await service.register("x@example.com", "Short1!aaaa", "fr")


async def test_register_should_raise_when_password_too_long(
    user_repository: AsyncMock,
    activation_code_repository: AsyncMock,
    email_service: AsyncMock,
) -> None:
    config = UserServiceConfig(password_policy=PasswordPolicy(max_length=20))
    svc = UserService(user_repository, activation_code_repository, email_service, config=config)

    with pytest.raises(WeakPasswordError, match="at most 20 characters"):
        await svc.register("x@example.com", "A" * 21 + "a1!", "fr")


async def test_register_should_raise_when_password_missing_lowercase(service: UserService) -> None:
    with pytest.raises(WeakPasswordError, match="one lowercase letter"):
        await service.register("x@example.com", "NOLOWERCASE123!", "fr")


async def test_register_should_raise_when_password_missing_uppercase(service: UserService) -> None:
    with pytest.raises(WeakPasswordError, match="one uppercase letter"):
        await service.register("x@example.com", "nouppercase123!", "fr")


async def test_register_should_raise_when_password_missing_digit(service: UserService) -> None:
    with pytest.raises(WeakPasswordError, match="one digit"):
        await service.register("x@example.com", "NoDigitHere!!!!", "fr")


async def test_register_should_raise_when_password_missing_special(service: UserService) -> None:
    with pytest.raises(WeakPasswordError, match="one special character"):
        await service.register("x@example.com", "NoSpecial12345", "fr")


async def test_register_should_report_all_violations_at_once(service: UserService) -> None:
    with pytest.raises(
        WeakPasswordError, match=r"at least 12 characters.*one uppercase letter.*one digit.*one special"
    ):
        await service.register("x@example.com", "short", "fr")


# --- request_activation_code() ---


async def test_request_activation_code_should_send_email(
    service: UserService,
    user_repository: AsyncMock,
    activation_code_repository: AsyncMock,
    email_service: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _USER

    await service.request_activation_code("test@example.com")

    activation_code_repository.create.assert_called_once()
    email_service.send_activation_code.assert_called_once()


async def test_request_activation_code_should_do_nothing_when_user_is_active(
    service: UserService,
    user_repository: AsyncMock,
    activation_code_repository: AsyncMock,
    email_service: AsyncMock,
) -> None:
    active_user = _USER.__class__(
        id=_USER.id,
        email=_USER.email,
        password_hash=_USER.password_hash,
        is_active=True,
        lang=_USER.lang,
        created_at=_USER.created_at,
    )
    user_repository.get_by_email.return_value = active_user

    await service.request_activation_code("test@example.com")

    activation_code_repository.create.assert_not_called()
    email_service.send_activation_code.assert_not_called()


async def test_request_activation_code_should_do_nothing_when_email_unknown(
    service: UserService,
    user_repository: AsyncMock,
    activation_code_repository: AsyncMock,
    email_service: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = None

    await service.request_activation_code("unknown@example.com")

    activation_code_repository.create.assert_not_called()
    email_service.send_activation_code.assert_not_called()


async def test_request_activation_code_should_not_raise_when_email_fails(
    service: UserService,
    user_repository: AsyncMock,
    email_service: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _USER
    email_service.send_activation_code.side_effect = NotificationError

    await service.request_activation_code("test@example.com")


# --- activate_user() ---


_AUTH_USER = AuthenticatedUser(
    id=_USER.id,
    email=_USER.email,
    is_active=False,
    lang=_USER.lang,
    created_at=_USER.created_at,
)

_ACTIVE_USER = AuthenticatedUser(
    id=_USER.id,
    email=_USER.email,
    is_active=True,
    lang=_USER.lang,
    created_at=_USER.created_at,
)


async def test_activate_user_with_valid_code_claims_atomically_and_activates(
    service: UserService,
    activation_code_repository: AsyncMock,
    user_repository: AsyncMock,
) -> None:
    activation_code_repository.claim_active_code.return_value = _ACTIVATION_CODE

    await service.activate_user(_AUTH_USER, "1234")

    activation_code_repository.claim_active_code.assert_called_once_with(_AUTH_USER.id, "1234")
    user_repository.activate.assert_called_once_with(_AUTH_USER.id)


async def test_activate_user_already_active_raises_user_already_active(service: UserService) -> None:
    with pytest.raises(UserAlreadyActiveError):
        await service.activate_user(_ACTIVE_USER, "1234")


async def test_activate_user_expired_code_raises_and_invalidates_all(
    service: UserService,
    activation_code_repository: AsyncMock,
) -> None:
    activation_code_repository.claim_active_code.return_value = None
    activation_code_repository.get_expired_code.return_value = _ACTIVATION_CODE

    with pytest.raises(ActivationCodeExpiredError):
        await service.activate_user(_AUTH_USER, "1234")

    activation_code_repository.invalidate_all.assert_called_once_with(_AUTH_USER.id)


async def test_activate_user_wrong_code_raises_invalid_code(
    service: UserService,
    activation_code_repository: AsyncMock,
) -> None:
    activation_code_repository.claim_active_code.return_value = None
    activation_code_repository.get_expired_code.return_value = None
    activation_code_repository.record_failed_attempt.return_value = False

    with pytest.raises(InvalidActivationCodeError):
        await service.activate_user(_AUTH_USER, "9999")


async def test_activate_user_locks_after_max_attempts(
    service: UserService,
    activation_code_repository: AsyncMock,
) -> None:
    activation_code_repository.claim_active_code.return_value = None
    activation_code_repository.get_expired_code.return_value = None
    activation_code_repository.record_failed_attempt.return_value = True  # threshold reached

    with pytest.raises(ActivationCodeLockedError):
        await service.activate_user(_AUTH_USER, "9999")

    activation_code_repository.invalidate_all.assert_called_once_with(_AUTH_USER.id)
