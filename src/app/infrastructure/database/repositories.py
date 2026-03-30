"""asyncpg implementations of domain repository ports — raw SQL, no ORM."""

from datetime import timedelta
from uuid import UUID

import asyncpg

from app.domain.models import ActivationCode, User
from app.domain.ports import ActivationCodeRepository, UserRepository


class PgUserRepository(UserRepository):
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, email: str, password_hash: str, lang: str) -> User:
        row = await self._conn.fetchrow(
            "INSERT INTO users (email, password_hash, lang) "
            "VALUES ($1, $2, $3) "
            "RETURNING id, email, password_hash, is_active, lang, created_at",
            email,
            password_hash,
            lang,
        )
        return _row_to_user(row)

    async def get_by_email(self, email: str) -> User | None:
        row = await self._conn.fetchrow(
            "SELECT id, email, password_hash, is_active, lang, created_at FROM users WHERE email = $1",
            email,
        )
        return _row_to_user(row) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._conn.fetchrow(
            "SELECT id, email, password_hash, is_active, lang, created_at FROM users WHERE id = $1",
            user_id,
        )
        return _row_to_user(row) if row else None

    async def activate(self, user_id: UUID) -> None:
        await self._conn.execute("UPDATE users SET is_active = TRUE WHERE id = $1", user_id)


class PgActivationCodeRepository(ActivationCodeRepository):
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, code: str, ttl_seconds: int) -> ActivationCode:
        row = await self._conn.fetchrow(
            "INSERT INTO activation_codes (user_id, code, expires_at) "
            "VALUES ($1, $2, now() + $3) "
            "RETURNING id, user_id, code, expires_at, used_at",
            user_id,
            code,
            timedelta(seconds=ttl_seconds),
        )
        return _row_to_activation_code(row)

    async def get_active_code(self, user_id: UUID, code: str) -> ActivationCode | None:
        row = await self._conn.fetchrow(
            "SELECT id, user_id, code, expires_at, used_at FROM activation_codes "
            "WHERE user_id = $1 AND code = $2 AND used_at IS NULL AND expires_at > now() "
            "ORDER BY expires_at DESC LIMIT 1",
            user_id,
            code,
        )
        return _row_to_activation_code(row) if row else None

    async def get_expired_code(self, user_id: UUID, code: str) -> ActivationCode | None:
        row = await self._conn.fetchrow(
            "SELECT id, user_id, code, expires_at, used_at FROM activation_codes "
            "WHERE user_id = $1 AND code = $2 AND used_at IS NULL AND expires_at <= now() "
            "ORDER BY expires_at DESC LIMIT 1",
            user_id,
            code,
        )
        return _row_to_activation_code(row) if row else None

    async def mark_used(self, code_id: UUID) -> None:
        await self._conn.execute(
            "UPDATE activation_codes SET used_at = now() WHERE id = $1",
            code_id,
        )


def _row_to_user(row: asyncpg.Record | None) -> User:
    if row is None:
        msg = "Expected a user row but got None"
        raise ValueError(msg)
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        is_active=row["is_active"],
        lang=row["lang"],
        created_at=row["created_at"],
    )


def _row_to_activation_code(row: asyncpg.Record | None) -> ActivationCode:
    if row is None:
        msg = "Expected an activation_code row but got None"
        raise ValueError(msg)
    return ActivationCode(
        id=row["id"],
        user_id=row["user_id"],
        code=row["code"],
        expires_at=row["expires_at"],
        used_at=row["used_at"],
    )
