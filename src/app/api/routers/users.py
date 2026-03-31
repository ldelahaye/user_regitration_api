"""User registration, activation code, and account activation router."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import UserServiceDep, get_active_user, get_authenticated_user
from app.api.schemas.users import (
    ActivationCodeMessageResponse,
    ActivationCodeRequest,
    ActivationRequest,
    ActivationResponse,
    UserRegisterRequest,
    UserResponse,
)
from app.domain.models import AuthenticatedUser

router = APIRouter(prefix="/users", tags=["users"])

AuthenticatedUserDep = Annotated[AuthenticatedUser, Depends(get_authenticated_user)]
ActiveUserDep = Annotated[AuthenticatedUser, Depends(get_active_user)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(body: UserRegisterRequest, user_service: UserServiceDep) -> UserResponse:
    user = await user_service.register(body.email, body.password.get_secret_value(), body.lang)
    return UserResponse.from_domain(user)


@router.post(
    "/activation-code",
    response_model=ActivationCodeMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_activation_code(
    body: ActivationCodeRequest, user_service: UserServiceDep
) -> ActivationCodeMessageResponse:
    await user_service.request_activation_code(body.email)
    return ActivationCodeMessageResponse(detail="If the email exists, an activation code has been sent")


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user(user: ActiveUserDep) -> UserResponse:
    return UserResponse.from_domain(user)


@router.post("/activate", response_model=ActivationResponse, status_code=status.HTTP_200_OK)
async def activate_user(
    body: ActivationRequest,
    user: AuthenticatedUserDep,
    user_service: UserServiceDep,
) -> ActivationResponse:
    await user_service.activate_user(user, body.code)
    return ActivationResponse(detail="Account activated successfully")
