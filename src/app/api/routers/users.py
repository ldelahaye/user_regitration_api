"""User registration, activation code, and account activation router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_authenticated_user, get_user_service
from app.api.schemas.users import (
    ActivationCodeResponse,
    ActivationRequest,
    ActivationResponse,
    UserRegisterRequest,
    UserResponse,
)
from app.domain.models import User
from app.domain.services import UserService

router = APIRouter(prefix="/users", tags=["users"])

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthenticatedUser = Annotated[User, Depends(get_authenticated_user)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(body: UserRegisterRequest, user_service: UserServiceDep) -> UserResponse:
    user = await user_service.register(body.email, body.password.get_secret_value(), body.lang)
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        lang=user.lang,
        created_at=user.created_at,
    )


@router.post(
    "/{user_id}/activation-code",
    response_model=ActivationCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_activation_code(user_id: UUID, user_service: UserServiceDep) -> ActivationCodeResponse:
    activation_code = await user_service.send_activation_code(user_id)
    return ActivationCodeResponse(
        id=activation_code.id,
        user_id=activation_code.user_id,
        expires_at=activation_code.expires_at,
    )


@router.post("/activate", response_model=ActivationResponse, status_code=status.HTTP_200_OK)
async def activate_user(
    body: ActivationRequest,
    user: AuthenticatedUser,
    user_service: UserServiceDep,
) -> ActivationResponse:
    await user_service.activate_user(user, body.code)
    return ActivationResponse(detail="Account activated successfully")
