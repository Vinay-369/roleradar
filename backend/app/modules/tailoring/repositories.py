from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections


async def create_version(
    db: AsyncIOMotorDatabase,
    user_id: str,
    job_id: str,
    job_title: str,
    company: str,
    changes: list[dict],
    sections_evaluated: list[str] | None = None,
    sections_changed: list[str] | None = None,
    unmatched_gaps: list[str] | None = None,
    parsed: dict | None = None,
    structured: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "job_id": job_id,
        "job_title": job_title,
        "company": company,
        "changes": changes,
        "sections_evaluated": sections_evaluated or [],
        "sections_changed": sections_changed or [],
        "unmatched_gaps": unmatched_gaps or [],
        "parsed": parsed or {},
        "structured": structured or {},
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


async def finalize_version(
    db: AsyncIOMotorDatabase,
    user_id: str,
    version_id: str,
    final_text: str,
    parsed: dict | None = None,
    audit: dict | None = None,
    changes: list[dict] | None = None,
    tailored_scores: dict | None = None,
    validation_summary: dict | None = None,
    one_page_fit: bool | None = None,
) -> dict | None:
    version = await get_version(db, user_id, version_id)
    if version is None:
        return None
    set_fields: dict[str, Any] = {"is_finalized": True, "final_text": final_text}
    if parsed is not None:
        set_fields["parsed"] = parsed
    if audit is not None:
        set_fields["audit"] = audit
    if changes is not None:
        set_fields["changes"] = changes
    if tailored_scores is not None:
        set_fields["tailored_scores"] = tailored_scores
    if validation_summary is not None:
        set_fields["validation_summary"] = validation_summary
    if one_page_fit is not None:
        set_fields["one_page_fit"] = one_page_fit
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]}, {"$set": set_fields}
    )
    return await get_version(db, user_id, version_id)


async def list_versions(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db[Collections.RESUME_VERSIONS].find({"user_id": user_id}).sort("created_at", -1)
    return await cursor.to_list(length=100)


async def delete_version(db: AsyncIOMotorDatabase, user_id: str, version_id: str) -> bool:
    try:
        oid = ObjectId(version_id)
    except Exception:
        return False
    res = await db[Collections.RESUME_VERSIONS].delete_one({"_id": oid, "user_id": user_id})
    return res.deleted_count > 0

