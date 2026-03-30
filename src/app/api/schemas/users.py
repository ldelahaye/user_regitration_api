"""Pydantic schemas for user endpoints — request validation and response serialization."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    lang: str = Field(pattern="^(fr|en|es|it|de)$")


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    lang: str
    created_at: datetime


class ActivationCodeResponse(BaseModel):
    id: UUID
    user_id: UUID
    expires_at: datetime


class ActivationRequest(BaseModel):
    code: str = Field(pattern=r"^\d{4}$")


class ActivationResponse(BaseModel):
    detail: str
