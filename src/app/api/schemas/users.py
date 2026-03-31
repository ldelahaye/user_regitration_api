"""Pydantic schemas for user endpoints — request validation and response serialization."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

from app.domain.models import AuthenticatedUser, SupportedLang, User

_LOWERCASE_RE = re.compile(r"[a-z]")
_UPPERCASE_RE = re.compile(r"[A-Z]")
_DIGIT_RE = re.compile(r"\d")
_SPECIAL_RE = re.compile(r"[^a-zA-Z0-9]")


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    lang: SupportedLang

    @field_validator("password", mode="after")
    @classmethod
    def validate_password_policy(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        violations: list[str] = []

        if not _LOWERCASE_RE.search(password):
            violations.append("one lowercase letter")
        if not _UPPERCASE_RE.search(password):
            violations.append("one uppercase letter")
        if not _DIGIT_RE.search(password):
            violations.append("one digit")
        if not _SPECIAL_RE.search(password):
            violations.append("one special character")

        if violations:
            raise ValueError(f"Password must contain: {', '.join(violations)}")

        return value


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    lang: str
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User | AuthenticatedUser) -> UserResponse:
        return cls.model_validate(user, from_attributes=True)


class ActivationCodeRequest(BaseModel):
    email: EmailStr


class ActivationCodeMessageResponse(BaseModel):
    detail: str


class ActivationRequest(BaseModel):
    code: str = Field(pattern=r"^\d{4}$")


class ActivationResponse(BaseModel):
    detail: str
