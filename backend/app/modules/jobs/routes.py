from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limit
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs import services
from app.modules.jobs.schemas import JobOut, CreateCustomJobRequest
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo

router = APIRouter()


def _attach_canonical_role_meta(job: dict) -> None:
    if job.get("canonical_role"):
        job.setdefault("canonical_role_key", None)
        job.setdefault("role_domain", job.get("industry") or "Technology")
        return
    from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role
    title = job.get("title") or ""
    prof, _, _ = resolve_role(title)
    if prof:
        job.setdefault("canonical_role", prof.canonical_role)
        canon_key = None
        for k, p in ROLE_TAXONOMY.items():
            if p.canonical_role == prof.canonical_role:
                canon_key = k
                break
        job.setdefault("canonical_role_key", canon_key)
        job.setdefault("role_domain", prof.domain)
    else:
        job.setdefault("canonical_role", title or None)
        job.setdefault("canonical_role_key", None)
        job.setdefault("role_domain", job.get("industry") or "Technology")


def _attach_compensation_meta(job: dict) -> None:
    if job.get("compensation_type") is None:
        from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text
        text = f"{job.get('description') or ''} {job.get('raw_html') or ''}"
        is_intern = (
            job.get("opportunity_type") == "INTERNSHIP"
            or job.get("job_type") == "internship"
            or "intern" in (job.get("title") or "").lower()
        )
        comp = extract_compensation_from_payload_and_text(
            text=text,
            raw_payload=job.get("raw_payload") or {},
            is_internship=is_intern,
        )
        job["compensation_type"] = comp.compensation_type
        job["compensation_text"] = comp.compensation_text
        if comp.salary_min is not None and job.get("salary_min") is None:
            job["salary_min"] = comp.salary_min
        if comp.salary_max is not None and job.get("salary_max") is None:
            job["salary_max"] = comp.salary_max
        if comp.stipend_min is not None and job.get("stipend_min") is None:
            job["stipend_min"] = comp.stipend_min
        if comp.salary_disclosed and not job.get("salary_disclosed"):
            job["salary_disclosed"] = True


def _attach_completeness_meta(job: dict) -> None:
    if not job.get("completeness_status") or not job.get("quality_tier"):
        from app.modules.jobs.completeness import evaluate_opportunity_completeness
        comp_eval = evaluate_opportunity_completeness(job)
        job.setdefault("completeness_status", comp_eval.recommendation_quality.value)
        job.setdefault("quality_tier", comp_eval.quality_tier.value)
        if comp_eval.rejection_reason:
            rej_val = comp_eval.rejection_reason.value if hasattr(comp_eval.rejection_reason, "value") else str(comp_eval.rejection_reason)
            job.setdefault("rejection_reason", rej_val)


def _strip_for_list(job: dict) -> dict:
    """Lighter payload for the list view — full description/responsibilities
    aren't needed until someone opens the detail view."""
    from app.modules.jobs.location_normalization import extract_country_from_location
    job = {**job}
    job.pop("_id", None)
    job.pop("jd_text", None)
    job.pop("responsibilities", None)
    job.pop("qualifications", None)
    job.setdefault("url_type", "UNVERIFIED")
    job.setdefault("is_direct_apply", job.get("url_type") == "DIRECT_REQUISITION")
    job.setdefault("verification_status", "VERIFIED_ACTIVE")
    job.setdefault("country", extract_country_from_location(job.get("location")))
    job.setdefault("contextual_requirements", [])
    job.setdefault("posted_days_ago", 0)
    _attach_canonical_role_meta(job)
    _attach_compensation_meta(job)
    _attach_completeness_meta(job)
    return job


