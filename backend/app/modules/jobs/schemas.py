from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    source: str
    title: str
    company: str
    industry: str
    description: str
    skills_required: list[str]
    skills_nice_to_have: list[str]
    experience_min: int
    experience_max: int
    job_type: str  # full_time | internship
    location: str
    is_remote: bool
    salary_min: float | None
    salary_max: float | None
    salary_disclosed: bool
    stipend_min: float | None
    internship_duration_months: int | None
    fresher_friendly: bool
    posted_days_ago: int
    apply_url: str
    responsibilities: list[str] = []


class JobFilters(BaseModel):
    job_type: str | None = None
    location: str | None = None
    remote_only: bool = False
    min_lpa: float | None = None
    fresher_friendly_only: bool = False
    skill: str | None = None
