from pydantic import BaseModel, Field


class ParseabilityIssueOut(BaseModel):
    code: str
    severity: str
    message: str


class ParseabilityOut(BaseModel):
    score: int
    issues: list[ParseabilityIssueOut]
    detected_sections: list[str]
    missing_standard_sections: list[str]
    contact_info_found: dict
    likely_multi_column: bool
    word_count: int


class RecruiterImpactOut(BaseModel):
    score: int
    bullets_analyzed: int
    quantified_bullets: int
    weak_verb_bullets: int
    quantification_rate: float
    issues: list[str]


class ActionVerbOut(BaseModel):
    score: int
    total_bullets: int
    strong_verb_bullets: int
    weak_verb_bullets: int
    power_verb_rate: float
    strong_verbs_found: list[str] = Field(default_factory=list)
    weak_verbs_found: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class SkillCategoryItemOut(BaseModel):
    id: str
    name: str
    items: list[str] = Field(default_factory=list)


class SkillsDepthOut(BaseModel):
    score: int
    total_skills: int
    verified_skills_count: int
    domain_coverage_count: int
    categorized_domains: list[SkillCategoryItemOut] = Field(default_factory=list)
    missing_domains: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ATSStatusOut(BaseModel):
    status: str
    label: str
    color: str


class MasterResumeOut(BaseModel):
    id: str
    version: int
    file_name: str
    file_type: str
    parsed: dict
    parseability: ParseabilityOut
    recruiter_impact: RecruiterImpactOut
    action_verbs: ActionVerbOut | None = None
    skills_depth: SkillsDepthOut | None = None
    strict_ats_score: int = 100
    ats_status: ATSStatusOut | None = None
    created_at: str


class AchievementCreate(BaseModel):
    title: str
    description: str
    metrics: str | None = None
    skills_tags: list[str] = []


class AchievementOut(BaseModel):
    id: str
    title: str
    description: str
    metrics: str | None
    skills_tags: list[str]
    created_at: str