def _strip_for_detail(job: dict) -> dict:
    """Full payload for the job detail view — keeps responsibilities and qualifications."""
    from app.modules.jobs.location_normalization import extract_country_from_location
    job = {**job}
    job.pop("_id", None)
    job.pop("jd_text", None)
    job.setdefault("responsibilities", [])
    job.setdefault("qualifications", [])
    job.setdefault("url_type", "UNVERIFIED")
    job.setdefault("is_direct_apply", job.get("url_type") == "DIRECT_REQUISITION")
    job.setdefault("verification_status", "VERIFIED_ACTIVE")
    job.setdefault("country", extract_country_from_location(job.get("location")))
    job.setdefault("contextual_requirements", [])
    job.setdefault("posted_days_ago", 0)
    _attach_canonical_role_meta(job)
    _attach_compensation_meta(job)
    _attach_completeness_meta(job)
    return job


@router.get("", response_model=list[JobOut])
async def list_jobs(
    job_type: str | None = None,
    opportunity_type: str | None = None,
    location: str | None = None,
    remote_only: bool = False,
    min_lpa: float | None = None,
    fresher_friendly_only: bool = False,
    skill: str | None = None,
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
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    safe_page = max(1, page)
    safe_page_size = min(max(1, page_size), 100)
    skip = (safe_page - 1) * safe_page_size

    filters = {
        "job_type": job_type,
        "opportunity_type": opportunity_type,
        "location": location,
        "remote_only": remote_only,
        "min_lpa": min_lpa,
        "fresher_friendly_only": fresher_friendly_only,
        "skill": skill,
        "role": role,
        "domain": domain,
        "stage": stage,
        "search": search,
        "sort_by": sort_by,
        "region": region,
        "max_posted_days": max_posted_days,
        "include_benchmarks": include_benchmarks,
        "skip": skip,
        "limit": safe_page_size,
        "active_discovery_only": not include_benchmarks,
        "direct_apply_only": not include_benchmarks,
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


@router.post(
    "/sync",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60, key_prefix="jobs_sync"))],
)
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


@router.post(
    "/custom", 
    response_model=JobOut,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60, key_prefix="jobs_custom"))],
)
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


    # Resolve canonical requirements from canonical JD analysis
    try:
        import html
        reqs = await services.get_canonical_job_requirements(db, job)
        if reqs:
            if reqs.required_skills or reqs.must_have_skills:
                job["skills_required"] = [html.unescape(s).strip() for s in (reqs.required_skills or reqs.must_have_skills)]

            if reqs.preferred_skills:
                job["skills_nice_to_have"] = [html.unescape(s).strip() for s in reqs.preferred_skills]

            if reqs.responsibilities:
                job["responsibilities"] = [html.unescape(r).strip() for r in reqs.responsibilities]

            if reqs.qualifications:
                job["qualifications"] = [html.unescape(q).strip() for q in reqs.qualifications]

            if reqs.min_years_experience is not None:
                job["experience_min"] = int(reqs.min_years_experience)

            if reqs.max_years_experience is not None:
                job["experience_max"] = int(reqs.max_years_experience)

            contextual = [
                html.unescape(k).strip() for k in (list(reqs.technologies) + reqs.domain_keywords + reqs.tools + reqs.keywords)
                if k not in job.get("skills_required", []) and k not in job.get("skills_nice_to_have", [])
            ]
            job["contextual_requirements"] = list(dict.fromkeys(contextual))[:10]
    except Exception:
        pass

    if job.get("location"):
        from app.modules.jobs.smartrecruiters_provider import normalize_location_string
        job["location"] = normalize_location_string(job["location"])

    try:
        from app.modules.profile import repositories as profile_repo
        from app.modules.resume import repositories as resume_repo
        from app.modules.matching.services import build_india_metadata
        from app.modules.matching import repositories as matching_repo

        user_id = str(current_user["_id"])
        profile = await profile_repo.get_profile(db, user_id)
        resume = await resume_repo.get_active_master_resume(db, user_id)
        meta = build_india_metadata(job, profile, resume)
        job.update(meta)

        if resume:
            cached = await matching_repo.get_cached_matches_for_jobs(
                db, user_id, resume.get("version", 1), [job_id]
            )
            if job_id in cached:
                job["match"] = cached[job_id].get("match_data")
    except Exception:
        pass

    return JobOut(**_strip_for_detail(job))
