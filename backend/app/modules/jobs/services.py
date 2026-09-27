import asyncio
import json
import logging
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
logger = logging.getLogger("roleradar.jobs.sync")


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


async def count_jobs(db: AsyncIOMotorDatabase, filters: dict, user_id: str | None = None) -> int:
    search_filters = dict(filters)
    if user_id:
        search_filters["user_id"] = user_id
    provider = CuratedJobProvider(db)
    return await provider.count(search_filters)


def _configured_board_tokens(settings: Settings, attribute: str) -> list[str]:
    configured = getattr(settings, attribute, "")
    if isinstance(configured, str):
        tokens = configured.split(",")
    elif isinstance(configured, (list, tuple, set)):
        tokens = configured
    else:
        return []
    return list(dict.fromkeys(token.strip() for token in tokens if isinstance(token, str) and token.strip()))


async def _sync_configured_boards(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    provider_class: type,
    companies_attribute: str,
    enabled_attribute: str,
    country: str | None = None,
) -> dict:
    boards = _configured_board_tokens(settings, companies_attribute)
    summary = {"total_boards": len(boards), "fetched": 0, "verified_active": 0, "closed": 0, "internships": 0, "errors": [], "results": []}
    if not getattr(settings, enabled_attribute, False) or not boards:
        return summary

    provider = provider_class(settings)
    semaphore = asyncio.Semaphore(5)

    async def sync_board(board: str):
        async with semaphore:
            try:
                kwargs = {"country": country} if country else {}
                return await provider.sync_company_openings(db, board, **kwargs)
            except Exception as exc:
                logger.warning("Provider sync failed for configured board %s: %s", board, exc)
                return {"board": board, "errors": [str(exc)]}

    results = await asyncio.gather(*(sync_board(board) for board in boards))
    summary["results"] = results
    for result in results:
        for key in ("fetched", "verified_active", "closed", "internships"):
            summary[key] += int(result.get(key) or 0)
        summary["errors"].extend(result.get("errors") or [])
        if result.get("error"):
            summary["errors"].append(result["error"])
        if result.get("network_error"):
            summary["errors"].append(f"{result.get('board')}: network error")
    return summary


<<<<<<< HEAD
async def sync_all_ashby_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
=======
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
    country_filter = getattr(active_settings, "SMARTRECRUITERS_COUNTRY", "in")
    for b in boards:
        res = await provider.sync_company_openings(db, b, country=country_filter)
        results.append(res)
        total_active += res.get("verified_active", 0)
        total_closed += res.get("closed", 0)

    return {
        "total_boards": len(boards),
        "verified_active": total_active,
        "closed": total_closed,
        "results": results,
    }


async def sync_ashby_board(
    db: AsyncIOMotorDatabase,
    board_token: str,
    company_name: str | None = None,
    settings: Settings | None = None,
) -> dict:
    """Synchronizes a single Ashby board token."""
>>>>>>> 70804571dc73c928037d4e20acf18351cd6a9b18
    from app.modules.jobs.ashby_provider import AshbyJobProvider
    return await _sync_configured_boards(db, settings, AshbyJobProvider, "ASHBY_COMPANIES", "ASHBY_ENABLED")


async def sync_all_greenhouse_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
    return await _sync_configured_boards(db, settings, GreenhouseJobProvider, "GREENHOUSE_COMPANIES", "GREENHOUSE_ENABLED")


async def sync_all_lever_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    from app.modules.jobs.lever_provider import LeverJobProvider
    return await _sync_configured_boards(db, settings, LeverJobProvider, "LEVER_COMPANIES", "LEVER_ENABLED")


<<<<<<< HEAD
async def sync_all_smartrecruiters_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider
    return await _sync_configured_boards(
        db,
        settings,
        SmartRecruitersJobProvider,
        "SMARTRECRUITERS_COMPANIES",
        "SMARTRECRUITERS_ENABLED",
        country=getattr(settings, "SMARTRECRUITERS_COUNTRY", None),
    )
=======
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
>>>>>>> 70804571dc73c928037d4e20acf18351cd6a9b18


async def refresh_live_jobs(db: AsyncIOMotorDatabase, settings: Settings, filters: dict) -> int:
    """Synchronize only explicitly configured, direct employer ATS boards."""
    if getattr(settings, "JOB_SOURCE_MODE", "curated") != "direct_ats":
        return 0

    sync_results = await asyncio.gather(
        sync_all_ashby_boards(db, settings),
        sync_all_greenhouse_boards(db, settings),
        sync_all_lever_boards(db, settings),
        sync_all_smartrecruiters_boards(db, settings),
    )
    return sum(result["verified_active"] for result in sync_results)


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
        source = job.get("source")
        is_aggregator = source in ("adzuna", "jooble", "remotive", "arbeitnow", "jsearch")
        vres = verify_opportunity_sync(job, now=now, enforce_direct_apply=not is_aggregator)
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
        if not user_id or job.get("user_id") != user_id:
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
            sr = StructuredJobRequirements(**job["structured_requirements"])
            # If experience bounds were not extracted previously, re-evaluate to catch explicit requirements
            if sr.min_years_experience is None and sr.max_years_experience is None:
                jd_text = job.get("jd_text") or job.get("description") or ""
                fresh = analyze_job_description(jd_text, job.get("title") or "")
                if fresh.min_years_experience is not None or fresh.max_years_experience is not None:
                    sr.min_years_experience = fresh.min_years_experience
                    sr.max_years_experience = fresh.max_years_experience
                    sr.experience_requirements = fresh.experience_requirements
                    if job.get("id"):
                        try:
                            update_dict = {"structured_requirements": sr.model_dump(mode="json")}
                            if sr.min_years_experience is not None:
                                update_dict["experience_min"] = int(sr.min_years_experience)
                                job["experience_min"] = int(sr.min_years_experience)
                            if sr.max_years_experience is not None:
                                update_dict["experience_max"] = int(sr.max_years_experience)
                                job["experience_max"] = int(sr.max_years_experience)
                            await db[Collections.JOBS].update_one({"id": job["id"]}, {"$set": update_dict})
                        except Exception:
                            pass
            if sr.must_have_skills or sr.required_skills or sr.responsibilities:
                return sr
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
    if job.get("id"):
        try:
            update_dict = {"structured_requirements": reqs.model_dump(mode="json")}
            if reqs.min_years_experience is not None and job.get("experience_min") is None:
                update_dict["experience_min"] = int(reqs.min_years_experience)
                job["experience_min"] = int(reqs.min_years_experience)
            if reqs.max_years_experience is not None and job.get("experience_max") is None:
                update_dict["experience_max"] = int(reqs.max_years_experience)
                job["experience_max"] = int(reqs.max_years_experience)
            await db[Collections.JOBS].update_one(
                {"id": job["id"]},
                {"$set": update_dict}
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
        "apply_url": "",
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "url_type": ApplicationUrlType.UNVERIFIED.value,
        "is_direct_apply": False,
        "verification_reason": "User-created private custom opportunity",
        "verification_method": "custom_creation",
    }

    # Persist and cache canonical analysis
    await db[Collections.JOBS].insert_one(job)
    set_cached_jd_requirements(jd_text, resolved_title, reqs)
    return job
