from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.profile import repositories as repo
from app.modules.profile import services
from app.modules.profile.schemas import OnboardingRequest, ProfileResponse

router = APIRouter()


@router.post("/onboarding/complete", response_model=ProfileResponse)
async def complete_onboarding(
    body: OnboardingRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    profile = await services.complete_onboarding(db, str(current_user["_id"]), body)
    profile.pop("_id", None)
    return ProfileResponse(**profile)


@router.get("/me", response_model=ProfileResponse | None)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    profile = await repo.get_profile(db, str(current_user["_id"]))
    if profile is None:
        return None
    profile.pop("_id", None)
    return ProfileResponse(**profile)


@router.delete("/me")
async def delete_my_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Deletes the authenticated user's account and cascades through all user-owned data (SEC-07).
    """
    user_id = str(current_user["_id"])
    return await services.purge_user_account_data(db, user_id)
