from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections
from app.modules.profile import repositories as repo
from app.modules.profile.schemas import OnboardingRequest


async def complete_onboarding(db: AsyncIOMotorDatabase, user_id: str, body: OnboardingRequest) -> dict:
    profile = await repo.upsert_profile(db, user_id, body.model_dump(mode="json"))
    await db[Collections.USERS].update_one(
        {"_id": _as_object_id(user_id)}, {"$set": {"onboarding_completed": True}}
    )
    return profile


def _as_object_id(user_id: str):
    from bson import ObjectId
    return ObjectId(user_id)
