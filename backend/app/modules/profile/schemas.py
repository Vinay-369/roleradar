from enum import Enum

from pydantic import BaseModel, Field


class CandidateCategory(str, Enum):
    FRESHER = "FRESHER"
    EXPERIENCED = "EXPERIENCED"
    CAREER_SWITCHER = "CAREER_SWITCHER"
    INTERNSHIP_SEEKER = "INTERNSHIP_SEEKER"


class RemotePreference(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY = "any"


class AutoApplyTier(str, Enum):
    MANUAL = "manual"
    BATCH_REVIEW = "batch_review"
    AUTO_HIGH_MATCH = "auto_high_match"


class AutoApplySettings(BaseModel):
    tier: AutoApplyTier = AutoApplyTier.MANUAL
    min_match_score: int = Field(default=90, ge=0, le=100)
    max_per_day: int = Field(default=5, ge=1, le=20)


class OnboardingRequest(BaseModel):
    category: CandidateCategory
    experience_years: float = 0
    target_roles: list[str] = Field(min_length=1, description="At least one target role is required")
    industries: list[str] = Field(default_factory=list)
    min_lpa: float | None = None
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: RemotePreference = RemotePreference.ANY
    internship_interested: bool = False
    min_stipend: float | None = None
    internship_duration_months: int | None = None
    cgpa: float | None = None
    tier_college: bool = False
    career_brief: str | None = None
    github: str | None = None
    linkedin: str | None = None
    portfolio: str | None = None
    auto_apply_settings: AutoApplySettings = Field(default_factory=AutoApplySettings)
    consent_text: str


class ProfileResponse(OnboardingRequest):
    user_id: str
