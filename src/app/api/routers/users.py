"""User registration router."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_user_service
from app.api.schemas.users import UserRegisterRequest, UserResponse
from app.domain.services import UserService

router = APIRouter(prefix="/users", tags=["users"])

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(body: UserRegisterRequest, user_service: UserServiceDep) -> UserResponse:
    user = await user_service.register(body.email, body.password.get_secret_value())
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
    )
