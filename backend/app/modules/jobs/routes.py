from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs import services
from app.modules.jobs.schemas import JobOut, CreateCustomJobRequest
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

    # Opportunity discovery queries persisted MongoDB opportunities directly without
    # blocking on external ATS synchronizations (decoupled in Phase 16C).
    jobs = await services.search_jobs(db, filters, user_id=str(current_user["_id"]))

    from app.modules.jobs.location_normalization import is_india_opportunity

    def _is_india_job(j: dict) -> bool:
        return j.get("country") == "India" or is_india_opportunity(j.get("location"))

    if isinstance(region, str) and region.lower() in ("india", "in"):
        jobs = [j for j in jobs if _is_india_job(j)]

    jobs.sort(key=lambda j: (0 if _is_india_job(j) else 1, j.get("posted_days_ago", 0)))
    return [JobOut(**_strip_for_list(j)) for j in jobs]


@router.post("/sync")
async def sync_live_jobs(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Explicit background/on-demand synchronization of active live opportunities
    from ATS providers (Greenhouse, Lever, SmartRecruiters, Adzuna). Decoupled from user read requests.
    """
    added_count = await services.refresh_live_jobs(db, settings, {})
    return {"status": "success", "added_count": added_count}



@router.post("/custom", response_model=JobOut)
async def create_custom_job_endpoint(
    payload: CreateCustomJobRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not payload.jd_text or not payload.jd_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job description text is required.",
        )
    job = await services.create_custom_job(
        db,
        company=payload.company or "",
        title=payload.title or "",
        jd_text=payload.jd_text,
        user_id=str(current_user["_id"]),
    )
    return JobOut(**_strip_for_detail(job))


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
