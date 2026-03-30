"""Domain entities — pure data, no framework dependencies."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

SUPPORTED_LANGUAGES: tuple[str, ...] = ("fr", "en", "es", "it", "de")


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str
    is_active: bool
    lang: str
    created_at: datetime


@dataclass(frozen=True)
class ActivationCode:
    id: UUID
    user_id: UUID
    code: str
    expires_at: datetime
    used_at: datetime | None
