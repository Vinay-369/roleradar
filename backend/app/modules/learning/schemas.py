from typing import Literal

from pydantic import BaseModel


class SkillGapOut(BaseModel):
    skill: str
    priority: str
    reason: str
    target_job_title: str
    current_evidence: str
    resources: list[str]
    project_suggestion: str
    estimated_days: int
    # Extended Role Intelligence & Provenance fields
    candidate_status: str | None = None
    source: str = "ROLE_TAXONOMY"
    confidence: str = "HIGH"
    domain: str | None = None
    subdomain: str | None = None


# ---------------------------------------------------------------------------
# Roadmap provenance types
# ---------------------------------------------------------------------------

# MARKET    – no real candidate evidence; skills represent role market benchmark
# CANDIDATE – real candidate evidence compared against market aggregate for role
# JOB       – real candidate evidence compared against a specific job's requirements
RoadmapType = Literal["MARKET", "CANDIDATE", "JOB"]

# NONE              – no resume uploaded; candidate skills are unknown
# LIMITED_EVIDENCE  – resume present but too few parsed skills to compute meaningful gaps
# PERSONALIZED      – sufficient candidate evidence exists
PersonalizationStatus = Literal["NONE", "LIMITED_EVIDENCE", "PERSONALIZED"]

# Minimum number of distinct candidate skills required to claim personalization.
# Below this threshold the roadmap defaults to MARKET / LIMITED_EVIDENCE.
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
