"""
Shared FastAPI dependency for authenticated routes. Imported by every
other module that needs to know "who is calling this" — this is the
one place that turns a bearer token into a user, so ownership checks
(Feature 22) are enforced consistently everywhere.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.mongo import get_db
from app.modules.auth import repositories as repo

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = decode_access_token(credentials.credentials, settings)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = await repo.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict | None:
    """Returns the authenticated user if valid credentials are provided, or None if unauthenticated."""
    if credentials is None:
        return None
    try:
        user_id = decode_access_token(credentials.credentials, settings)
        if user_id is None:
            return None
        return await repo.get_user_by_id(db, user_id)
    except Exception:
        return None

