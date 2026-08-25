from pydantic import BaseModel


class JobMatchOut(BaseModel):
    job_id: str
    job_title: str
    company: str
    overall_score: int
    skill_score: int
    role_score: int
    experience_score: int
    location_score: int
    salary_score: int
    industry_score: int
    matched_skills: list[str]
    partial_skills: list[str]
    missing_skills: list[str]
    apply_readiness: str
    job_type: str
    source: str
    apply_url: str
    location: str | None = None
    is_remote: bool | None = False
    salary_min: float | None = None
    salary_max: float | None = None
    stipend_min: int | None = None
    stipend_max: int | None = None
    posted_days_ago: int | None = 0
    created_at: str | None = None
