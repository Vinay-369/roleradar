"""
Pydantic schemas that AI structured output is validated against.
Living here (not in a feature module) because AIService itself validates
against these before ever handing output back to a module.
"""
from enum import Enum

from pydantic import BaseModel, Field


class ChangeStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_USER_INPUT = "NEEDS_USER_INPUT"


class ChangeType(str, Enum):
    TEXT_REWRITE = "TEXT_REWRITE"
    SKILL_REORDER = "SKILL_REORDER"
    KEYWORD_INJECTION = "KEYWORD_INJECTION"
    SECTION_REORDER = "SECTION_REORDER"


class BulletRewrite(BaseModel):
    bullet_index: int
    original: str
    proposed: str
    action: str = "REWRITE"  # REWRITE | KEEP
    reason: str = ""
    source_evidence: str = ""
    confidence: float = Field(default=0.9, ge=0, le=1)
    status: ChangeStatus = ChangeStatus.PENDING
    fabrication_warning: str | None = None
    change_id: str | None = None


class SkillAddition(BaseModel):
    skill: str
    source_evidence: str
    reason: str = ""
    status: ChangeStatus = ChangeStatus.PENDING
    change_id: str | None = None


class SkillsTailoring(BaseModel):
    ordered_skills: list[str] = Field(default_factory=list)
    additions: list[SkillAddition] = Field(default_factory=list)


class SummaryTailoring(BaseModel):
    original: str = ""
    proposed: str = ""
    reason: str = ""
    source_evidence: str = ""
    confidence: float = Field(default=0.95, ge=0, le=1)
    status: ChangeStatus = ChangeStatus.PENDING
    change_id: str | None = None


class TailoringChange(BaseModel):
    change_id: str
    section: str = "EXPERIENCE"  # SUMMARY | SKILLS | EXPERIENCE | PROJECTS
    change_type: str = "TEXT_REWRITE"  # TEXT_REWRITE | SKILL_REORDER | KEYWORD_INJECTION
    original: str
    proposed: str
    reason: str
    source_evidence: str
    confidence: float = Field(ge=0, le=1)
    status: ChangeStatus
    target_bullet_index: int | None = None
    fabrication_warning: str | None = None
    before_order: list[str] | None = None
    after_order: list[str] | None = None


class CompactBulletRewrite(BaseModel):
    bullet_index: int
    proposed: str
    reason: str = ""


class CompactTailoringPlan(BaseModel):
    summary: str | None = None
    experience_rewrites: list[CompactBulletRewrite] = Field(default_factory=list)
    project_rewrites: list[CompactBulletRewrite] = Field(default_factory=list)
    unmatched_gaps: list[str] = Field(default_factory=list)
    changes: list[TailoringChange] = Field(default_factory=list)


class StructuredTailoringResult(BaseModel):
    summary: SummaryTailoring | None = None
    skills: SkillsTailoring = Field(default_factory=SkillsTailoring)
    experience_bullets: list[BulletRewrite] = Field(default_factory=list)
    project_bullets: list[BulletRewrite] = Field(default_factory=list)
    unmatched_gaps: list[str] = Field(default_factory=list)
    sections_evaluated: list[str] = Field(default_factory=list)
    sections_changed: list[str] = Field(default_factory=list)
    changes: list[TailoringChange] = Field(default_factory=list)


class TailoringResult(BaseModel):
    sections_evaluated: list[str] = Field(default_factory=list)
    sections_changed: list[str] = Field(default_factory=list)
    unmatched_gaps: list[str] = Field(default_factory=list)
    changes: list[TailoringChange] = Field(default_factory=list)
    structured: StructuredTailoringResult | None = None


class ExtractedJDSkill(BaseModel):
    skill: str
    requirement_level: str  # REQUIRED | PREFERRED | OPTIONAL


class InterviewQuestion(BaseModel):
    question: str
    category: str  # technical | managerial | hr | behavioral | project_defense | role_specific
    star_hint: str | None = None
    strategy: str | None = None
    sample_answer: str | None = None
    pitfalls: str | None = None


class InterviewQuestionsResult(BaseModel):
    questions: list[InterviewQuestion]


class JobDescriptionAnalysis(BaseModel):
    company: str | None = None
    role: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
    experience_years_min: float | None = None
    education: list[str] = []
    certifications: list[str] = []
    keywords: list[str] = []
    location: str | None = None
    job_type: str | None = None
