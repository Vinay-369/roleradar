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
    opportunity_type: str | None = Query(default=None, description="FULL_TIME | INTERNSHIP | GRADUATE_PROGRAM | APPRENTICESHIP"),
    experience_tier: str | None = Query(default=None, description="internship | fresher | 0-1 | 1-3 | 3+"),
    location_preset: str | None = Query(default=None, description="Bengaluru | Hyderabad | Pune | Delhi NCR | etc."),
    workplace_type: str | None = Query(default=None, description="REMOTE | HYBRID | ON_SITE"),
    region: str | None = Query(default=None, description="india | global | all"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user_id = str(current_user["_id"])
    profile = await profile_repo.get_profile(db, user_id)
    resume = await resume_repo.get_active_master_resume(db, user_id)

    # Opportunity discovery queries persisted MongoDB opportunities directly without
    # blocking on external ATS synchronizations (decoupled in Phase 16C).
    search_filters: dict = {
        "limit": 500,
        "active_discovery_only": True,
        "direct_apply_only": True,
    }
    if job_type:
        search_filters["job_type"] = job_type
    if live_only:
        search_filters["source"] = "live"
    if opportunity_type:
        search_filters["opportunity_type"] = opportunity_type
    if experience_tier:
        search_filters["experience_tier"] = experience_tier
    if location_preset:
        search_filters["location_preset"] = location_preset
    if workplace_type:
        search_filters["workplace_type"] = workplace_type

    jobs = await jobs_services.search_jobs(db, search_filters, user_id=user_id)
    if live_only:
        jobs = [j for j in jobs if j.get("source") == "live" or (j.get("apply_url") and "example.com" not in j.get("apply_url", ""))]

    from app.modules.jobs.location_normalization import is_india_opportunity

    if isinstance(region, str) and region.lower() in ("india", "in"):
        jobs = [j for j in jobs if (j.get("country") == "India" or is_india_opportunity(j.get("location")))]

    # If candidate has an active master resume, compute personalized matching
    if resume is not None:
        effective_profile = profile or {
            "target_roles": [],
            "experience_years": 0,
            "preferred_locations": [],
            "remote_preference": "any",
            "min_lpa": None,
            "min_stipend": None,
            "category": "FRESHER",
        }
        matches = await matching_services.get_or_compute_matches(db, user_id, resume, effective_profile, jobs, settings)
        return [JobMatchOut(**m) for m in matches]

    # Pre-Resume Discovery Mode:
    # Return canonical live/curated opportunities without fabricating match scores
    from app.modules.jobs.classification import classify_opportunity
    from app.modules.jobs.location_normalization import normalize_india_location, detect_workplace_type, extract_country_from_location

    def _is_india_job(j: dict) -> bool:
        return j.get("country") == "India" or is_india_opportunity(j.get("location"))

    jobs.sort(key=lambda j: (0 if _is_india_job(j) else 1, j.get("posted_days_ago", 0)))
    results = []
    for j in jobs:
        created_val = j.get("created_at") or j.get("created")
        created_str = created_val.isoformat() if hasattr(created_val, "isoformat") else (str(created_val) if created_val else None)

        classification = classify_opportunity(
            j.get("title", ""),
            j.get("description", ""),
            j.get("experience_min"),
            j.get("experience_max"),
            j.get("job_type", "full_time"),
        )
        wp_mode = detect_workplace_type(j.get("location"), j.get("description", ""), j.get("is_remote", False))
        norm_loc = normalize_india_location(j.get("location"))

        stipend_val = j.get("stipend") or j.get("stipend_min")
        stipend_curr = j.get("stipend_currency") or ("INR" if stipend_val else None)
        stipend_per = j.get("stipend_period") or ("per_month" if stipend_val else None)

        intrinsic_eligibility = {
            "status": "ELIGIBLE" if (classification.fresher_eligible or classification.student_eligible) else "UNKNOWN",
            "reasons": ["Student / Fresher friendly opening"] if (classification.fresher_eligible or classification.student_eligible) else ["Upload resume to evaluate detailed eligibility"],
            "checks": {
                "experience": "PASS" if classification.fresher_eligible else "UNKNOWN",
                "education": "UNKNOWN",
                "location": "UNKNOWN",
                "opportunity_type": "PASS",
            },
            "realistic_fit": "UNKNOWN",
            "fit_explanation": "Upload your resume to see your personalized eligibility and match score.",
        }

        results.append(JobMatchOut(
            job_id=j["id"],
            job_title=j["title"],
            company=j["company"],
            overall_score=None,
            skill_score=None,
            role_score=None,
            experience_score=None,
            location_score=None,
            salary_score=None,
            industry_score=None,
            matched_skills=[],
            partial_skills=[],
            missing_skills=[],
            skills_required=j.get("skills_required", []),
            apply_readiness=None,
            job_type=j.get("job_type", "full_time"),
            source=j.get("source", "curated"),
            apply_url=j.get("apply_url", ""),
            location=j.get("location"),
            is_remote=j.get("is_remote", False),
            salary_min=j.get("salary_min"),
            salary_max=j.get("salary_max"),
            stipend_min=j.get("stipend_min"),
            stipend_max=j.get("stipend_max"),
            posted_days_ago=j.get("posted_days_ago", 0),
            created_at=created_str,
            has_match=False,
            source_job_id=j.get("source_job_id"),
            source_url=j.get("source_url"),
            verification_status=j.get("verification_status", "VERIFIED_ACTIVE"),
            verified_at=j.get("verified_at"),
            last_verified_at=j.get("last_verified_at") or j.get("verified_at"),
            verification_reason=j.get("verification_reason"),
            verification_method=j.get("verification_method"),
            url_type=j.get("url_type", "UNVERIFIED"),
            is_direct_apply=j.get("is_direct_apply", j.get("url_type") == "DIRECT_REQUISITION"),
            posted_at=j.get("posted_at"),
            country=j.get("country") or extract_country_from_location(j.get("location")),
            opportunity_type=classification.opportunity_type.value,
            candidate_suitability=classification.suitability.value,
            student_eligible=classification.student_eligible,
            fresher_eligible=classification.fresher_eligible,
            stipend=stipend_val,
            stipend_currency=stipend_curr,
            stipend_period=stipend_per,
            salary_currency=j.get("salary_currency", "INR"),
            eligibility_text=intrinsic_eligibility["reasons"][0],
            degree_requirements=classification.degree_requirements,
            graduation_year_requirements=classification.graduation_year_requirements,
            workplace_type=wp_mode,
            normalized_location=norm_loc,
            eligibility=intrinsic_eligibility,
            realistic_fit="UNKNOWN",
            fit_explanation=intrinsic_eligibility["fit_explanation"],
        ))
    return results
