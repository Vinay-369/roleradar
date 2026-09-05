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
    experience_min: int | None = None
    experience_max: int | None = None
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
    updated_at: str | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    responsibilities: list[str] = []
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


class CreateCustomJobRequest(BaseModel):
    company: str | None = None
    title: str | None = None
    jd_text: str


class JobFilters(BaseModel):
    job_type: str | None = None
    location: str | None = None
    remote_only: bool = False
    min_lpa: float | None = None
    fresher_friendly_only: bool = False
    skill: str | None = None
    opportunity_type: str | None = None
    experience_tier: str | None = None  # internship | fresher | 0-1 | 1-3 | 3+
    location_preset: str | None = None  # Bengaluru, Hyderabad, Pune, Delhi NCR, etc.
    workplace_type: str | None = None   # REMOTE | HYBRID | ON_SITE
