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


async def purge_user_account_data(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    """
    Cascading purge of all user-owned records (SEC-07).
    Deletes profile, resumes, tailored versions, applications, chat history, etc.
    Preserves all curated global jobs and strictly isolates from other users.
    """
    user_filter = {"user_id": user_id}
    
    # Cascade delete all user-scoped operational collections
    await db[Collections.PROFILES].delete_many(user_filter)
    await db[Collections.MASTER_RESUMES].delete_many(user_filter)
    await db[Collections.RESUME_VERSIONS].delete_many(user_filter)
    await db[Collections.RESUME_ANALYSES].delete_many(user_filter)
    await db[Collections.JOB_MATCHES].delete_many(user_filter)
    await db[Collections.APPLICATIONS].delete_many(user_filter)
    await db[Collections.SKILL_GAPS].delete_many(user_filter)
    await db[Collections.LEARNING_PATHS].delete_many(user_filter)
    await db[Collections.ACHIEVEMENTS].delete_many(user_filter)
    await db[Collections.INTERVIEW_SESSIONS].delete_many(user_filter)
    await db[Collections.CHAT_CONVERSATIONS].delete_many(user_filter)
    await db[Collections.AUDIT_LOGS].delete_many(user_filter)

    # Finally delete user account
    oid = _as_object_id(user_id)
    await db[Collections.USERS].delete_one({"_id": oid})

    return {"status": "deleted", "user_id": user_id}


def _as_object_id(user_id: str):
    from bson import ObjectId
    return ObjectId(user_id)
