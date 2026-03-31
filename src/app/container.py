"""Composition root — wires abstract ports to concrete infrastructure adapters."""

import asyncpg

from app.core.config import settings
from app.domain.ports import ActivationCodeRepository, UserRepository
from app.infrastructure.database.repositories import PgActivationCodeRepository, PgUserRepository


def create_user_repository(conn: asyncpg.Connection) -> UserRepository:
    return PgUserRepository(conn)


def create_activation_code_repository(conn: asyncpg.Connection) -> ActivationCodeRepository:
    return PgActivationCodeRepository(conn, settings.hmac_secret.get_secret_value())
