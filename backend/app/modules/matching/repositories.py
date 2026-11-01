"""
Repository for caching job match scores in Collections.JOB_MATCHES.
Keyed by (user_id, job_id, resume_version).
"""
from datetime import datetime, timezone
import hashlib
import json
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.db.mongo import Collections


def job_match_fingerprint(job: dict) -> str:
    fields = (
        "title", "description", "jd_text", "structured_requirements", "jd_evidence_status",
        "skills_required", "experience_min", "experience_max", "location", "is_remote",
        "salary_min", "salary_max", "salary_disclosed", "stipend_min", "stipend_max",
        "job_type", "industry",
    )
    content = {key: job.get(key) for key in fields}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


async def get_cached_matches_for_jobs(
    db: AsyncIOMotorDatabase,
    user_id: str,
    resume_version: int,
    job_ids: list[str],
    expected_fingerprints: dict[str, str],
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
        job_id = doc["job_id"]
        if doc.get("job_fingerprint") == expected_fingerprints.get(job_id):
            results[job_id] = doc
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
    operations = []
    for m in matches_to_cache:
        doc = {
            "user_id": user_id,
            "job_id": m["job_id"],
            "resume_version": resume_version,
            "job_fingerprint": m["job_fingerprint"],
            "match_data": m["match_data"],
            "overall_score": m["match_data"].get("overall_score", 0),
            "updated_at": now,
        }
        operations.append(
            UpdateOne(
                {"user_id": user_id, "job_id": m["job_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        )

    try:
        await db[Collections.JOB_MATCHES].bulk_write(operations, ordered=False)
    except TypeError as exc:
        # Older mongomock/PyMongo combinations cannot consume newer UpdateOne
        # fields (for example ``sort``). Keep production bulk writes fast, but
        # make the repository compatible with test doubles and older clients.
        if "unexpected keyword argument" not in str(exc):
            raise
        collection = db[Collections.JOB_MATCHES]
        for operation in operations:
            await collection.update_one(
                operation._filter,
                operation._doc,
                upsert=operation._upsert,
            )


async def invalidate_user_matches(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """Clear stale cached matches when a new resume is uploaded or profile changes."""
    await db[Collections.JOB_MATCHES].delete_many({"user_id": user_id})
