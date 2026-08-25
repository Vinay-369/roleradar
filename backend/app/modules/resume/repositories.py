from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections


async def get_next_version(db: AsyncIOMotorDatabase, user_id: str) -> int:
    latest = await db[Collections.MASTER_RESUMES].find_one(
        {"user_id": user_id}, sort=[("version", -1)]
    )
    return (latest["version"] + 1) if latest else 1


async def deactivate_previous(db: AsyncIOMotorDatabase, user_id: str) -> None:
    await db[Collections.MASTER_RESUMES].update_many(
        {"user_id": user_id, "is_active": True}, {"$set": {"is_active": False}}
    )


async def create_master_resume(
    db: AsyncIOMotorDatabase,
    user_id: str,
    version: int,
    file_name: str,
    file_type: str,
    raw_text: str,
    parsed: dict,
    parseability: dict,
    recruiter_impact: dict,
    action_verbs: dict | None = None,
    skills_depth: dict | None = None,
    strict_ats_score: int = 100,
    ats_status: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "version": version,
        "is_active": True,
        "file_name": file_name,
        "file_type": file_type,
        "raw_text": raw_text,
        "parsed": parsed,
        "parseability": parseability,
        "recruiter_impact": recruiter_impact,
        "action_verbs": action_verbs,
        "skills_depth": skills_depth,
        "strict_ats_score": strict_ats_score,
        "ats_status": ats_status,
        "created_at": now,
    }
    result = await db[Collections.MASTER_RESUMES].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_active_master_resume(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    return await db[Collections.MASTER_RESUMES].find_one({"user_id": user_id, "is_active": True})


# --- Achievement Journal (Feature 18) ---
# Kept in the resume module rather than a separate top-level module
# since it's a Resume-section nav item, not an independent domain.

async def create_achievement(db: AsyncIOMotorDatabase, user_id: str, data: dict) -> dict:
    now = datetime.now(timezone.utc)
    doc = {**data, "user_id": user_id, "created_at": now}
    result = await db[Collections.ACHIEVEMENTS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_achievements(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db[Collections.ACHIEVEMENTS].find({"user_id": user_id}).sort("created_at", -1)
    return await cursor.to_list(length=200)


async def delete_achievement(db: AsyncIOMotorDatabase, user_id: str, achievement_id: str) -> bool:
    from bson import ObjectId
    try:
        oid = ObjectId(achievement_id)
    except Exception:
        return False
    result = await db[Collections.ACHIEVEMENTS].delete_one({"_id": oid, "user_id": user_id})
    return result.deleted_count > 0
