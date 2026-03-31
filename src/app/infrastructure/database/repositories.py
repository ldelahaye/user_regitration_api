"""asyncpg implementations of domain repository ports — raw SQL, no ORM."""

import hashlib
import hmac
from datetime import timedelta
from uuid import UUID

import asyncpg

from app.core.exceptions import DuplicateEntryError
from app.domain.models import ActivationCode, User
from app.domain.ports import ActivationCodeRepository, UserRepository


def _hash_code(secret: str, user_id: UUID, code: str) -> str:
    """Return a keyed HMAC-SHA256 of the activation code.

    Uses a server-side secret as the HMAC key. user_id is included in the
    message to prevent cross-user precomputation. The raw code is never
    stored — only this hash is persisted.
    """
    key = secret.encode()
    message = f"{user_id}:{code}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


class PgUserRepository(UserRepository):
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, email: str, password_hash: str, lang: str) -> User:
        try:
            row = await self._conn.fetchrow(
                "INSERT INTO users (email, password_hash, lang) "
                "VALUES ($1, $2, $3) "
                "RETURNING id, email, password_hash, is_active, lang, created_at",
                email,
                password_hash,
                lang,
            )
        except asyncpg.UniqueViolationError:
            raise DuplicateEntryError from None
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
    def __init__(self, conn: asyncpg.Connection, hmac_secret: str) -> None:
        self._conn = conn
        self._hmac_secret = hmac_secret

    async def create(self, user_id: UUID, code: str, ttl_seconds: int) -> ActivationCode:
        code_hash = _hash_code(self._hmac_secret, user_id, code)
        row = await self._conn.fetchrow(
            "INSERT INTO activation_codes (user_id, code, expires_at) "
            "VALUES ($1, $2, now() + $3) "
            "RETURNING id, user_id, code, expires_at, used_at, failed_attempts",
            user_id,
            code_hash,
            timedelta(seconds=ttl_seconds),
        )
        return _row_to_activation_code(row)

    async def claim_active_code(self, user_id: UUID, code: str) -> ActivationCode | None:
        """Atomically mark a valid code as used and return it — prevents TOCTOU race."""
        code_hash = _hash_code(self._hmac_secret, user_id, code)
        row = await self._conn.fetchrow(
            "UPDATE activation_codes SET used_at = now() "
            "WHERE id = ("
            "  SELECT id FROM activation_codes "
            "  WHERE user_id = $1 AND code = $2 AND used_at IS NULL AND expires_at > now() "
            "  ORDER BY expires_at DESC LIMIT 1 "
            ") "
            "RETURNING id, user_id, code, expires_at, used_at, failed_attempts",
            user_id,
            code_hash,
        )
        return _row_to_activation_code(row) if row else None

    async def get_expired_code(self, user_id: UUID, code: str) -> ActivationCode | None:
        code_hash = _hash_code(self._hmac_secret, user_id, code)
        row = await self._conn.fetchrow(
            "SELECT id, user_id, code, expires_at, used_at, failed_attempts FROM activation_codes "
            "WHERE user_id = $1 AND code = $2 AND used_at IS NULL AND expires_at <= now() "
            "ORDER BY expires_at DESC LIMIT 1",
            user_id,
            code_hash,
        )
        return _row_to_activation_code(row) if row else None

    async def invalidate_all(self, user_id: UUID) -> None:
        await self._conn.execute(
            "UPDATE activation_codes SET used_at = now() WHERE user_id = $1 AND used_at IS NULL AND expires_at > now()",
            user_id,
        )

    async def record_failed_attempt(self, user_id: UUID, max_attempts: int) -> bool:
        """Increment failed_attempts on all active codes. Returns True if threshold reached."""
        row = await self._conn.fetchrow(
            "WITH updated AS ("
            "  UPDATE activation_codes "
            "  SET failed_attempts = failed_attempts + 1 "
            "  WHERE user_id = $1 AND used_at IS NULL AND expires_at > now() "
            "  RETURNING failed_attempts"
            ") SELECT MAX(failed_attempts) AS max_failed FROM updated",
            user_id,
        )
        if row is None or row["max_failed"] is None:
            return False
        return bool(row["max_failed"] >= max_attempts)


def _row_to_user(row: asyncpg.Record) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        is_active=row["is_active"],
        lang=row["lang"],
        created_at=row["created_at"],
    )


def _row_to_activation_code(row: asyncpg.Record) -> ActivationCode:
    return ActivationCode(
        id=row["id"],
        user_id=row["user_id"],
        code=row["code"],
        expires_at=row["expires_at"],
        used_at=row["used_at"],
        failed_attempts=row["failed_attempts"],
    )
