from pydantic import BaseModel, Field


class JobOut(BaseModel):
    id: str
    source: str
    source_id: str | None = None
    internal_source: str | None = None
    title: str
    company: str
    company_description: str | None = None
    industry: str | None = None
    description: str | None = None
    skills_required: list[str] = []
    skills_nice_to_have: list[str] = []
    experience_min: float | None = None
    experience_max: float | None = None
    experience_text: str | None = None
    job_type: str | None = None
    employment_type: str | None = None
    location: str | None = None
    country: str | None = None
    city: str | None = None
    state: str | None = None
    is_remote: bool | None = None
    workplace_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_disclosed: bool = False
    salary_currency: str | None = None
    salary_period: str | None = None
    salary_unit: str | None = None
    stipend: float | None = None
    stipend_min: float | None = None
    stipend_max: float | None = None
    stipend_currency: str | None = None
    stipend_period: str | None = None
    stipend_unit: str | None = None
    compensation_type: str | None = None
    compensation_text: str | None = None
    internship_duration_months: int | None = None
    fresher_friendly: bool | None = None
    posted_days_ago: int | None = None
    posted_at: str | None = None
    updated_at: str | None = None
    registration_closing_date: str | None = None
    application_deadline: str | None = None
    end_date: str | None = None
    apply_url: str | None = None
    source_job_id: str | None = None
    source_url: str | None = None
    verification_status: str | None = None
    verified_at: str | None = None
    last_verified_at: str | None = None
    verification_reason: str | None = None
    verification_method: str | None = None
    url_type: str | None = None
    is_direct_apply: bool | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    responsibilities: list[str] = []
    qualifications: list[str] = []
    opportunity_type: str | None = None
    candidate_suitability: str | None = None
    student_eligible: bool | None = None
    fresher_eligible: bool | None = None
    eligibility_text: str | None = None
    degree_requirements: list[str] = []
    graduation_year_requirements: list[int] = []
    normalized_location: str | None = None
    eligibility: dict | None = None
    realistic_fit: str | None = None
    canonical_role: str | None = None
    canonical_role_key: str | None = None
    role_domain: str | None = None
    contextual_requirements: list[str] = []
    completeness_status: str | None = None
    quality_tier: str | None = None
    role_confidence: str | None = None
    rejection_reason: str | None = None
    structured_requirements: dict | None = None
    match: dict | None = None


class CreateCustomJobRequest(BaseModel):
    company: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    jd_text: str = Field(..., max_length=50_000)


class JobFilters(BaseModel):
    job_type: str | None = None
    location: str | None = None
    remote_only: bool = False
    min_lpa: float | None = None
    fresher_friendly_only: bool = False
    skill: str | None = None
    opportunity_type: str | None = None
    experience_tier: str | None = None
    location_preset: str | None = None
    workplace_type: str | None = None