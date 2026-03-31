"""Domain services — business logic orchestration."""

import asyncio
import logging
import re
import secrets
from dataclasses import dataclass, field

import bcrypt

from app.core.exceptions import (
    ActivationCodeExpiredError,
    ActivationCodeLockedError,
    DuplicateEntryError,
    InvalidActivationCodeError,
    NotificationError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
    WeakPasswordError,
)
from app.domain.models import AuthenticatedUser, User
from app.domain.ports import ActivationCodeRepository, EmailService, UserRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PasswordPolicy:
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True


@dataclass(frozen=True)
class UserServiceConfig:
    activation_code_ttl_minutes: int = 1
    activation_max_attempts: int = 5
    bcrypt_rounds: int = 12
    password_policy: PasswordPolicy = field(default_factory=PasswordPolicy)


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        activation_code_repository: ActivationCodeRepository,
        email_service: EmailService,
        config: UserServiceConfig | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._activation_code_repository = activation_code_repository
        self._email_service = email_service
        cfg = config or UserServiceConfig()
        self._activation_code_ttl_minutes = cfg.activation_code_ttl_minutes
        self._activation_max_attempts = cfg.activation_max_attempts
        self._bcrypt_rounds = cfg.bcrypt_rounds
        self._password_policy = cfg.password_policy
        self._dummy_hash = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=self._bcrypt_rounds)).decode()

    async def authenticate(self, email: str, password: str) -> AuthenticatedUser:
        """Verify credentials — return an AuthenticatedUser or raise UserNotFoundError.

        Always runs bcrypt.checkpw to prevent timing-based user enumeration.
        password_hash is never propagated beyond this method.
        """
        user = await self._user_repository.get_by_email(email)
        hash_to_check = user.password_hash if user is not None else self._dummy_hash
        password_valid = await asyncio.to_thread(bcrypt.checkpw, password.encode(), hash_to_check.encode())

        if not password_valid or user is None:
            raise UserNotFoundError("Invalid credentials")

        return AuthenticatedUser(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            lang=user.lang,
            created_at=user.created_at,
        )

    def _validate_password(self, password: str) -> None:
        """Enforce password policy — raises WeakPasswordError with all violations."""
        policy = self._password_policy
        violations: list[str] = []

        if len(password) < policy.min_length:
            violations.append(f"at least {policy.min_length} characters")
        if len(password) > policy.max_length:
            violations.append(f"at most {policy.max_length} characters")
        if policy.require_lowercase and not re.search(r"[a-z]", password):
            violations.append("one lowercase letter")
        if policy.require_uppercase and not re.search(r"[A-Z]", password):
            violations.append("one uppercase letter")
        if policy.require_digit and not re.search(r"\d", password):
            violations.append("one digit")
        if policy.require_special and not re.search(r"[^a-zA-Z0-9]", password):
            violations.append("one special character")

        if violations:
            raise WeakPasswordError(f"Password must contain: {', '.join(violations)}")

    async def register(self, email: str, password: str, lang: str) -> User:
        """Register a new user and send an activation code by email."""
        self._validate_password(password)

        existing = await self._user_repository.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError

        password_hash = await asyncio.to_thread(
            lambda: bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=self._bcrypt_rounds)).decode()
        )
        try:
            user = await self._user_repository.create(email, password_hash, lang)
        except DuplicateEntryError:
            # Race condition: two concurrent registrations passed the get_by_email check.
            raise UserAlreadyExistsError from None

        await self._issue_activation_code(user, raise_on_email_error=True)

        return user

    async def request_activation_code(self, email: str) -> None:
        """Generate and send an activation code by email.

        If the email is not found, silently returns to prevent user enumeration.
        """
        user = await self._user_repository.get_by_email(email)
        if user is None or user.is_active:
            return

        await self._issue_activation_code(user, raise_on_email_error=False)

    async def activate_user(self, user: AuthenticatedUser, code: str) -> None:
        """Activate a user account with a 4-digit code."""
        if user.is_active:
            raise UserAlreadyActiveError

        claimed = await self._activation_code_repository.claim_active_code(user.id, code)
        if claimed is None:
            expired = await self._activation_code_repository.get_expired_code(user.id, code)
            if expired is not None:
                await self._activation_code_repository.invalidate_all(user.id)
                raise ActivationCodeExpiredError

            locked = await self._activation_code_repository.record_failed_attempt(
                user.id, self._activation_max_attempts
            )
            if locked:
                await self._activation_code_repository.invalidate_all(user.id)
                raise ActivationCodeLockedError
            raise InvalidActivationCodeError

        await self._user_repository.activate(user.id)

    async def _issue_activation_code(self, user: User, *, raise_on_email_error: bool) -> None:
        """Generate an activation code, persist it, and send it by email."""
        code = _generate_4_digit_code()
        ttl_seconds = self._activation_code_ttl_minutes * 60
        await self._activation_code_repository.create(user.id, code, ttl_seconds)

        try:
            await self._email_service.send_activation_code(
                user.email, code, self._activation_code_ttl_minutes, user.lang
            )
        except NotificationError:
            if raise_on_email_error:
                logger.error(
                    "Failed to send activation code during registration for user %s — rolling back",
                    user.id,
                    exc_info=True,
                )
                raise
            logger.warning(
                "Failed to send activation code for user %s",
                user.id,
                exc_info=True,
            )


def _generate_4_digit_code() -> str:
    """Generate a cryptographically secure 4-digit code."""
    return f"{secrets.randbelow(10000):04d}"
