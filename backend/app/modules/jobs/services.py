import json
import os
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.caching import get_cached_jd_requirements, set_cached_jd_requirements
from app.core.config import Settings, get_settings
from app.db.mongo import Collections
from app.modules.jobs import repositories as repo
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.taxonomy import RequirementCategory, StructuredJobRequirements, analyze_job_description

from datetime import datetime, timezone

from app.modules.jobs.deduplication import deduplicate_opportunities
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import (
    OpportunityLifecycleStatus,
    verify_opportunity_sync,
)

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "seeds", "jobs_seed.json")


async def ensure_seed_loaded(db: AsyncIOMotorDatabase) -> int:
    """Loads, verifies, deduplicates, and syncs the seed dataset into MongoDB. Idempotent — safe to call on every app startup."""
    seed_path = os.path.abspath(SEED_PATH)
    if not os.path.exists(seed_path):
        return 0

    with open(seed_path) as f:
        jobs = json.load(f)

    if not jobs:
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()
    processed_jobs = []
    for job in jobs:
        url_type, url_reason = classify_application_url(job.get("apply_url"), company=job.get("company"))
        job_copy = dict(job)
        job_copy["source"] = "curated_benchmark"
        job_copy["verification_status"] = OpportunityLifecycleStatus.MARKET_BENCHMARK.value
        job_copy["url_type"] = url_type.value
        job_copy["is_direct_apply"] = False
        job_copy["first_seen_at"] = now_iso
        job_copy["last_verified_at"] = now_iso
        job_copy["verified_at"] = now_iso
        job_copy["verification_reason"] = f"Curated catalog benchmark record: {url_reason}"
        job_copy["verification_method"] = "seed_catalog"
        if not job_copy.get("source_url"):
            job_copy["source_url"] = job_copy.get("apply_url")
        processed_jobs.append(job_copy)

    deduped = deduplicate_opportunities(processed_jobs)
    await repo.upsert_jobs(db, deduped)
    return len(deduped)


async def search_jobs(db: AsyncIOMotorDatabase, filters: dict, user_id: str | None = None) -> list[dict]:
    search_filters = dict(filters)
    if user_id:
        search_filters["user_id"] = user_id
    provider = CuratedJobProvider(db)
    return await provider.search(search_filters)


async def sync_all_greenhouse_boards(db: AsyncIOMotorDatabase, settings: Settings | None = None) -> dict:
    """Synchronizes all configured Greenhouse company boards into MongoDB."""
    active_settings = settings or get_settings()
    if not getattr(active_settings, "GREENHOUSE_ENABLED", True):
        return {"total_boards": 0, "verified_active": 0, "closed": 0, "results": []}

    from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
    provider = GreenhouseJobProvider(active_settings)

    raw_boards = getattr(active_settings, "GREENHOUSE_COMPANIES", "postman,inmobi,groww")
    boards = [b.strip() for b in raw_boards.split(",") if b.strip()]

    results = []
    total_active = 0
    total_closed = 0

    for b in boards:
        res = await provider.sync_company_openings(db, b)
        results.append(res)
        total_active += res.get("verified_active", 0)
        total_closed += res.get("closed", 0)

    return {
        "total_boards": len(boards),
        "verified_active": total_active,
        "closed": total_closed,
        "results": results,
    }


async def sync_greenhouse_board(
    db: AsyncIOMotorDatabase,
    board_token: str,
    company_name: str | None = None,
    settings: Settings | None = None,
) -> dict:
    """Synchronizes a single Greenhouse board token."""
    from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
    provider = GreenhouseJobProvider(settings or get_settings())
    return await provider.sync_company_openings(db, board_token, company_name=company_name)


async def sync_lever_board(
    db: AsyncIOMotorDatabase,
    board_token: str,
    company_name: str | None = None,
    settings: Settings | None = None,
) -> dict:
    """Synchronizes a single Lever board token."""
    from app.modules.jobs.lever_provider import LeverJobProvider
    provider = LeverJobProvider(settings or get_settings())
    return await provider.sync_company_openings(db, board_token, company_name=company_name)


async def sync_all_lever_boards(db: AsyncIOMotorDatabase, settings: Settings | None = None) -> dict:
    """Synchronizes all configured Lever company boards into MongoDB."""
    active_settings = settings or get_settings()
    if not getattr(active_settings, "LEVER_ENABLED", False):
        return {"total_boards": 0, "verified_active": 0, "closed": 0, "results": []}

    from app.modules.jobs.lever_provider import LeverJobProvider
    provider = LeverJobProvider(active_settings)

    raw_boards = getattr(active_settings, "LEVER_COMPANIES", "paytm,meesho,cred,fi")
    boards = [b.strip() for b in raw_boards.split(",") if b.strip()]

    results = []
    total_active = 0
    total_closed = 0

    for b in boards:
        res = await provider.sync_company_openings(db, b)
        results.append(res)
        total_active += res.get("verified_active", 0)
        total_closed += res.get("closed", 0)

    return {
        "total_boards": len(boards),
        "verified_active": total_active,
        "closed": total_closed,
        "results": results,
    }


async def sync_smartrecruiters_board(
    db: AsyncIOMotorDatabase,
    board_token: str,
    company_name: str | None = None,
    country: str | None = None,
    settings: Settings | None = None,
) -> dict:
    """Synchronizes a single SmartRecruiters board token."""
    from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider
    provider = SmartRecruitersJobProvider(settings or get_settings())
    return await provider.sync_company_openings(db, board_token, company_name=company_name, country=country)


async def sync_all_smartrecruiters_boards(db: AsyncIOMotorDatabase, settings: Settings | None = None) -> dict:
    """Synchronizes all configured SmartRecruiters company boards into MongoDB."""
    active_settings = settings or get_settings()
    if not getattr(active_settings, "SMARTRECRUITERS_ENABLED", False):
        return {"total_boards": 0, "verified_active": 0, "closed": 0, "results": []}

    from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider
    provider = SmartRecruitersJobProvider(active_settings)

    raw_boards = getattr(active_settings, "SMARTRECRUITERS_COMPANIES", "BoschGroup,Sandisk,AveryDennison,BlueberryLabsPrivateLimited,Ubisoft2")
    boards = [b.strip() for b in raw_boards.split(",") if b.strip()]

    results = []
    total_active = 0
    total_closed = 0

    for b in boards:
        res = await provider.sync_company_openings(db, b)
        results.append(res)
        total_active += res.get("verified_active", 0)
        total_closed += res.get("closed", 0)

    return {
        "total_boards": len(boards),
        "verified_active": total_active,
        "closed": total_closed,
        "results": results,
    }


async def refresh_live_jobs(db: AsyncIOMotorDatabase, settings: Settings, filters: dict) -> int:
    """
    Refreshes opportunities from active live providers:
    1. Greenhouse Direct ATS Provider (if enabled).
    2. Lever Direct ATS Provider (if enabled).
    3. SmartRecruiters Direct ATS Provider (if enabled).
    4. Adzuna Provider (if configured in hybrid mode).
    Normalizes, verifies, deduplicates, and upserts into MongoDB.
    """
    added_count = 0

    # 1. Greenhouse Direct ATS Provider
    if getattr(settings, "GREENHOUSE_ENABLED", False):
        try:
            gh_res = await sync_all_greenhouse_boards(db, settings)
            added_count += gh_res.get("verified_active", 0)
        except Exception:
            pass

    # 2. Lever Direct ATS Provider
    if getattr(settings, "LEVER_ENABLED", False):
        try:
            lever_res = await sync_all_lever_boards(db, settings)
            added_count += lever_res.get("verified_active", 0)
        except Exception:
            pass

    # 3. SmartRecruiters Direct ATS Provider
    if getattr(settings, "SMARTRECRUITERS_ENABLED", False):
        try:
            sr_res = await sync_all_smartrecruiters_boards(db, settings)
            added_count += sr_res.get("verified_active", 0)
        except Exception:
            pass

    # 4. Adzuna Provider (if configured in hybrid mode)
    if settings.JOB_SOURCE_MODE == "hybrid":
        from app.modules.jobs.live_provider import AdzunaConfigError, AdzunaJobProvider
        try:
            provider = AdzunaJobProvider(settings)
            live_jobs = await provider.search(filters)
            if live_jobs:
                verified_live_jobs = []
                for job in live_jobs:
                    vres = verify_opportunity_sync(job)
                    job_copy = dict(job)
                    job_copy["verification_status"] = vres.status.value
                    job_copy["verified_at"] = vres.verified_at
                    job_copy["verification_reason"] = vres.reason
                    job_copy["verification_method"] = "live_provider_verified"
                    if vres.status == OpportunityLifecycleStatus.VERIFIED_ACTIVE:
                        verified_live_jobs.append(job_copy)

                if verified_live_jobs:
                    deduped = deduplicate_opportunities(verified_live_jobs)
                    await repo.upsert_jobs(db, deduped)
                    added_count += len(deduped)
        except AdzunaConfigError:
            pass

    return added_count


