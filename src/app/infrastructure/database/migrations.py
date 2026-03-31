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
    lang       VARCHAR(5) NOT NULL DEFAULT 'fr',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activation_codes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code       TEXT NOT NULL,
    failed_attempts INT NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_activation_codes_user_code
    ON activation_codes (user_id, code, expires_at);
"""


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Apply database schema."""
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("Database migrations applied")
