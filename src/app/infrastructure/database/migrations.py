"""SQL schema creation — runs on application startup."""

import logging

import asyncpg

logger = logging.getLogger(__name__)

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS users (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email      VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activation_codes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code       CHAR(4) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ
);
"""


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Apply database schema."""
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("Database migrations applied")
