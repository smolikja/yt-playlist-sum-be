from fastapi import APIRouter
from fastapi_users import FastAPIUsers
import uuid
from app.models.sql import User
from app.repositories.users import get_user_manager
from app.core.auth import auth_backend
from app.models.api import UserRead, UserCreate, UserUpdate

fastapi_users_app = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

router = APIRouter()

router.include_router(
    fastapi_users_app.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

router.include_router(
    fastapi_users_app.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users_app.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

current_active_user = fastapi_users_app.current_user(active=True)
current_optional_user = fastapi_users_app.current_user(optional=True, active=True)
