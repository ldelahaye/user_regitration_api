"""FastAPI exception handler registration."""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.logging import CORRELATION_ID_HEADER
from app.domain.exceptions import (
    ActivationCodeExpiredError,
    ActivationCodeLockedError,
    DomainError,
    InactiveUserError,
    InvalidActivationCodeError,
    NotificationError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
    WeakPasswordError,
)

logger = logging.getLogger(__name__)

_HTTP_STATUS: dict[type[DomainError], int] = {
    UserAlreadyExistsError: status.HTTP_409_CONFLICT,
    UserNotFoundError: status.HTTP_401_UNAUTHORIZED,
    InactiveUserError: status.HTTP_403_FORBIDDEN,
    UserAlreadyActiveError: status.HTTP_409_CONFLICT,
    InvalidActivationCodeError: status.HTTP_400_BAD_REQUEST,
    ActivationCodeLockedError: status.HTTP_429_TOO_MANY_REQUESTS,
    ActivationCodeExpiredError: status.HTTP_400_BAD_REQUEST,
    WeakPasswordError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NotificationError: status.HTTP_502_BAD_GATEWAY,
}

_AUTH_ERRORS: set[type[DomainError]] = {UserNotFoundError, InactiveUserError}
_AUTH_HEADERS: dict[str, str] = {"WWW-Authenticate": "Basic"}

_ACTIVATE_ENDPOINT_PATH = "/users/activate"


def _is_activation_code_error(request: Request, errors: Sequence[Any]) -> bool:
    """Return True when the validation error is a pattern mismatch on the activation code field."""
    if request.url.path != _ACTIVATE_ENDPOINT_PATH:
        return False
    return any(
        err.get("type") == "string_pattern_mismatch" and tuple(err.get("loc", [])) == ("body", "code") for err in errors
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        http_status = _HTTP_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
        log_fn = logger.error if http_status >= 500 else logger.warning
        log_fn("Domain error: %s (code=%s)", exc.detail, exc.error_code, exc_info=http_status >= 500)
        headers = _AUTH_HEADERS if type(exc) in _AUTH_ERRORS else None
        return JSONResponse(
            status_code=http_status,
            content={"detail": exc.detail, "error_code": exc.error_code},
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": "HTTP_ERROR"},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()

        if _is_activation_code_error(request, errors):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "The activation code is invalid",
                    "error_code": "INVALID_ACTIVATION_CODE",
                },
            )

        safe_errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in errors]
        first_error = safe_errors[0] if safe_errors else {}
        field = " → ".join(str(loc) for loc in first_error.get("loc", []))
        message = first_error.get("msg", "Validation error")
        detail = f"{field}: {message}" if field else message
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": detail, "error_code": "VALIDATION_ERROR", "errors": safe_errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        cid = getattr(request.state, "correlation_id", None)
        headers = {CORRELATION_ID_HEADER: cid} if cid else None
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
            headers=headers,
        )
