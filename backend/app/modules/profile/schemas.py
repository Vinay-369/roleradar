from enum import Enum

from pydantic import BaseModel, Field, model_validator


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
    experience_years: float = Field(default=0.0, ge=0.0, le=60.0)
    target_roles: list[str] = Field(min_length=1, description="At least one target role is required")
    industries: list[str] = Field(default_factory=list)
    min_lpa: float | None = Field(default=None, ge=0.0, le=500.0)
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: RemotePreference = RemotePreference.ANY
    internship_interested: bool = False
    min_stipend: float | None = Field(default=None, ge=0.0, le=10_000_000.0)
    internship_duration_months: int | None = Field(default=None, ge=1, le=36)
    cgpa: float | None = Field(default=None, ge=0.0, le=10.0)
    tier_college: bool = False
    career_brief: str | None = Field(default=None, max_length=2000)
    github: str | None = None
    linkedin: str | None = None
    portfolio: str | None = None
    auto_apply_settings: AutoApplySettings = Field(default_factory=AutoApplySettings)
    consent_text: str

    @model_validator(mode="after")
    def enforce_category_consistency(self) -> "OnboardingRequest":
        if self.category == CandidateCategory.INTERNSHIP_SEEKER:
            self.internship_interested = True
            self.experience_years = 0.0
            self.min_lpa = None
        return self


class ProfileResponse(OnboardingRequest):
    user_id: str
