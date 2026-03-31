"""Domain exception classes — pure Python, no framework dependencies."""

import logging
from typing import ClassVar

logger = logging.getLogger(__name__)


# --- Base ---


class DomainError(Exception):
    """Base class for all domain exceptions."""

    error_code: ClassVar[str] = "DOMAIN_ERROR"
    _default_detail: ClassVar[str] = "A domain error occurred"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or type(self)._default_detail)

    @property
    def detail(self) -> str:
        return str(self.args[0])


# --- User ---


class UserAlreadyExistsError(DomainError):
    error_code: ClassVar[str] = "USER_ALREADY_EXISTS"
    _default_detail: ClassVar[str] = "A user with this email already exists"


class UserNotFoundError(DomainError):
    error_code: ClassVar[str] = "USER_NOT_FOUND"
    _default_detail: ClassVar[str] = "User not found"


class InactiveUserError(DomainError):
    error_code: ClassVar[str] = "INACTIVE_USER"
    _default_detail: ClassVar[str] = "Account is not activated"


class UserAlreadyActiveError(DomainError):
    error_code: ClassVar[str] = "USER_ALREADY_ACTIVE"
    _default_detail: ClassVar[str] = "Account is already active"


class WeakPasswordError(DomainError):
    error_code: ClassVar[str] = "WEAK_PASSWORD"
    _default_detail: ClassVar[str] = "Password does not meet security requirements"


# --- Activation ---


class InvalidActivationCodeError(DomainError):
    error_code: ClassVar[str] = "INVALID_ACTIVATION_CODE"
    _default_detail: ClassVar[str] = "The activation code is invalid"


class ActivationCodeLockedError(DomainError):
    error_code: ClassVar[str] = "ACTIVATION_CODE_LOCKED"
    _default_detail: ClassVar[str] = "Too many failed attempts — request a new activation code"


class ActivationCodeExpiredError(DomainError):
    error_code: ClassVar[str] = "ACTIVATION_CODE_EXPIRED"
    _default_detail: ClassVar[str] = "The activation code has expired"


# --- Infrastructure ---


class DuplicateEntryError(Exception):
    """Raised by repository adapters when a unique constraint is violated."""


# --- Notification ---


class NotificationError(DomainError):
    """The notification (email, SMS, etc.) could not be delivered."""

    error_code: ClassVar[str] = "NOTIFICATION_FAILED"
    _default_detail: ClassVar[str] = "Failed to send notification"
