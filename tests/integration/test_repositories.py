"""Integration tests for asyncpg repository implementations."""

import asyncpg
import pytest

from app.infrastructure.database.repositories import PgActivationCodeRepository, PgUserRepository, _hash_code

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
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("code@example.com", "hashed_password", "fr")

    code = await code_repo.create(user.id, "1234", ttl_seconds=60)

    assert code.user_id == user.id
    assert code.code == _hash_code("test-secret", user.id, "1234")
    assert code.used_at is None
    assert code.expires_at is not None
    assert code.failed_attempts == 0


async def test_claim_active_code(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("active_code@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "5678", ttl_seconds=60)

    claimed = await code_repo.claim_active_code(user.id, "5678")

    assert claimed is not None
    assert claimed.used_at is not None  # atomically marked used


async def test_claim_active_code_is_idempotent(db_conn: asyncpg.Connection) -> None:
    """Second claim of the same code returns None — race condition protection."""
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("idempotent@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "7777", ttl_seconds=60)

    first = await code_repo.claim_active_code(user.id, "7777")
    second = await code_repo.claim_active_code(user.id, "7777")

    assert first is not None
    assert second is None  # already claimed — TOCTOU protection


async def test_claim_active_code_wrong_code(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("wrong_code@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "1111", ttl_seconds=60)

    claimed = await code_repo.claim_active_code(user.id, "9999")

    assert claimed is None


async def test_get_expired_code(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("expired@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "2222", ttl_seconds=0)  # expires immediately

    found = await code_repo.get_expired_code(user.id, "2222")

    assert found is not None


async def test_invalidate_all(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("invalidate@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "3333", ttl_seconds=60)
    await code_repo.create(user.id, "4444", ttl_seconds=60)

    await code_repo.invalidate_all(user.id)

    assert await code_repo.claim_active_code(user.id, "3333") is None
    assert await code_repo.claim_active_code(user.id, "4444") is None


async def test_record_failed_attempt_returns_false_before_threshold(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("fail_attempt@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "9999", ttl_seconds=60)

    locked = await code_repo.record_failed_attempt(user.id, max_attempts=5)

    assert locked is False


async def test_record_failed_attempt_returns_true_at_threshold(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("lockout@example.com", "hashed_password", "fr")
    await code_repo.create(user.id, "0000", ttl_seconds=60)

    result = None
    for _ in range(3):
        result = await code_repo.record_failed_attempt(user.id, max_attempts=3)

    assert result is True


async def test_record_failed_attempt_returns_false_when_no_active_code(db_conn: asyncpg.Connection) -> None:
    user_repo = PgUserRepository(db_conn)
    code_repo = PgActivationCodeRepository(db_conn, hmac_secret="test-secret")  # noqa: S106
    user = await user_repo.create("no_code@example.com", "hashed_password", "fr")

    locked = await code_repo.record_failed_attempt(user.id, max_attempts=5)

    assert locked is False
