from pydantic import BaseModel


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


class MasterResumeOut(BaseModel):
    id: str
    version: int
    file_name: str
    file_type: str
    parsed: dict
    parseability: ParseabilityOut
    recruiter_impact: RecruiterImpactOut
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
