"""
Career Copilot context assembly (Feature 20).

This is the piece that makes the Copilot different from a generic
chatbot: before AIService.chat() is ever called, this module pulls
ONLY the requesting user's own data from the collections that already
exist as the source of truth (profile, resume analysis, job matches,
skill gaps). The LLM is never the source of facts here — it only
explains and reasons over context that was already computed
deterministically by other modules.
"""
from dataclasses import dataclass, field

from motor.motor_asyncio import AsyncIOMotorDatabase


@dataclass
class CopilotContext:
    user_id: str
    profile_summary: dict | None = None
    resume_intelligence: dict | None = None
    top_job_matches: list[dict] = field(default_factory=list)
    active_applications: list[dict] = field(default_factory=list)
    skill_gaps: list[dict] = field(default_factory=list)
    learning_progress: dict | None = None
    missing_context_notes: list[str] = field(default_factory=list)


async def build_copilot_context(
    user_id: str,
    db: AsyncIOMotorDatabase | None = None,
    settings: "Settings | None" = None,
) -> CopilotContext:
    """
    Pulls real, user-scoped data from every module that has something
    to say about this candidate. Every query is filtered by user_id at
    the repository layer, never just in the prompt — a candidate can
    never see another user's data through the Copilot.

    db is optional so this remains callable (with an honest "not set
    up" context) in code paths that don't have a live database, e.g.
    isolated unit tests exercising AIService.chat() directly.
    """
    if db is None:
        return CopilotContext(
            user_id=user_id,
            missing_context_notes=["No database connection available."],
        )

    from app.modules.applications import repositories as applications_repo
    from app.modules.jobs import services as jobs_services
    from app.modules.matching.engine import compute_match
    from app.modules.profile import repositories as profile_repo
    from app.modules.resume import repositories as resume_repo

    notes: list[str] = []

    profile = await profile_repo.get_profile(db, user_id)
    if profile is None:
        notes.append("This candidate hasn't completed onboarding yet — no target roles, LPA, or preferences are set.")
        profile_summary = None
    else:
        profile_summary = {
            "category": profile.get("category"),
            "target_roles": profile.get("target_roles", []),
            "min_lpa": profile.get("min_lpa"),
            "preferred_locations": profile.get("preferred_locations", []),
        }

    resume = await resume_repo.get_active_master_resume(db, user_id)
    if resume is None:
        notes.append("This candidate hasn't uploaded a resume yet — no skills, ATS score, or intelligence data exists.")
        resume_intelligence = None
    else:
        resume_intelligence = {
            "skills": resume["parsed"].get("skills", []),
            "parseability_score": resume["parseability"]["score"],
            "recruiter_impact_score": resume["recruiter_impact"]["score"],
            "parseability_issues": [i["message"] for i in resume["parseability"]["issues"][:3]],
        }

    top_matches: list[dict] = []
    if profile is not None and resume is not None:
        from app.db.mongo import Collections

        # 1. Prefer existing persisted match data from Collections.JOB_MATCHES (Phase 16C)
        cursor = db[Collections.JOB_MATCHES].find(
            {"user_id": user_id}
        ).sort("overall_score", -1).limit(5)
        cached_matches = await cursor.to_list(length=5)

        if cached_matches:
            job_ids = [m["job_id"] for m in cached_matches]
            jobs_cursor = db[Collections.JOBS].find({"id": {"$in": job_ids}})
            jobs_by_id = {j["id"]: j async for j in jobs_cursor}
            for m in cached_matches:
                j = jobs_by_id.get(m["job_id"], {})
                m_data = m.get("match_data", {})
                top_matches.append({
                    "job_id": m["job_id"],
                    "title": j.get("title") or m_data.get("job_title", "Opportunity"),
                    "company": j.get("company") or m_data.get("company", "Company"),
                    "overall_score": m.get("overall_score", m_data.get("overall_score", 0)),
                    "apply_readiness": m_data.get("apply_readiness", "READY" if m.get("overall_score", 0) >= 70 else "DEVELOPING"),
                    "missing_skills": m_data.get("missing_skills", []),
                })
        else:
            # 2. Cold-start fallback: evaluate at most 5 jobs (not 100), eliminating CPU/embedding bottleneck
            sample_jobs = await jobs_services.search_jobs(db, {"limit": 5}, user_id=user_id)
            if sample_jobs:
                from app.core.config import get_settings
                from app.core.embeddings.factory import build_embedding_provider

                active_settings = settings or get_settings()
                embedder = build_embedding_provider(active_settings)
                candidate = {
                    "skills": resume["parsed"].get("skills", []),
                    "target_roles": profile.get("target_roles", []),
                    "experience_years": profile.get("experience_years", 0),
                    "preferred_locations": profile.get("preferred_locations", []),
                    "remote_preference": profile.get("remote_preference", "any"),
                    "min_lpa": profile.get("min_lpa"),
                    "industries": profile.get("industries", []),
                }
                scored = []
                for job in sample_jobs:
                    match = compute_match(candidate, job, embedder, category=profile.get("category", "FRESHER"))
                    scored.append({
                        "job_id": job["id"],
                        "title": job["title"],
                        "company": job["company"],
                        "overall_score": match.overall_score,
                        "apply_readiness": match.apply_readiness,
                        "missing_skills": match.skill_match.missing,
                    })
                scored.sort(key=lambda s: s["overall_score"], reverse=True)
                top_matches = scored[:5]
    else:
        notes.append("Job matches can't be computed until both a profile and a resume exist.")

    applications = await applications_repo.list_applications(db, user_id)
    active_applications = [
        {"job_title": a["job_title"], "company": a["company"], "status": a["status"]}
        for a in applications[:10]
    ]
    if not applications:
        notes.append("This candidate has no saved or tracked applications yet.")

    return CopilotContext(
        user_id=user_id,
        profile_summary=profile_summary,
        resume_intelligence=resume_intelligence,
        top_job_matches=top_matches,
        active_applications=active_applications,
        skill_gaps=[],  # gaps are job-specific; the Copilot can be extended to fetch these per-question in a future pass
        learning_progress=None,
        missing_context_notes=notes,
    )
