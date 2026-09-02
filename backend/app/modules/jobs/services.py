import json
import os
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.caching import get_cached_jd_requirements, set_cached_jd_requirements
from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.jobs import repositories as repo
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.taxonomy import RequirementCategory, StructuredJobRequirements, analyze_job_description

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "seeds", "jobs_seed.json")


async def ensure_seed_loaded(db: AsyncIOMotorDatabase) -> int:
    """Loads and syncs the seed dataset into MongoDB. Idempotent — safe to call on every app startup."""
    seed_path = os.path.abspath(SEED_PATH)
    if not os.path.exists(seed_path):
        return 0

    with open(seed_path) as f:
        jobs = json.load(f)

    if jobs:
        await repo.upsert_jobs(db, jobs)
    return len(jobs)


async def search_jobs(db: AsyncIOMotorDatabase, filters: dict, user_id: str | None = None) -> list[dict]:
    search_filters = dict(filters)
    if user_id:
        search_filters["user_id"] = user_id
    provider = CuratedJobProvider(db)
    return await provider.search(search_filters)


async def refresh_live_jobs(db: AsyncIOMotorDatabase, settings: Settings, filters: dict) -> int:
    """
    Fetches from Adzuna (if configured) and upserts results into the
    jobs collection so they show up in normal searches alongside
    curated data.
    """
    if settings.JOB_SOURCE_MODE != "hybrid":
        return 0

    from app.modules.jobs.live_provider import AdzunaConfigError, AdzunaJobProvider

    try:
        provider = AdzunaJobProvider(settings)
    except AdzunaConfigError:
        return 0

    live_jobs = await provider.search(filters)
    if live_jobs:
        await repo.upsert_jobs(db, live_jobs)
    return len(live_jobs)


async def get_job(db: AsyncIOMotorDatabase, job_id: str, user_id: str | None = None) -> dict | None:
    job = await repo.get_job_by_id(db, job_id)
    if job is None:
        return None
    # User-scoping for custom JDs
    if job.get("source") == "custom" and job.get("user_id"):
        if user_id and job.get("user_id") != user_id:
            return None
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
    }

    # Persist and cache canonical analysis
    await db[Collections.JOBS].insert_one(job)
    set_cached_jd_requirements(jd_text, resolved_title, reqs)
    return job
