from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections

# Statuses that count as "still active" for duplicate-application checks.
# WITHDRAWN and REJECTED don't block a fresh application to the same job.
ACTIVE_STATUSES = ["SAVED", "TAILORED", "QUEUED", "APPLIED", "VIEWED", "INTERVIEW", "OFFER"]


async def find_active_application(db: AsyncIOMotorDatabase, user_id: str, job_id: str) -> dict | None:
    return await db[Collections.APPLICATIONS].find_one(
        {"user_id": user_id, "job_id": job_id, "status": {"$in": ACTIVE_STATUSES}}
    )


async def create_application(
    db: AsyncIOMotorDatabase,
    user_id: str,
    job_id: str,
    job_title: str,
    company: str,
    apply_url: str,
    tailored_resume_id: str | None,
    match_score_at_save: int | None,
    notes: str | None,
) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "job_id": job_id,
        "job_title": job_title,
        "company": company,
        "apply_url": apply_url,
        "tailored_resume_id": tailored_resume_id,
        "status": "TAILORED" if tailored_resume_id else "SAVED",
        "match_score_at_save": match_score_at_save,
        "notes": notes,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[Collections.APPLICATIONS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_applications(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db[Collections.APPLICATIONS].find({"user_id": user_id}).sort("created_at", -1)
    return await cursor.to_list(length=500)


async def get_application(db: AsyncIOMotorDatabase, user_id: str, application_id: str) -> dict | None:
    try:
        oid = ObjectId(application_id)
    except Exception:
        return None
    return await db[Collections.APPLICATIONS].find_one({"_id": oid, "user_id": user_id})


async def update_application(db: AsyncIOMotorDatabase, user_id: str, application_id: str, updates: dict) -> dict | None:
    app = await get_application(db, user_id, application_id)
    if app is None:
        return None
    updates["updated_at"] = datetime.now(timezone.utc)
    await db[Collections.APPLICATIONS].update_one({"_id": app["_id"]}, {"$set": updates})
    return await get_application(db, user_id, application_id)


async def delete_application(db: AsyncIOMotorDatabase, user_id: str, application_id: str) -> bool:
    try:
        oid = ObjectId(application_id)
    except Exception:
        return False
    result = await db[Collections.APPLICATIONS].delete_one({"_id": oid, "user_id": user_id})
    return result.deleted_count > 0
