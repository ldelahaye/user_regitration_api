"""Pydantic schemas for user endpoints — request validation and response serialization."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.domain.models import AuthenticatedUser, User

SupportedLang = Literal["fr", "en", "es", "it", "de"]


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    lang: SupportedLang


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
