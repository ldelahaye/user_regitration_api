"""Pydantic schemas for user endpoints — request validation and response serialization."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime
