from pydantic import BaseModel


class DashboardOut(BaseModel):
    role_readiness_index: int
    ats_compatibility: int
    skill_coverage: int
    top_matches: list[dict]
    application_counts: dict
    recommended_next_action: str
    resume_uploaded: bool
    onboarding_completed: bool


class MatchGuidanceOut(BaseModel):
    status: str
    label: str
    message: str
    target_range: str = "75% - 85%"


class PlatformWarningOut(BaseModel):
    severity: str
    title: str
    message: str


class PlatformComplianceOut(BaseModel):
    platform: str
    platform_name: str
    compliance_score: int
    is_compliant: bool
    warnings: list[PlatformWarningOut]
    tips: list[str]


class ATSScoreOut(BaseModel):
    overall: int
    keyword_coverage: int
    required_skills: int
    role_alignment: int
    structure: int
    formatting: int
    readability: int
    job_title: str
    company: str
    keyword_density: float = 1.5
    over_optimization_warning: bool = False
    match_guidance: MatchGuidanceOut | None = None
    platform_compliance: PlatformComplianceOut | None = None
