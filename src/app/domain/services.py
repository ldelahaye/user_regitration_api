"""Domain services — business logic orchestration."""

import logging

import bcrypt

from app.core.exceptions import UserAlreadyExistsError
from app.domain.models import User
from app.domain.ports import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def register(self, email: str, password: str) -> User:
        """Register a new user with email and password."""
        existing = await self._user_repository.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return await self._user_repository.create(email, password_hash)
