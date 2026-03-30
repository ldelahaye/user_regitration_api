"""Integration tests for asyncpg repository implementations."""

import asyncpg
import pytest

from app.infrastructure.database.repositories import PgActivationCodeRepository, PgUserRepository

pytestmark = pytest.mark.integration


async def test_create_user(db_conn: asyncpg.Connection) -> None:
    repo = PgUserRepository(db_conn)

    user = await repo.create("test@example.com", "hashed_password", "fr")

    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_password"
    assert user.is_active is False
    assert user.lang == "fr"
    assert user.id is not None
    assert user.created_at is not None


async def test_get_by_email(db_conn: asyncpg.Connection) -> None:
    repo = PgUserRepository(db_conn)
    await repo.create("find@example.com", "hashed_password", "en")

    found = await repo.get_by_email("find@example.com")

    assert found is not None
    assert found.email == "find@example.com"


async def test_get_by_email_not_found(db_conn: asyncpg.Connection) -> None:
    repo = PgUserRepository(db_conn)

    found = await repo.get_by_email("nonexistent@example.com")

    assert found is None


async def test_get_by_id(db_conn: asyncpg.Connection) -> None:
    repo = PgUserRepository(db_conn)
    user = await repo.create("byid@example.com", "hashed_password", "fr")

    found = await repo.get_by_id(user.id)

    assert found is not None
    assert found.id == user.id


async def test_activate_user(db_conn: asyncpg.Connection) -> None:
    repo = PgUserRepository(db_conn)
    user = await repo.create("activate@example.com", "hashed_password", "fr")
    assert user.is_active is False

    await repo.activate(user.id)

    activated = await repo.get_by_id(user.id)
    assert activated is not None
    assert activated.is_active is True


async def test_create_activation_code(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn)
    user = await user_repo.create("code@example.com", "hashed_password", "fr")

    code = await code_repo.create(user.id, "1234", ttl_seconds=60)

    assert code.user_id == user.id
    assert code.code == "1234"
    assert code.used_at is None
    assert code.expires_at is not None


async def test_get_active_code(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn)
    user = await user_repo.create("active_code@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "5678", ttl_seconds=60)

    found = await code_repo.get_active_code(user.id, "5678")

    assert found is not None
    assert found.code == "5678"


async def test_get_active_code_wrong_code(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn)
    user = await user_repo.create("wrong_code@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "1111", ttl_seconds=60)

    found = await code_repo.get_active_code(user.id, "9999")

    assert found is None


async def test_mark_code_used(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn)
    user = await user_repo.create("mark_used@example.com", "hashed_password", "fr")
    code = await code_repo.create(user.id, "4321", ttl_seconds=60)

    await code_repo.mark_used(code.id)

    found = await code_repo.get_active_code(user.id, "4321")
    assert found is None  # used_at is set, so it's no longer "active"
