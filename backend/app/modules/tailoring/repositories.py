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
    candidate_classification: dict | None = None,
    resume_strategy: dict | None = None,
    evidence_mapping: list[dict] | None = None,
    matched_skills: list[str] | None = None,
    missing_skills: list[str] | None = None,
    partial_skills: list[str] | None = None,
    ats_readability_findings: dict | None = None,
    master_resume_id: str | None = None,
    master_resume_version: int | None = None,
    opportunity_type: str | None = None,
    opportunity_id: str | None = None,
    jd_analysis_summary: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    
    # Query if an existing version already exists for this job or company
    query: dict[str, Any] = {"user_id": user_id}
    if job_id and not job_id.startswith("custom-"):
        query["job_id"] = job_id
    else:
        query["company"] = company
        query["job_title"] = job_title

    existing = await db[Collections.RESUME_VERSIONS].find_one(query)

    doc_fields = {
        "user_id": user_id,
        "job_id": job_id,
        "job_title": job_title,
        "company": company,
        "master_resume_id": master_resume_id,
        "master_resume_version": master_resume_version,
        "opportunity_type": opportunity_type or ("INTERNSHIP" if "intern" in (job_id or "").lower() else "JOB"),
        "opportunity_id": opportunity_id or job_id,
        "jd_analysis_summary": jd_analysis_summary,
        "changes": changes,
        "sections_evaluated": sections_evaluated or [],
        "sections_changed": sections_changed or [],
        "unmatched_gaps": unmatched_gaps or [],
        "parsed": parsed or {},
        "structured": structured or {},
        "candidate_classification": candidate_classification,
        "resume_strategy": resume_strategy,
        "evidence_mapping": evidence_mapping,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "partial_skills": partial_skills,
        "ats_readability_findings": ats_readability_findings,
        "is_finalized": False,
        "final_text": None,
        "updated_at": now,
    }

    if existing:
        doc_fields["created_at"] = existing.get("created_at", now)
        await db[Collections.RESUME_VERSIONS].update_one({"_id": existing["_id"]}, {"$set": doc_fields})
        doc_fields["_id"] = existing["_id"]
        # Clean up any duplicate legacy documents for the exact same job/company
        await db[Collections.RESUME_VERSIONS].delete_many({
            "user_id": user_id,
            "_id": {"$ne": existing["_id"]},
            **({"job_id": job_id} if (job_id and not job_id.startswith("custom-")) else {"company": company, "job_title": job_title}),
        })
        return doc_fields
    else:
        doc_fields["created_at"] = now
        result = await db[Collections.RESUME_VERSIONS].insert_one(doc_fields)
        doc_fields["_id"] = result.inserted_id
        return doc_fields


async def get_version_by_job(db: AsyncIOMotorDatabase, user_id: str, job_id: str) -> dict | None:
    return await db[Collections.RESUME_VERSIONS].find_one(
        {"user_id": user_id, "job_id": job_id},
        sort=[("created_at", -1)],
    )


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


async def update_parsed_resume(
    db: AsyncIOMotorDatabase,
    user_id: str,
    version_id: str,
    parsed: dict,
    user_modified: bool = True,
    truth_guard_audit: dict | None = None,
    ats_readability_findings: dict | None = None,
    verification_status: str | None = None,
) -> dict | None:
    version = await get_version(db, user_id, version_id)
    if version is None:
        return None
    set_fields: dict[str, Any] = {
        "parsed": parsed,
        "user_modified": user_modified,
    }
    if truth_guard_audit is not None:
        set_fields["truth_guard_audit"] = truth_guard_audit
    if ats_readability_findings is not None:
        set_fields["ats_readability_findings"] = ats_readability_findings
    if verification_status is not None:
        set_fields["verification_status"] = verification_status

    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]}, {"$set": set_fields}
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
    candidate_classification: dict | None = None,
    resume_strategy: dict | None = None,
    evidence_mapping: list[dict] | None = None,
    matched_skills: list[str] | None = None,
    missing_skills: list[str] | None = None,
    partial_skills: list[str] | None = None,
    ats_readability_findings: dict | None = None,
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
    if candidate_classification is not None:
        set_fields["candidate_classification"] = candidate_classification
    if resume_strategy is not None:
        set_fields["resume_strategy"] = resume_strategy
    if evidence_mapping is not None:
        set_fields["evidence_mapping"] = evidence_mapping
    if matched_skills is not None:
        set_fields["matched_skills"] = matched_skills
    if missing_skills is not None:
        set_fields["missing_skills"] = missing_skills
    if partial_skills is not None:
        set_fields["partial_skills"] = partial_skills
    if ats_readability_findings is not None:
        set_fields["ats_readability_findings"] = ats_readability_findings
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]}, {"$set": set_fields}
    )
    return await get_version(db, user_id, version_id)


async def list_versions(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db[Collections.RESUME_VERSIONS].find({"user_id": user_id}).sort("created_at", -1)
    all_versions = await cursor.to_list(length=200)
    seen_keys = set()
    deduped = []
    for v in all_versions:
        # Key by job_id if present and not custom, else by normalized company + job_title
        j_id = v.get("job_id")
        if j_id and not j_id.startswith("custom-"):
            key = f"job_{j_id}"
        else:
            comp = str(v.get("company", "")).strip().lower()
            role = str(v.get("job_title", "")).strip().lower()
            key = f"comp_{comp}_{role}"
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(v)
    return deduped


async def delete_version(db: AsyncIOMotorDatabase, user_id: str, version_id: str) -> bool:
    try:
        oid = ObjectId(version_id)
    except Exception:
        return False
    res = await db[Collections.RESUME_VERSIONS].delete_one({"_id": oid, "user_id": user_id})
    return res.deleted_count > 0

