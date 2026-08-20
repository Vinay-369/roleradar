"""
Repository for caching job match scores in Collections.JOB_MATCHES.
Keyed by (user_id, job_id, resume_version).
"""
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections


async def get_cached_matches_for_jobs(
    db: AsyncIOMotorDatabase,
    user_id: str,
    resume_version: int,
    job_ids: list[str],
) -> dict[str, dict]:
    """Returns a map of {job_id: match_doc} for all cached matches matching user_id & resume_version."""
    if not job_ids:
        return {}
    cursor = db[Collections.JOB_MATCHES].find({
        "user_id": user_id,
        "resume_version": resume_version,
        "job_id": {"$in": job_ids},
    })
    results = {}
    async for doc in cursor:
        results[doc["job_id"]] = doc
    return results


async def save_cached_matches(
    db: AsyncIOMotorDatabase,
    user_id: str,
    resume_version: int,
    matches_to_cache: list[dict],
) -> None:
    """Bulk upsert computed matches into Collections.JOB_MATCHES."""
    if not matches_to_cache:
        return
    now = datetime.now(timezone.utc)
    for m in matches_to_cache:
        doc = {
            "user_id": user_id,
            "job_id": m["job_id"],
            "resume_version": resume_version,
            "match_data": m["match_data"],
            "overall_score": m["match_data"].get("overall_score", 0),
            "updated_at": now,
        }
        await db[Collections.JOB_MATCHES].update_one(
            {"user_id": user_id, "job_id": m["job_id"]},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )


async def invalidate_user_matches(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """Clear stale cached matches when a new resume is uploaded or profile changes."""
    await db[Collections.JOB_MATCHES].delete_many({"user_id": user_id})
