"""Shared FastAPI dependencies — database connection lifecycle."""

from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings
from app.core.security import verify_credentials
from app.domain.models import User
from app.domain.ports import EmailService
from app.domain.services import UserService
from app.infrastructure.database.repositories import PgActivationCodeRepository, PgUserRepository


def get_pool(request: Request) -> asyncpg.Pool:
    """Retrieve the database pool from app state."""
    return request.app.state.db_pool


def get_email_service(request: Request) -> EmailService:
    """Retrieve the email service from app state."""
    service: EmailService = request.app.state.email_service
    return service


async def get_connection(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection with transaction — commit on success, rollback on error."""
    async with pool.acquire() as conn:
        transaction = conn.transaction()
        await transaction.start()
        try:
            yield conn
        except Exception:
            await transaction.rollback()
            raise
        else:
            await transaction.commit()


DbConnection = Annotated[asyncpg.Connection, Depends(get_connection)]

_http_basic = HTTPBasic()


async def get_authenticated_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(_http_basic)],
    conn: DbConnection,
) -> User:
    """Verify Basic Auth credentials and return the authenticated user."""
    user_repository = PgUserRepository(conn)
    return await verify_credentials(credentials, user_repository)


async def get_user_service(
    conn: DbConnection,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> UserService:
    return UserService(
        PgUserRepository(conn),
        PgActivationCodeRepository(conn),
        email_service,
        activation_code_ttl_minutes=settings.activation_code_ttl_minutes,
    )
