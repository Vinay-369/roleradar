from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs import services
from app.modules.jobs.schemas import JobOut
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo

router = APIRouter()


def _strip_for_list(job: dict) -> dict:
    """Lighter payload for the list view — full description/responsibilities
    aren't needed until someone opens the detail view."""
    from app.modules.jobs.location_normalization import extract_country_from_location
    job = {**job}
    job.pop("_id", None)
    job.pop("jd_text", None)
    job.pop("responsibilities", None)
    job.setdefault("url_type", "UNVERIFIED")
    job.setdefault("is_direct_apply", job.get("url_type") == "DIRECT_REQUISITION")
    job.setdefault("verification_status", "VERIFIED_ACTIVE")
    job.setdefault("country", extract_country_from_location(job.get("location")))
    return job


def _strip_for_detail(job: dict) -> dict:
    """Full payload for the job detail view — keeps responsibilities."""
    from app.modules.jobs.location_normalization import extract_country_from_location
    job = {**job}
    job.pop("_id", None)
    job.pop("jd_text", None)
    job.setdefault("responsibilities", [])
    job.setdefault("url_type", "UNVERIFIED")
    job.setdefault("is_direct_apply", job.get("url_type") == "DIRECT_REQUISITION")
    job.setdefault("verification_status", "VERIFIED_ACTIVE")
    job.setdefault("country", extract_country_from_location(job.get("location")))
    return job


@router.get("", response_model=list[JobOut])
async def list_jobs(
    job_type: str | None = None,
    location: str | None = None,
    remote_only: bool = False,
    min_lpa: float | None = None,
    fresher_friendly_only: bool = False,
    skill: str | None = None,
    region: str | None = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    filters = {
        "job_type": job_type,
        "location": location,
        "remote_only": remote_only,
        "min_lpa": min_lpa,
        "fresher_friendly_only": fresher_friendly_only,
        "skill": skill,
        "limit": 500,
        "active_discovery_only": True,
        "direct_apply_only": True,
    }

    # Build a personalized live-fetch query from the candidate's own
    # data instead of an empty/generic search -- this is what makes
    # live results actually relevant to this specific person rather
    # than just "whatever Adzuna returns with no keywords".
    live_filters = dict(filters)
    if not skill:
        resume = await resume_repo.get_active_master_resume(db, str(current_user["_id"]))
        profile = await profile_repo.get_profile(db, str(current_user["_id"]))
        skills_from_resume = resume["parsed"].get("skills", []) if resume else []
        roles_from_profile = profile.get("target_roles", []) if profile else []
        live_filters["skills"] = (skills_from_resume[:6] + roles_from_profile[:2]) or None
        if not location and profile and profile.get("preferred_locations"):
            live_filters["location"] = profile["preferred_locations"][0]

    # Best-effort: if a live source is configured, refresh before
    # searching so real listings are included. Never blocks or fails
    # the request if the live source is unavailable or unconfigured.
    await services.refresh_live_jobs(db, settings, live_filters)

    jobs = await services.search_jobs(db, filters, user_id=str(current_user["_id"]))

    from app.modules.jobs.location_normalization import is_india_opportunity

    def _is_india_job(j: dict) -> bool:
        return j.get("country") == "India" or is_india_opportunity(j.get("location"))

    if isinstance(region, str) and region.lower() in ("india", "in"):
        jobs = [j for j in jobs if _is_india_job(j)]

    jobs.sort(key=lambda j: (0 if _is_india_job(j) else 1, j.get("posted_days_ago", 0)))
    return [JobOut(**_strip_for_list(j)) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    job = await services.get_job(db, job_id, user_id=str(current_user["_id"]))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobOut(**_strip_for_detail(job))
