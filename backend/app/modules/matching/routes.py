from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs import services as jobs_services
from app.modules.matching import services as matching_services
from app.modules.matching.schemas import JobMatchOut
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo

router = APIRouter()


@router.get("/recommended", response_model=list[JobMatchOut])
async def recommended_matches(
    job_type: str | None = Query(default=None, description="full_time | internship"),
    live_only: bool = Query(default=False, description="Return only live postings with direct apply links"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user_id = str(current_user["_id"])
    profile = await profile_repo.get_profile(db, user_id)
    resume = await resume_repo.get_active_master_resume(db, user_id)

    if profile is None or resume is None:
        return []

    # Refresh live jobs if configured
    live_filters = {
        "job_type": job_type,
        "skills": (resume["parsed"].get("skills", [])[:6] + profile.get("target_roles", [])[:2]) or None,
        "location": profile.get("preferred_locations", [None])[0] if profile.get("preferred_locations") else None,
    }
    await jobs_services.refresh_live_jobs(db, settings, live_filters)

    search_filters: dict = {}
    if job_type:
        search_filters["job_type"] = job_type
    if live_only:
        search_filters["source"] = "live"

    jobs = await jobs_services.search_jobs(db, search_filters)
    if live_only:
        jobs = [j for j in jobs if j.get("source") == "live" or (j.get("apply_url") and "example.com" not in j.get("apply_url", ""))]

    matches = await matching_services.get_or_compute_matches(db, user_id, resume, profile, jobs, settings)
    return [JobMatchOut(**m) for m in matches]
