"""Domain exception classes and HTTP exception handler registration."""

import logging

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


# --- Domain exceptions ---


class DomainError(Exception):
    """Base class for all domain exceptions."""

    error_code: str = "DOMAIN_ERROR"
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "A domain error occurred"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class UserAlreadyExistsError(DomainError):
    error_code = "USER_ALREADY_EXISTS"
    status_code = status.HTTP_409_CONFLICT
    detail = "A user with this email already exists"


class UserNotFoundError(DomainError):
    error_code = "USER_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    detail = "User not found"


class InvalidActivationCodeError(DomainError):
    error_code = "INVALID_ACTIVATION_CODE"
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "The activation code is invalid"


class ActivationCodeExpiredError(DomainError):
    error_code = "ACTIVATION_CODE_EXPIRED"
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "The activation code has expired"


class EmailSendError(DomainError):
    error_code = "EMAIL_SEND_FAILED"
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "Failed to send email"


# --- Exception handler registration ---


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        logger.warning("Domain error: %s (code=%s)", exc.detail, exc.error_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": exc.error_code},
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
