"""Domain services — business logic orchestration."""

import logging
import secrets
from uuid import UUID

import bcrypt

from app.core.exceptions import (
    ActivationCodeExpiredError,
    InvalidActivationCodeError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.domain.models import ActivationCode, User
from app.domain.ports import ActivationCodeRepository, EmailService, UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        activation_code_repository: ActivationCodeRepository,
        email_service: EmailService,
        activation_code_ttl_minutes: int = 1,
    ) -> None:
        self._user_repository = user_repository
        self._activation_code_repository = activation_code_repository
        self._email_service = email_service
        self._activation_code_ttl_minutes = activation_code_ttl_minutes

    async def register(self, email: str, password: str, lang: str) -> User:
        """Register a new user with email and password."""
        existing = await self._user_repository.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return await self._user_repository.create(email, password_hash, lang)

    async def send_activation_code(self, user_id: UUID) -> ActivationCode:
        """Generate a 4-digit code, store it, and send it by email."""
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        code = _generate_4_digit_code()
        ttl_seconds = self._activation_code_ttl_minutes * 60
        activation_code = await self._activation_code_repository.create(user_id, code, ttl_seconds)
        await self._email_service.send_activation_code(user.email, code, self._activation_code_ttl_minutes, user.lang)
        return activation_code

    async def activate_user(self, user: User, code: str) -> None:
        """Activate a user account with a 4-digit code."""
        if user.is_active:
            raise InvalidActivationCodeError(detail="Account is already active")

        activation_code = await self._activation_code_repository.get_active_code(user.id, code)
        if activation_code is None:
            expired = await self._activation_code_repository.get_expired_code(user.id, code)
            if expired is not None:
                raise ActivationCodeExpiredError
            raise InvalidActivationCodeError

        await self._activation_code_repository.mark_used(activation_code.id)
        await self._user_repository.activate(user.id)


def _generate_4_digit_code() -> str:
    """Generate a cryptographically secure 4-digit code."""
    return f"{secrets.randbelow(10000):04d}"