async def reverify_active_opportunities(db: AsyncIOMotorDatabase, now: datetime | None = None) -> dict:
    """
    Re-verifies existing opportunities in MongoDB.
    Transitions stale/closed/expired/invalid listings out of VERIFIED_ACTIVE.
    Preserves historical records internally with updated status.
    """
    cursor = db[Collections.JOBS].find({})
    all_jobs = await cursor.to_list(length=2000)

    stats = {
        "checked": len(all_jobs),
        "retained_active": 0,
        "transitioned_closed": 0,
        "transitioned_expired": 0,
        "transitioned_stale": 0,
        "transitioned_invalid": 0,
    }

    for job in all_jobs:
        prev_status = job.get("verification_status", OpportunityLifecycleStatus.VERIFIED_ACTIVE.value)
        vres = verify_opportunity_sync(job, now=now)
        new_status = vres.status.value

        update_fields = {
            "verification_status": new_status,
            "verified_at": vres.verified_at,
            "last_verified_at": vres.verified_at,
            "verification_reason": vres.reason,
            "verification_method": "reverification_audit",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type == ApplicationUrlType.DIRECT_REQUISITION and new_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value),
        }

        if new_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value:
            stats["retained_active"] += 1
        elif new_status == OpportunityLifecycleStatus.CLOSED.value:
            stats["transitioned_closed"] += 1
        elif new_status == OpportunityLifecycleStatus.EXPIRED.value:
            stats["transitioned_expired"] += 1
        elif new_status == OpportunityLifecycleStatus.STALE.value:
            stats["transitioned_stale"] += 1
        elif new_status == OpportunityLifecycleStatus.INVALID.value:
            stats["transitioned_invalid"] += 1

        await db[Collections.JOBS].update_one({"id": job["id"]}, {"$set": update_fields})

    return stats


async def get_job(db: AsyncIOMotorDatabase, job_id: str, user_id: str | None = None) -> dict | None:
    job = await repo.get_job_by_id(db, job_id)
    if job is None:
        return None
    # User-scoping for custom JDs
    if job.get("source") == "custom" and job.get("user_id"):
        if user_id and job.get("user_id") != user_id:
            return None

    posted_at = job.get("posted_at") or job.get("first_seen_at")
    if posted_at:
        try:
            p_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            job["posted_days_ago"] = max(0, (datetime.now(timezone.utc) - p_dt).days)
        except (ValueError, TypeError):
            pass

    return job


async def get_canonical_job_requirements(db: AsyncIOMotorDatabase, job: dict) -> StructuredJobRequirements:
    """
    Canonical JD Intelligence Accessor.
    Resolves authoritative StructuredJobRequirements from:
    1. Pre-stored structured_requirements dictionary if present
    2. Cached in-memory taxonomy analysis
    3. Fresh analyze_job_description(jd_text, title) with lazy caching
    """
    # 1. Direct structured_requirements in document
    if job.get("structured_requirements") and isinstance(job["structured_requirements"], dict):
        try:
            return StructuredJobRequirements(**job["structured_requirements"])
        except Exception:
            pass

    jd_text = job.get("jd_text") or job.get("description") or ""
    title = job.get("title") or ""

    # 2. Check in-memory cache
    cached = get_cached_jd_requirements(jd_text, title)
    if cached is not None:
        return cached

    # 3. Analyze raw JD text through Phase 3 generalized taxonomy
    reqs = analyze_job_description(jd_text, title)
    set_cached_jd_requirements(jd_text, title, reqs)

    # Lazily update MongoDB job document if it has an id
    if job.get("id") and not job.get("structured_requirements"):
        try:
            await db[Collections.JOBS].update_one(
                {"id": job["id"]},
                {"$set": {"structured_requirements": reqs.model_dump(mode="json")}}
            )
        except Exception:
            pass

    return reqs


