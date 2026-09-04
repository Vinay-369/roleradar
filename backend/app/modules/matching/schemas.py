from pydantic import BaseModel


class JobMatchOut(BaseModel):
    job_id: str
    job_title: str
    company: str
    overall_score: int | None = None
    skill_score: int | None = None
    role_score: int | None = None
    experience_score: int | None = None
    location_score: int | None = None
    salary_score: int | None = None
    industry_score: int | None = None
    matched_skills: list[str] = []
    partial_skills: list[str] = []
    missing_skills: list[str] = []
    skills_required: list[str] = []
    apply_readiness: str | None = None
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
    has_match: bool = True
    source_job_id: str | None = None
    source_url: str | None = None
    verification_status: str = "VERIFIED_ACTIVE"
    verified_at: str | None = None
    last_verified_at: str | None = None
    verification_reason: str | None = None
    verification_method: str | None = None
    url_type: str = "UNVERIFIED"
    is_direct_apply: bool = False
    posted_at: str | None = None
    country: str | None = None
    opportunity_type: str | None = "FULL_TIME"
    candidate_suitability: str | None = "UNKNOWN"
    student_eligible: bool | None = False
    fresher_eligible: bool | None = False
    stipend: float | None = None
    stipend_currency: str | None = None
    stipend_period: str | None = None
    salary_currency: str | None = "INR"
    eligibility_text: str | None = None
    degree_requirements: list[str] = []
    graduation_year_requirements: list[int] = []
    workplace_type: str = "UNKNOWN"
    normalized_location: str | None = None
    eligibility: dict | None = None
    realistic_fit: str | None = None
    fit_explanation: str | None = None
    factor_weights: dict[str, float] | None = None
    score_explanation: str | None = None
