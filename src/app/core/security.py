"""HTTP Basic Auth credential verification."""

import asyncio

import bcrypt
from fastapi import HTTPException, status
from fastapi.security import HTTPBasicCredentials

from app.domain.models import User
from app.domain.ports import UserRepository

# Pre-computed dummy hash to prevent timing-based user enumeration.
# When an email doesn't exist, we still run bcrypt.checkpw against this hash
# so the response time is identical to a valid email with a wrong password.
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode()


async def verify_credentials(
    credentials: HTTPBasicCredentials,
    user_repository: UserRepository,
) -> User:
    """Verify Basic Auth credentials — return the user or raise 401.

    Always runs bcrypt.checkpw to prevent timing-based user enumeration.
    """
    user = await user_repository.get_by_email(credentials.username)
    hash_to_check = user.password_hash if user is not None else _DUMMY_HASH
    password_valid = await asyncio.to_thread(bcrypt.checkpw, credentials.password.encode(), hash_to_check.encode())

    if not password_valid or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user
