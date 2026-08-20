from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.embeddings.factory import build_embedding_provider
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs import repositories as jobs_repo
from app.modules.learning.engine import build_roadmap, compute_skill_gaps
from app.modules.learning.schemas import RoadmapOut, SkillGapOut
from app.modules.matching import services as matching_services
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo

router = APIRouter()


from collections import Counter


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
        for s in j.get("skills_required", []):
            req_counter[s] += 1
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

    matches = await matching_services.get_or_compute_matches(db, user_id, resume, profile or {}, [job], settings)
    match_data = matches[0] if matches else {}

    candidate_skills = resume["parsed"].get("skills", [])
    candidate_skills_lower = {s.lower() for s in candidate_skills}
    missing_nice_to_have = [
        s for s in job.get("skills_nice_to_have", []) if s.lower() not in candidate_skills_lower
    ]

    gaps = compute_skill_gaps(
        missing_required=match_data.get("missing_skills", []),
        partial_required=match_data.get("partial_skills", []),
        missing_nice_to_have=missing_nice_to_have,
        job_title=job["title"],
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
