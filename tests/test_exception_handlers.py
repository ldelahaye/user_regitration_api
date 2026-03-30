"""Tests for custom exception handlers — structured error responses."""

from fastapi import APIRouter
from httpx import AsyncClient
from pydantic import BaseModel

from app.core.exceptions import (
    ActivationCodeExpiredError,
    EmailSendError,
    InvalidActivationCodeError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.main import app

# Temporary router to trigger exceptions in tests
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


@_test_router.get("/email-send-error")
async def _raise_email_send_error() -> None:
    raise EmailSendError


@_test_router.get("/custom-detail")
async def _raise_custom_detail() -> None:
    raise UserNotFoundError(detail="User with ID abc123 not found")


class _ValidationBody(BaseModel):
    name: str


@_test_router.post("/validate")
async def _validate_body(body: _ValidationBody) -> _ValidationBody:
    return body


app.include_router(_test_router)


async def test_user_already_exists_returns_409(client: AsyncClient) -> None:
    response = await client.get("/_test_exceptions/user-already-exists")

    assert response.status_code == 409
    body = response.json()
    assert body["detail"] == "A user with this email already exists"
    assert body["error_code"] == "USER_ALREADY_EXISTS"


async def test_user_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/_test_exceptions/user-not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "User not found"
    assert body["error_code"] == "USER_NOT_FOUND"


async def test_invalid_activation_code_returns_400(client: AsyncClient) -> None:
    response = await client.get("/_test_exceptions/invalid-activation-code")

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "The activation code is invalid"
    assert body["error_code"] == "INVALID_ACTIVATION_CODE"


async def test_activation_code_expired_returns_400(client: AsyncClient) -> None:
    response = await client.get("/_test_exceptions/activation-code-expired")

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "The activation code has expired"
    assert body["error_code"] == "ACTIVATION_CODE_EXPIRED"


async def test_email_send_error_returns_502(client: AsyncClient) -> None:
    response = await client.get("/_test_exceptions/email-send-error")

    assert response.status_code == 502
    body = response.json()
    assert body["detail"] == "Failed to send email"
    assert body["error_code"] == "EMAIL_SEND_FAILED"


async def test_domain_error_with_custom_detail(client: AsyncClient) -> None:
    response = await client.get("/_test_exceptions/custom-detail")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "User with ID abc123 not found"
    assert body["error_code"] == "USER_NOT_FOUND"


async def test_http_exception_returns_structured_format(client: AsyncClient) -> None:
    response = await client.get("/nonexistent-path")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "Not Found"
    assert body["error_code"] == "HTTP_ERROR"


async def test_validation_error_returns_structured_format(client: AsyncClient) -> None:
    response = await client.post("/_test_exceptions/validate", json={"name": 123})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "detail" in body
    assert "errors" in body
