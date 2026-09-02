from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.embeddings.factory import build_embedding_provider
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs import repositories as jobs_repo
from app.modules.jobs.services import get_canonical_job_requirements
from app.modules.learning.engine import build_roadmap, compute_skill_gaps
from app.modules.learning.schemas import RoadmapOut, SkillGapOut
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo

router = APIRouter()


async def _aggregate_role_requirements(db: AsyncIOMotorDatabase, target_role: str) -> dict:
    """Aggregates skill requirements across matching postings for target_role."""
    target_lower = target_role.lower()
    target_words = set(target_lower.split())

    all_jobs = await jobs_repo.find_jobs(db, {}, limit=200)
    matching_jobs = []
    for j in all_jobs:
        title_lower = j.get("title", "").lower()
        if target_lower in title_lower or title_lower in target_lower or any(w in title_lower for w in target_words if len(w) > 3):
            matching_jobs.append(j)

    if not matching_jobs and all_jobs:
        matching_jobs = all_jobs[:10]

    req_counter: Counter = Counter()
    nice_counter: Counter = Counter()

    for j in matching_jobs:
        # Prefer canonical structured requirements if present
        if j.get("must_have_skills"):
            for s in j["must_have_skills"]:
                req_counter[s] += 1
        else:
            for s in j.get("skills_required", []):
                req_counter[s] += 1

        if j.get("preferred_skills"):
            for s in j["preferred_skills"]:
                nice_counter[s] += 1
        else:
            for s in j.get("skills_nice_to_have", []):
                nice_counter[s] += 1

    # Standard industry benchmarks for common tech roles
    default_role_skills = {
        "full stack": ["JavaScript", "TypeScript", "React", "Node.js", "Python", "SQL", "Git", "REST APIs", "Docker", "PostgreSQL"],
        "backend": ["Python", "FastAPI", "SQL", "PostgreSQL", "REST APIs", "Docker", "Redis", "Git", "Data Structures", "System Design"],
        "frontend": ["JavaScript", "TypeScript", "React", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git", "REST APIs", "Next.js"],
        "data": ["Python", "SQL", "Pandas", "NumPy", "Tableau", "Data Analysis", "Statistics", "Machine Learning", "Power BI"],
        "machine learning": ["Python", "PyTorch", "TensorFlow", "Scikit-Learn", "Machine Learning", "Deep Learning", "SQL", "NLP", "Pandas"],
        "devops": ["Docker", "Kubernetes", "Linux", "AWS", "CI/CD", "Terraform", "Git", "Bash", "Monitoring", "Python"],
    }

    for key, skills in default_role_skills.items():
        if key in target_lower:
            for idx, s in enumerate(skills):
                req_counter[s] += (len(skills) - idx)

    top_required = [s for s, count in req_counter.most_common(8)]
    top_nice = [s for s, count in nice_counter.most_common(6) if s not in top_required]

    if not top_required:
        top_required = ["Python", "JavaScript", "SQL", "REST APIs", "Git"]
    if not top_nice:
        top_nice = ["Docker", "AWS", "CI/CD", "Testing"]

    return {
        "id": f"role_{target_lower.replace(' ', '_')}",
        "title": target_role,
        "company": "Market Standard",
        "must_have_skills": top_required,
        "preferred_skills": top_nice,
        "skills_required": top_required,
        "skills_nice_to_have": top_nice,
        "description": f"Aggregated requirements across matching market postings for {target_role}.",
        "jd_text": f"Target Role: {target_role}. Required skills: {', '.join(top_required)}. Nice to have: {', '.join(top_nice)}.",
        "experience_min": 0,
        "experience_max": 5,
        "job_type": "full_time",
        "location": "Any",
        "is_remote": True,
    }


async def _resolve_job_for_context(db: AsyncIOMotorDatabase, user_id: str, job_id: str | None = None, role: str | None = None) -> dict:
    if job_id:
        job = await jobs_repo.get_job_by_id(db, job_id)
        if job is not None:
            if job.get("source") == "custom" and job.get("user_id") and job.get("user_id") != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
            return job

    profile = await profile_repo.get_profile(db, user_id)
    target_role = role
    if not target_role and profile and profile.get("target_roles"):
        target_role = profile["target_roles"][0]

    return await _aggregate_role_requirements(db, target_role or "Software Engineer")


async def _compute_gaps(db, settings, user_id, job_id: str | None = None, role: str | None = None):
    resume = await resume_repo.get_active_master_resume(db, user_id)
    profile = await profile_repo.get_profile(db, user_id)
    job = await _resolve_job_for_context(db, user_id, job_id=job_id, role=role)

    # 1. Resolve Canonical Phase 3 StructuredJobRequirements
    reqs = await get_canonical_job_requirements(db, job)

    if resume is None:
        # Graceful fallback: synthesize baseline candidate skills from achievements/profile
        achievements = await resume_repo.list_achievements(db, user_id)
        ach_skills = []
        for a in achievements:
            ach_skills.extend(a.get("skills_tags", []))

        synthetic_skills = list(dict.fromkeys(ach_skills)) or ["Git", "Data Structures", "Problem Solving"]
        resume = {
            "user_id": user_id,
            "parsed": {
                "skills": synthetic_skills,
                "experience_raw": [],
                "projects_raw": [],
            },
        }

    candidate_skills = list(resume["parsed"].get("skills", []))
    for s in resume["parsed"].get("inferred_skills", []):
        if s not in candidate_skills:
            candidate_skills.append(s)
    for e in resume["parsed"].get("experience_entries", []):
        for t in e.get("technologies", []):
            if t not in candidate_skills:
                candidate_skills.append(t)
    for p in resume["parsed"].get("project_entries", []):
        for t in p.get("technologies", []):
            if t not in candidate_skills:
                candidate_skills.append(t)
    candidate_skills_lower = {s.lower().strip() for s in candidate_skills}

    embedder = build_embedding_provider(settings)

    # 2. Extract authoritative must-have and preferred requirements
    must_haves = reqs.must_have_skills if reqs.must_have_skills else job.get("skills_required", [])
    preferreds = reqs.preferred_skills if reqs.preferred_skills else job.get("skills_nice_to_have", [])

    missing_required = []
    partial_required = []

    for req_skill in must_haves:
        r_low = req_skill.lower().strip()
        if r_low in candidate_skills_lower:
            continue
        best_sim = max((embedder.similarity(r_low, c) for c in candidate_skills_lower), default=0.0)
        if best_sim >= 0.55:
            partial_required.append(req_skill)
        else:
            missing_required.append(req_skill)

    missing_preferred = []
    for pref_skill in preferreds:
        p_low = pref_skill.lower().strip()
        if p_low in candidate_skills_lower:
            continue
        missing_preferred.append(pref_skill)

    gaps = compute_skill_gaps(
        missing_required=missing_required,
        partial_required=partial_required,
        missing_nice_to_have=missing_preferred,
        job_title=job.get("title", reqs.target_role or "Target Role"),
    )
    return gaps, job


@router.get("/gaps", response_model=list[SkillGapOut])
async def get_skill_gaps_for_role(
    role: str | None = Query(default=None, description="Target role name"),
    job_id: str | None = Query(default=None, description="Optional job ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, _ = await _compute_gaps(db, settings, str(current_user["_id"]), job_id=job_id, role=role)
    return [SkillGapOut(**g.__dict__) for g in gaps]


@router.get("/gaps/{job_id}", response_model=list[SkillGapOut])
async def get_skill_gaps(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, _ = await _compute_gaps(db, settings, str(current_user["_id"]), job_id=job_id)
    return [SkillGapOut(**g.__dict__) for g in gaps]


@router.get("/roadmap", response_model=RoadmapOut)
async def get_roadmap_for_role(
    role: str | None = Query(default=None, description="Target role name"),
    job_id: str | None = Query(default=None, description="Optional job ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, _ = await _compute_gaps(db, settings, str(current_user["_id"]), job_id=job_id, role=role)
    roadmap = build_roadmap(gaps)
    return RoadmapOut(**roadmap)


@router.get("/roadmap/{job_id}", response_model=RoadmapOut)
async def get_roadmap(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, _ = await _compute_gaps(db, settings, str(current_user["_id"]), job_id=job_id)
    roadmap = build_roadmap(gaps)
    return RoadmapOut(**roadmap)
