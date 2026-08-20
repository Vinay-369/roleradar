from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections


async def create_version(db: AsyncIOMotorDatabase, user_id: str, job_id: str, job_title: str, company: str, changes: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "job_id": job_id,
        "job_title": job_title,
        "company": company,
        "changes": changes,
        "is_finalized": False,
        "final_text": None,
        "created_at": now,
    }
    result = await db[Collections.RESUME_VERSIONS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_version(db: AsyncIOMotorDatabase, user_id: str, version_id: str) -> dict | None:
    try:
        oid = ObjectId(version_id)
    except Exception:
        return None
    return await db[Collections.RESUME_VERSIONS].find_one({"_id": oid, "user_id": user_id})


async def update_change_status(db: AsyncIOMotorDatabase, user_id: str, version_id: str, change_id: str, status: str) -> dict | None:
    version = await get_version(db, user_id, version_id)
    if version is None:
        return None
    for change in version["changes"]:
        if change["change_id"] == change_id:
            change["status"] = status
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]}, {"$set": {"changes": version["changes"]}}
    )
    return await get_version(db, user_id, version_id)


async def finalize_version(db: AsyncIOMotorDatabase, user_id: str, version_id: str, final_text: str) -> dict | None:
    version = await get_version(db, user_id, version_id)
    if version is None:
        return None
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]}, {"$set": {"is_finalized": True, "final_text": final_text}}
    )
    return await get_version(db, user_id, version_id)


async def list_versions(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db[Collections.RESUME_VERSIONS].find({"user_id": user_id}).sort("created_at", -1)
    return await cursor.to_list(length=100)
