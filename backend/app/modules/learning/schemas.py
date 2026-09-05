from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class CompetencyStatus(str, Enum):
    DEMONSTRATED = "DEMONSTRATED"
    PARTIALLY_DEMONSTRATED = "PARTIALLY_DEMONSTRATED"
    NO_RESUME_EVIDENCE = "NO_RESUME_EVIDENCE"


class CompetencyTier(str, Enum):
    FOUNDATION = "FOUNDATION"
    CORE = "CORE"
    DOMAIN_PROCESSING = "DOMAIN_PROCESSING"
    TOOLS = "TOOLS"
    CLOUD_SPECIALIZATION = "CLOUD_SPECIALIZATION"
    ADVANCED = "ADVANCED"


class CompetencyImportance(str, Enum):
    CORE = "CORE"
    COMMON = "COMMON"
    OPTIONAL = "OPTIONAL"


class CompetencyEvidenceOut(BaseModel):
    section: str = "SKILLS"  # EXPERIENCE | PROJECTS | SKILLS | EDUCATION | SUMMARY
    entity_name: str | None = None  # e.g., "RoleRadar", "Acme Corp", "B.Tech Computer Science"
    text: str = ""  # Evidence snippet or bullet text
    evidence_type: str = "EXPLICIT_SKILL"  # WORK_EXPERIENCE | PROJECT | EXPLICIT_SKILL | COURSEWORK | RELATED_TECHNOLOGY | NONE
    source_reference: str | None = None


class SkillGapOut(BaseModel):
    skill: str
    priority: str
    reason: str
    target_job_title: str
    current_evidence: str
    resources: list[str] = Field(default_factory=list)
    project_suggestion: str = ""
    estimated_days: int = 5
    # Extended Role Intelligence & Provenance fields
    candidate_status: str | None = None
    source: str = "ROLE_TAXONOMY"
    confidence: str = "HIGH"
    domain: str | None = None
    subdomain: str | None = None
    # Canonical Phase 16D Career Skill Intelligence fields
    tier: str = CompetencyTier.CORE.value
    status: str = CompetencyStatus.NO_RESUME_EVIDENCE.value
    importance: str = CompetencyImportance.CORE.value
    evidence: list[CompetencyEvidenceOut] = Field(default_factory=list)
    explanation: str = ""
    evidence_type: str = "NONE"


CareerCompetencyOut = SkillGapOut


class CareerAlignmentSummary(BaseModel):
    total: int = 0
    demonstrated: int = 0
    partially_demonstrated: int = 0
    no_resume_evidence: int = 0


class CareerAlignmentOut(BaseModel):
    role: str
    domain: str | None = None
    subdomain: str | None = None
    confidence: str = "HIGH"
    provenance: str = "ROLE_TAXONOMY"
    has_resume: bool = False
    message: str | None = None
    summary: CareerAlignmentSummary = Field(default_factory=CareerAlignmentSummary)
    competencies: list[CareerCompetencyOut] = Field(default_factory=list)


class CanonicalRoleOut(BaseModel):
    role: str
    domain: str
    subdomain: str
    aliases: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Roadmap provenance types
# ---------------------------------------------------------------------------

RoadmapType = Literal["MARKET", "CANDIDATE", "JOB"]
PersonalizationStatus = Literal["NONE", "LIMITED_EVIDENCE", "PERSONALIZED"]
_MIN_SKILLS_FOR_PERSONALIZATION = 3


class RoadmapOut(BaseModel):
    immediate: list[str]
    week_1: list[str]
    week_2: list[str]
    month_1: list[str]
    # Provenance / personalization context
    is_personalized: bool = False
    roadmap_type: RoadmapType = "MARKET"
    personalization_status: PersonalizationStatus = "NONE"
    role_context: str = ""
    role_confidence: str = "HIGH"
    provenance_source: str = "ROLE_TAXONOMY"
    message: str | None = None
