from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.embeddings.factory import build_embedding_provider
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.intelligence.ats_platform import (
    ATSPlatform,
    detect_platform_from_url,
    evaluate_platform_compliance,
)
from app.modules.intelligence.ats_score import compute_ats_score
from app.modules.intelligence.dashboard import compute_rri, recommend_next_action, DashboardSummary
from app.modules.intelligence.schemas import (
    ATSScoreOut,
    DashboardOut,
    MatchGuidanceOut,
    PlatformComplianceOut,
    ScoreCategoryOut,
    ActionPlanItemOut,
)
from app.modules.applications import repositories as applications_repo
from app.modules.jobs import services as jobs_services
from app.modules.matching import services as matching_services
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo

router = APIRouter()


@router.get("/ats/{job_id}", response_model=ATSScoreOut)
async def get_ats_score(
    job_id: str,
    platform: str | None = Query(default=None, description="workday | taleo | greenhouse | lever | icims | generic"),
    version_id: str | None = Query(default=None, description="Optional tailored resume version ID to score"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user_id = str(current_user["_id"])
    resume = await resume_repo.get_active_master_resume(db, user_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a resume first.")

    job = await jobs_services.get_job(db, job_id, user_id=user_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    profile = await profile_repo.get_profile(db, user_id) or {}

    tailored_version = None
    if version_id:
        from app.modules.tailoring import repositories as tailoring_repo
        tailored_version = await tailoring_repo.get_version(db, user_id, version_id)
        if tailored_version is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailored version not found.")
        if not tailored_version.get("is_finalized") or not tailored_version.get("final_text"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This tailored version isn't finalized yet — approve your changes and finalize before scoring.",
            )

        from dataclasses import asdict
        from app.modules.matching.engine import compute_match
        from app.modules.resume.parsing.parseability import analyze_parseability
        from app.modules.resume.parsing.recruiter_impact import analyze_recruiter_impact
        from app.modules.resume.parsing.structurer import structure_resume_text

        final_text = tailored_version["final_text"]
        parsed = structure_resume_text(final_text)
        pa = analyze_parseability(final_text, blocks=[], file_type="docx", has_tables=False)
        combined_bullets = parsed.get("experience_raw", []) + parsed.get("projects_raw", [])
        ri = analyze_recruiter_impact(combined_bullets)

        tailored_candidate = {
            "skills": parsed.get("skills", []),
            "target_roles": profile.get("target_roles", []),
            "experience_years": profile.get("experience_years", 0),
            "preferred_locations": profile.get("preferred_locations", []),
            "remote_preference": profile.get("remote_preference", "any"),
            "min_lpa": profile.get("min_lpa"),
            "industries": profile.get("industries", []),
        }
        embedder = build_embedding_provider(settings)
        tailored_match = compute_match(tailored_candidate, job, embedder, category=profile.get("category", "FRESHER"))

        score = compute_ats_score(
            resume_text=final_text,
            jd_text=job["jd_text"],
            parseability_score=pa.score,
            recruiter_impact_score=ri.score,
            skill_match_score=tailored_match.skill_score,
            role_match_score=tailored_match.role_score,
        )

        target_platform = platform if isinstance(platform, str) and platform else detect_platform_from_url(job.get("apply_url", ""))
        platform_res = evaluate_platform_compliance(
            resume_text=final_text,
            parseability_data=asdict(pa),
            platform=target_platform,
            keyword_density=score.keyword_density,
        )
    else:
        matches = await matching_services.get_or_compute_matches(db, user_id, resume, profile, [job], settings)
        match = matches[0] if matches else {}

        score = compute_ats_score(
            resume_text=resume["raw_text"],
            jd_text=job["jd_text"],
            parseability_score=resume["parseability"]["score"],
            recruiter_impact_score=resume["recruiter_impact"]["score"],
            skill_match_score=match.get("skill_score", 0),
            role_match_score=match.get("role_score", 0),
        )

        target_platform = platform if isinstance(platform, str) and platform else detect_platform_from_url(job.get("apply_url", ""))
        platform_res = evaluate_platform_compliance(
            resume_text=resume["raw_text"],
            parseability_data=resume.get("parseability", {}),
            platform=target_platform,
            keyword_density=score.keyword_density,
        )

    return ATSScoreOut(
        overall=score.overall,
        keyword_coverage=score.keyword_coverage,
        required_skills=score.required_skills,
        role_alignment=score.role_alignment,
        structure=score.structure,
        formatting=score.formatting,
        readability=score.readability,
        job_title=job["title"],
        company=job["company"],
        keyword_density=score.keyword_density,
        over_optimization_warning=score.over_optimization_warning,
        knockout_passed=score.knockout_passed,
        knockout_reason=score.knockout_reason,
        match_status=score.match_status,
        categories=[
            ScoreCategoryOut(
                category_name=c.category_name,
                max_points=c.max_points,
                points_awarded=c.points_awarded,
                key_findings=c.key_findings,
            )
            for c in score.categories
        ],
        action_plan=[
            ActionPlanItemOut(
                type=a.type,
                title=a.title,
                description=a.description,
            )
            for a in score.action_plan
        ],
        match_guidance=MatchGuidanceOut(**score.match_guidance.__dict__) if score.match_guidance else None,
        platform_compliance=PlatformComplianceOut(**platform_res) if platform_res else None,
    )



@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user_id = str(current_user["_id"])
    profile = await profile_repo.get_profile(db, user_id)
    resume = await resume_repo.get_active_master_resume(db, user_id)

    onboarding_completed = current_user.get("onboarding_completed", False)
    resume_uploaded = resume is not None

    top_matches: list[dict] = []
    if profile is not None and resume is not None:
        jobs = await jobs_services.search_jobs(db, {"limit": 100}, user_id=user_id)
        matches = await matching_services.get_or_compute_matches(db, user_id, resume, profile, jobs, settings)
        top_matches = [
            {
                "job_id": m["job_id"],
                "job_title": m["job_title"],
                "company": m["company"],
                "overall_score": m["overall_score"],
                "apply_readiness": m["apply_readiness"],
                "missing_skills": m["missing_skills"],
            }
            for m in matches[:5]
        ]

    applications = await applications_repo.list_applications(db, user_id)
    counts: dict[str, int] = {}
    for a in applications:
        counts[a["status"]] = counts.get(a["status"], 0) + 1

    parseability_score = resume["parseability"]["score"] if resume else None
    recruiter_impact_score = resume["recruiter_impact"]["score"] if resume else None
    best_skill_score = top_matches[0]["overall_score"] if top_matches else 0

    rri = compute_rri(parseability_score or 0, recruiter_impact_score or 0, best_skill_score) if resume else 0

    next_action = recommend_next_action(
        resume_uploaded, onboarding_completed, parseability_score, recruiter_impact_score, top_matches
    )

    return DashboardOut(
        role_readiness_index=rri,
        ats_compatibility=parseability_score or 0,
        skill_coverage=best_skill_score,
        top_matches=top_matches,
        application_counts=counts,
        recommended_next_action=next_action,
        resume_uploaded=resume_uploaded,
        onboarding_completed=onboarding_completed,
    )
