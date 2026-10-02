from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.rate_limit import auth_rate_limit
from app.db.mongo import get_db
from app.modules.auth import services
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter()


def _to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user["full_name"],
        phone=user.get("phone"),
        onboarding_completed=user.get("onboarding_completed", False),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit(key_prefix="auth_register"))],
)
async def register(
    body: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        _, token = await services.register_user(
            db, settings, body.email, body.password, body.full_name, body.phone
        )
    except services.EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(auth_rate_limit(key_prefix="auth_login"))],
)
async def login(
    body: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        _, token = await services.authenticate_user(db, settings, body.email, body.password)
    except services.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return TokenResponse(access_token=token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    token = await services.request_password_reset(db, body.email)
    response = ForgotPasswordResponse(
        message="If an account exists for that email, a password reset link has been prepared."
    )
    # Development has no configured mail transport, so expose the token for the local UI.
    if token and settings.ENV.lower() != "production":
        response.reset_token = token
    return response


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        await services.reset_password(db, body.token, body.new_password)
    except services.InvalidPasswordResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"message": "Password updated successfully. You can now sign in."}


@router.get("/me", response_model=UserPublic)
async def me(current_user: dict = Depends(get_current_user)):
    return _to_public(current_user)
