"""Tests for custom exception handlers — structured error responses."""

from collections.abc import AsyncIterator

import pytest
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.api.schemas.users import ActivationRequest
from app.core.exception_handlers import register_exception_handlers
from app.domain.exceptions import (
    ActivationCodeExpiredError,
    ActivationCodeLockedError,
    InactiveUserError,
    InvalidActivationCodeError,
    NotificationError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

_test_router = APIRouter(prefix="/_test_exceptions", tags=["test"])


@_test_router.get("/user-already-exists")
async def _raise_user_already_exists() -> None:
    raise UserAlreadyExistsError


@_test_router.get("/user-not-found")
async def _raise_user_not_found() -> None:
    raise UserNotFoundError


@_test_router.get("/invalid-activation-code")
async def _raise_invalid_activation_code() -> None:
    raise InvalidActivationCodeError


@_test_router.get("/activation-code-expired")
async def _raise_activation_code_expired() -> None:
    raise ActivationCodeExpiredError


@_test_router.get("/activation-code-locked")
async def _raise_activation_code_locked() -> None:
    raise ActivationCodeLockedError


@_test_router.get("/email-send-error")
async def _raise_email_send_error() -> None:
    raise NotificationError


@_test_router.get("/user-already-active")
async def _raise_user_already_active() -> None:
    raise UserAlreadyActiveError


@_test_router.get("/inactive-user")
async def _raise_inactive_user() -> None:
    raise InactiveUserError


@_test_router.get("/custom-detail")
async def _raise_custom_detail() -> None:
    raise UserNotFoundError(detail="User with ID abc123 not found")


class _ValidationBody(BaseModel):
    name: str


@_test_router.post("/validate")
async def _validate_body(body: _ValidationBody) -> _ValidationBody:
    return body


_activate_router = APIRouter(prefix="/users", tags=["users"])


@_activate_router.post("/activate")
async def _activate(body: ActivationRequest) -> dict[str, str]:
    return {"detail": "ok"}


_test_app = FastAPI()
register_exception_handlers(_test_app)
_test_app.include_router(_test_router)
_test_app.include_router(_activate_router)


@pytest.fixture
async def exception_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_user_already_exists_returns_409(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/user-already-exists")

    assert response.status_code == 409
    body = response.json()
    assert body["detail"] == "A user with this email already exists"
    assert body["error_code"] == "USER_ALREADY_EXISTS"


async def test_user_not_found_returns_401(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/user-not-found")

    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "User not found"
    assert body["error_code"] == "USER_NOT_FOUND"
    assert response.headers["WWW-Authenticate"] == "Basic"


async def test_invalid_activation_code_returns_400(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/invalid-activation-code")

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "The activation code is invalid"
    assert body["error_code"] == "INVALID_ACTIVATION_CODE"


async def test_activation_code_locked_returns_429(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/activation-code-locked")

    assert response.status_code == 429
    body = response.json()
    assert body["error_code"] == "ACTIVATION_CODE_LOCKED"


async def test_activation_code_expired_returns_400(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/activation-code-expired")

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "The activation code has expired"
    assert body["error_code"] == "ACTIVATION_CODE_EXPIRED"


async def test_user_already_active_returns_409(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/user-already-active")

    assert response.status_code == 409
    body = response.json()
    assert body["detail"] == "Account is already active"
    assert body["error_code"] == "USER_ALREADY_ACTIVE"


async def test_inactive_user_returns_403(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/inactive-user")

    assert response.status_code == 403
    body = response.json()
    assert body["detail"] == "Account is not activated"
    assert body["error_code"] == "INACTIVE_USER"
    assert response.headers["WWW-Authenticate"] == "Basic"


async def test_notification_error_returns_502(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/email-send-error")

    assert response.status_code == 502
    body = response.json()
    assert body["detail"] == "Failed to send notification"
    assert body["error_code"] == "NOTIFICATION_FAILED"


async def test_domain_error_with_custom_detail(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/_test_exceptions/custom-detail")

    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "User with ID abc123 not found"
    assert body["error_code"] == "USER_NOT_FOUND"


async def test_http_exception_returns_structured_format(exception_client: AsyncClient) -> None:
    response = await exception_client.get("/nonexistent-path")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "Not Found"
    assert body["error_code"] == "HTTP_ERROR"


async def test_validation_error_returns_structured_format(exception_client: AsyncClient) -> None:
    response = await exception_client.post("/_test_exceptions/validate", json={"name": 123})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "detail" in body
    assert "errors" in body


async def test_activate_invalid_code_hides_pattern(exception_client: AsyncClient) -> None:
    response = await exception_client.post("/users/activate", json={"code": "62734"})

    assert response.status_code == 400
    body = response.json()
    assert body == {"detail": "The activation code is invalid", "error_code": "INVALID_ACTIVATION_CODE"}


async def test_activate_valid_code_passes_validation(exception_client: AsyncClient) -> None:
    response = await exception_client.post("/users/activate", json={"code": "1234"})

    assert response.status_code == 200