async def create_custom_job(
    db: AsyncIOMotorDatabase,
    company: str,
    title: str,
    jd_text: str,
    user_id: str | None = None,
) -> dict:
    """
    Canonical Opportunity Factory for User-Pasted External JDs.
    Runs full Phase 3 generalized semantic analysis (analyze_job_description).
    Zero arbitrary skill slicing, complete responsibilities preservation,
    and user-scoped isolation.
    """
    # 1. Canonical JD Analysis
    reqs = analyze_job_description(jd_text, title)

    # 2. Extract structured fields
    resolved_title = reqs.target_role or title or "Target Role"
    resolved_company = reqs.company or company or "Custom Application"
    resolved_location = reqs.location or "Not specified"
    resolved_work_mode = reqs.work_mode
    is_remote = (resolved_work_mode == "Remote") or ("remote" in resolved_location.lower())

    resp_list = [
        r.text for r in reqs.requirements
        if r.category == RequirementCategory.RESPONSIBILITY
    ]
    if not resp_list and reqs.responsibilities:
        resp_list = list(reqs.responsibilities)

    exp_min = int(reqs.min_years_experience) if reqs.min_years_experience is not None else 0
    exp_max = int(reqs.max_years_experience) if reqs.max_years_experience is not None else (exp_min + 3 if exp_min > 0 else 5)

    is_intern = (
        (reqs.employment_type and "intern" in reqs.employment_type.lower())
        or ("intern" in resolved_title.lower())
    )

    must_have_skills = list(reqs.must_have_skills)
    preferred_skills = list(reqs.preferred_skills)

    # If the JD had no explicit requirement headings (e.g. single-paragraph or informal JD),
    # fallback to detected technologies, keywords, or vocabulary extraction so skills are preserved
    if not must_have_skills and not preferred_skills:
        fallback = reqs.technologies or reqs.required_skills or extract_skills_from_text(jd_text)
        must_have_skills = list(fallback)

    job = {
        "id": f"custom_{uuid.uuid4().hex[:10]}",
        "user_id": user_id,  # User-scoped ownership for privacy & isolation
        "source": "custom",
        "title": resolved_title,
        "company": resolved_company,
        "industry": reqs.domain or "Technology",
        "description": jd_text,
        "jd_text": jd_text,
        # Canonical Phase 3 fields
        "must_have_skills": must_have_skills,
        "preferred_skills": preferred_skills,
        "seniority": reqs.seniority,
        "domain": reqs.domain,
        "min_years_experience": reqs.min_years_experience,
        "max_years_experience": reqs.max_years_experience,
        "company_overview": reqs.company_overview,
        "role_overview": reqs.role_overview,
        "structured_requirements": reqs.model_dump(mode="json"),
        # Backward-compatibility projection fields for discovery / legacy queries
        "skills_required": list(must_have_skills),
        "skills_nice_to_have": list(preferred_skills),
        "responsibilities": resp_list,
        "experience_min": exp_min,
        "experience_max": exp_max,
        "job_type": "internship" if is_intern else "full_time",
        "location": resolved_location,
        "is_remote": is_remote,
        "salary_min": None,
        "salary_max": None,
        "salary_disclosed": False,
        "stipend_min": None,
        "internship_duration_months": None,
        "fresher_friendly": exp_min == 0,
        "posted_days_ago": 0,
        "apply_url": "",
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "url_type": ApplicationUrlType.DIRECT_REQUISITION.value,
        "is_direct_apply": True,
        "verification_reason": "User-created private custom opportunity",
        "verification_method": "custom_creation",
    }

    # Persist and cache canonical analysis
    await db[Collections.JOBS].insert_one(job)
    set_cached_jd_requirements(jd_text, resolved_title, reqs)
    return job
