from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai_service.service import AIService, get_ai_service
from app.core.config import get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.interview.schemas import InterviewPrepOut
from app.modules.jobs import repositories as jobs_repo
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo

router = APIRouter()


def _get_ai_service() -> AIService:
    return get_ai_service(get_settings())


def _build_real_experiences_search_url(company: str, title: str) -> str:
    query = quote_plus(f"{company} {title} interview questions experience")
    return f"https://www.google.com/search?q={query}"


async def _generate_prep(db, ai_service, user_id, job_id: str | None = None, role: str | None = None, company: str | None = None):
    resume = await resume_repo.get_active_master_resume(db, user_id)
    profile = await profile_repo.get_profile(db, user_id)

    target_role = role
    target_company = company or "Target Company"
    jd_text = ""

    if job_id:
        job = await jobs_repo.get_job_by_id(db, job_id)
        if job is not None:
            if job.get("source") == "custom" and job.get("user_id") and job.get("user_id") != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found.")
            target_role = job["title"]
            target_company = job["company"]
            jd_text = job.get("jd_text", "")

    if not target_role:
        if profile and profile.get("target_roles"):
            target_role = profile["target_roles"][0]
        else:
            target_role = "Software Engineer"

    if not jd_text:
        jd_text = f"Interview preparation for {target_role} position at {target_company}."

    if resume is not None and resume.get("parsed"):
        resume_summary = (
            f"Skills: {', '.join(resume['parsed'].get('skills', []))}. "
            f"Experience: {' | '.join(resume['parsed'].get('experience_raw', [])[:5])}. "
            f"Projects: {' | '.join(resume['parsed'].get('projects_raw', [])[:5])}."
        )
    else:
        achievements = await resume_repo.list_achievements(db, user_id)
        ach_texts = [f"{a.get('title', '')}: {a.get('description', '')}" for a in achievements]
        user_skills = []
        for a in achievements:
            user_skills.extend(a.get("skills_tags", []))
        resume_summary = (
            f"Target Role: {target_role}. "
            f"Candidate Skills: {', '.join(user_skills) if user_skills else 'Software Engineering, Problem Solving, Web Development'}. "
            f"Key Achievements & Projects: {' | '.join(ach_texts) if ach_texts else 'Hands-on project development and academic experience'}."
        )

    result = await ai_service.generate_interview_questions(
        resume_summary=resume_summary,
        jd_text=jd_text,
        target_role=target_role,
        company=target_company,
        user_id=user_id,
    )

    return InterviewPrepOut(
        job_title=target_role,
        company=target_company,
        questions=[q.model_dump() for q in result.questions],
        real_experiences_search_url=_build_real_experiences_search_url(target_company, target_role),
    )


@router.get("/questions", response_model=InterviewPrepOut)
async def get_interview_questions_for_role(
    role: str | None = Query(default=None, description="Target role"),
    company: str | None = Query(default=None, description="Target company"),
    job_id: str | None = Query(default=None, description="Optional job ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    ai_service: AIService = Depends(_get_ai_service),
):
    return await _generate_prep(db, ai_service, str(current_user["_id"]), job_id=job_id, role=role, company=company)


@router.get("/curated/{role_name}", response_model=InterviewPrepOut)
async def get_curated_interview_questions(
    role_name: str,
    company: str | None = Query(default=None, description="Optional target company"),
    current_user: dict = Depends(get_current_user),
):
    from app.modules.interview.role_banks import get_curated_role_questions

    target_company = company or "Target Company"
    curated_raw = get_curated_role_questions(role_name)

    questions = []
    for q in curated_raw:
        q_copy = dict(q)
        q_copy["question"] = q_copy["question"].replace("{comp}", target_company).replace("{target_role}", role_name)
        q_copy["sample_answer"] = q_copy["sample_answer"].replace("{comp}", target_company).replace("{target_role}", role_name)
        questions.append(q_copy)

    return InterviewPrepOut(
        job_title=role_name,
        company=target_company,
        questions=questions,
        real_experiences_search_url=_build_real_experiences_search_url(target_company, role_name),
    )


@router.get("/{job_id}/questions", response_model=InterviewPrepOut)
async def get_interview_questions(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    ai_service: AIService = Depends(_get_ai_service),
):
    return await _generate_prep(db, ai_service, str(current_user["_id"]), job_id=job_id)
