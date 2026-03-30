"""FastAPI exception handler registration."""

import logging

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.exceptions import (
    ActivationCodeExpiredError,
    ActivationCodeLockedError,
    DomainError,
    DuplicateEntryError,
    InactiveUserError,
    InvalidActivationCodeError,
    NotificationError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

_HTTP_STATUS: dict[type[DomainError], int] = {
    UserAlreadyExistsError: 409,
    UserNotFoundError: 404,
    InactiveUserError: 403,
    UserAlreadyActiveError: 409,
    InvalidActivationCodeError: 400,
    ActivationCodeLockedError: 429,
    ActivationCodeExpiredError: 400,
    NotificationError: 502,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        http_status = _HTTP_STATUS.get(type(exc), 400)
        log_fn = logger.error if http_status >= 500 else logger.warning
        log_fn("Domain error: %s (code=%s)", exc.detail, exc.error_code)
        return JSONResponse(
            status_code=http_status,
            content={"detail": exc.detail, "error_code": exc.error_code},
        )

    @app.exception_handler(DuplicateEntryError)
    async def duplicate_entry_handler(_request: Request, exc: DuplicateEntryError) -> JSONResponse:
        logger.warning("Duplicate entry: %s", exc)
        return JSONResponse(
            status_code=409,
            content={"detail": "Resource already exists", "error_code": "DUPLICATE_ENTRY"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": "HTTP_ERROR"},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first_error = errors[0] if errors else {}
        field = " → ".join(str(loc) for loc in first_error.get("loc", []))
        message = first_error.get("msg", "Validation error")
        detail = f"{field}: {message}" if field else message
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": detail, "error_code": "VALIDATION_ERROR", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
        )
