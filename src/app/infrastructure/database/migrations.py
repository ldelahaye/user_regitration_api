"""Versioned database migrations via yoyo-migrations."""

import asyncio
import logging
from pathlib import Path

from yoyo import get_backend, read_migrations

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _yoyo_url(database_url: str) -> str:
    """Ensure the URL uses the postgresql:// scheme that yoyo's psycopg2 backend expects."""
    return database_url.replace("postgres://", "postgresql://", 1)


def _apply_migrations(database_url: str) -> None:
    """Apply all pending migrations synchronously. Called via asyncio.to_thread at startup."""
    backend = get_backend(_yoyo_url(database_url))
    migrations = read_migrations(str(_MIGRATIONS_DIR))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    logger.info("Database migrations applied")


async def run_migrations(database_url: str) -> None:
    """Apply pending yoyo migrations. Wraps the sync call in a thread to avoid blocking the event loop."""
    await asyncio.to_thread(_apply_migrations, database_url)
