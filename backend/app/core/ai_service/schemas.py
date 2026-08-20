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


class TailoringChange(BaseModel):
    change_id: str
    original: str
    proposed: str
    reason: str
    source_evidence: str
    confidence: float = Field(ge=0, le=1)
    status: ChangeStatus


class TailoringResult(BaseModel):
    changes: list[TailoringChange]


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
