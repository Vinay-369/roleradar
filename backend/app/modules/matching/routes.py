from fastapi import APIRouter, Depends, Query, Response
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
    job_type: str | None = None,
    live_only: bool = False,
    opportunity_type: str | None = None,
    experience_tier: str | None = None,
    location_preset: str | None = None,
    workplace_type: str | None = None,
    region: str | None = None,
    role: str | None = None,
    domain: str | None = None,
    stage: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    max_posted_days: int | None = None,
    include_benchmarks: bool = False,
    page: int = 1,
    page_size: int = 50,
    response: Response = Response(),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user_id = str(current_user["_id"])
    profile = await profile_repo.get_profile(db, user_id)
    resume = await resume_repo.get_active_master_resume(db, user_id)

    raw_page = page.default if hasattr(page, "default") else page
    raw_page_size = page_size.default if hasattr(page_size, "default") else page_size
    raw_include_benchmarks = include_benchmarks.default if hasattr(include_benchmarks, "default") else include_benchmarks

    safe_page = max(1, int(raw_page or 1))
    safe_page_size = min(max(1, int(raw_page_size or 50)), 100)
    skip = (safe_page - 1) * safe_page_size

    # Opportunity discovery queries persisted MongoDB opportunities directly without
    # blocking on external ATS synchronizations (decoupled in Phase 16C).
    search_filters: dict = {
        "skip": skip,
        "limit": safe_page_size,
        "active_discovery_only": not include_benchmarks,
        "direct_apply_only": not include_benchmarks,
        "include_benchmarks": include_benchmarks,
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
    if role:
        search_filters["role"] = role
    if domain:
        search_filters["domain"] = domain
    if stage:
        search_filters["stage"] = stage
    if search:
        search_filters["search"] = search
    if sort_by:
        search_filters["sort_by"] = sort_by
    if max_posted_days:
        search_filters["max_posted_days"] = max_posted_days
    if region:
        search_filters["region"] = region

    total_count = await jobs_services.count_jobs(db, search_filters, user_id=user_id)
    if response is not None:
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"

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
            compensation_type=j.get("compensation_type"),
            compensation_text=j.get("compensation_text"),
            eligibility_text=intrinsic_eligibility["reasons"][0],
            degree_requirements=classification.degree_requirements,
            graduation_year_requirements=classification.graduation_year_requirements,
            workplace_type=wp_mode,
            normalized_location=norm_loc,
            eligibility=intrinsic_eligibility,
            realistic_fit="UNKNOWN",
            fit_explanation=intrinsic_eligibility["fit_explanation"],
            contextual_requirements=j.get("contextual_requirements", []),
            **matching_services._get_role_metadata(j),
        ))
    return results
