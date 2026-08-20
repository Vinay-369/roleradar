"""
Auth business logic. Pure Python + repository calls — no framework
(FastAPI) concerns here, so it's directly unit-testable.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth import repositories as repo


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register_user(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    email: str,
    password: str,
    full_name: str,
    phone: str | None,
) -> tuple[dict, str]:
    existing = await repo.get_user_by_email(db, email)
    if existing:
        raise EmailAlreadyRegisteredError(f"Email {email} is already registered.")

    password_hash = hash_password(password)
    user = await repo.create_user(db, email, password_hash, full_name, phone)
    token = create_access_token(subject=str(user["_id"]), settings=settings)
    return user, token


async def authenticate_user(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    email: str,
    password: str,
) -> tuple[dict, str]:
    user = await repo.get_user_by_email(db, email)
    if not user or not verify_password(password, user["password_hash"]):
        raise InvalidCredentialsError("Invalid email or password.")

    token = create_access_token(subject=str(user["_id"]), settings=settings)
    return user, token
