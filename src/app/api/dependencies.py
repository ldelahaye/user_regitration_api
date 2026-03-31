"""Shared FastAPI dependencies — database connection lifecycle and authentication."""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

import asyncpg
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.container import create_activation_code_repository, create_user_repository
from app.core.config import settings
from app.domain.exceptions import InactiveUserError, UserNotFoundError
from app.domain.models import AuthenticatedUser
from app.domain.ports import ActivationCodeRepository, EmailService, UserRepository
from app.domain.services import PasswordPolicy, UserService, UserServiceConfig

logger = logging.getLogger(__name__)


def get_pool(request: Request) -> asyncpg.Pool:
    """Retrieve the database pool from app state."""
    return request.app.state.db_pool


def get_email_service(request: Request) -> EmailService:
    """Retrieve the email service from app state."""
    service: EmailService = request.app.state.email_service
    return service


async def get_connection(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> AsyncGenerator[asyncpg.Connection]:
    """Acquire a connection with transaction — commit on success, rollback on error."""
    async with pool.acquire() as conn:
        transaction = conn.transaction()
        await transaction.start()
        try:
            yield conn
        except Exception:
            try:
                await transaction.rollback()
            except Exception:
                logger.exception("Failed to rollback transaction")
            raise
        else:
            await transaction.commit()


DbConnection = Annotated[asyncpg.Connection, Depends(get_connection, scope="request")]


async def get_user_repository(conn: DbConnection) -> UserRepository:
    return create_user_repository(conn)


async def get_activation_code_repository(conn: DbConnection) -> ActivationCodeRepository:
    return create_activation_code_repository(conn)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
ActivationCodeRepositoryDep = Annotated[ActivationCodeRepository, Depends(get_activation_code_repository)]

_http_basic = HTTPBasic()

_service_config = UserServiceConfig(
    activation_code_ttl_minutes=settings.activation_code_ttl_minutes,
    activation_max_attempts=settings.activation_max_attempts,
    bcrypt_rounds=settings.bcrypt_rounds,
    password_policy=PasswordPolicy(
        min_length=settings.password_min_length,
        max_length=settings.password_max_length,
        require_uppercase=settings.password_require_uppercase,
        require_lowercase=settings.password_require_lowercase,
        require_digit=settings.password_require_digit,
        require_special=settings.password_require_special,
    ),
)


async def get_user_service(
    user_repository: UserRepositoryDep,
    activation_code_repository: ActivationCodeRepositoryDep,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> UserService:
    return UserService(user_repository, activation_code_repository, email_service, config=_service_config)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_authenticated_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(_http_basic)],
    user_service: UserServiceDep,
) -> AuthenticatedUser:
    """Verify Basic Auth credentials and return the authenticated user."""
    try:
        return await user_service.authenticate(credentials.username, credentials.password)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers=_http_basic.make_authenticate_headers(),
        ) from None


async def get_active_user(user: Annotated[AuthenticatedUser, Depends(get_authenticated_user)]) -> AuthenticatedUser:
    """Verify that the authenticated user has an active account."""
    if not user.is_active:
        raise InactiveUserError
    return user
