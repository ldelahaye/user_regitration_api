"""Shared FastAPI dependencies — database connection lifecycle."""

from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from app.domain.ports import ActivationCodeRepository, UserRepository
from app.domain.services import UserService
from app.infrastructure.database.repositories import PgActivationCodeRepository, PgUserRepository


def get_pool(request: Request) -> asyncpg.Pool:
    """Retrieve the database pool from app state."""
    return request.app.state.db_pool


async def get_connection(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the pool, release on completion."""
    async with pool.acquire() as conn:
        yield conn


DbConnection = Annotated[asyncpg.Connection, Depends(get_connection)]


async def get_user_repository(conn: DbConnection) -> UserRepository:
    return PgUserRepository(conn)


async def get_activation_code_repository(conn: DbConnection) -> ActivationCodeRepository:
    return PgActivationCodeRepository(conn)


async def get_user_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(user_repository)
