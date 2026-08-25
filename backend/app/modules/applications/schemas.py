from enum import Enum

from pydantic import BaseModel


class ApplicationStatus(str, Enum):
    SAVED = "SAVED"
    TAILORED = "TAILORED"
    QUEUED = "QUEUED"
    APPLIED = "APPLIED"
    SHORTLISTED = "SHORTLISTED"
    VIEWED = "VIEWED"  # Kept for legacy backward compatibility
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class CreateApplicationRequest(BaseModel):
    job_id: str
    tailored_resume_id: str | None = None
    notes: str | None = None


class UpdateApplicationRequest(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None


class ApplicationOut(BaseModel):
    id: str
    job_id: str
    job_title: str
    company: str
    apply_url: str
    tailored_resume_id: str | None
    status: ApplicationStatus
    match_score_at_save: int | None
    notes: str | None
    created_at: str
    updated_at: str


class ApplicationPackageOut(BaseModel):
    job_title: str
    company: str
    apply_url: str
    resume_text: str | None
    resume_source: str  # "tailored" | "master" | "none"
    cover_letter: str | None
    checklist: list[str]
    tailored_version_id: str | None = None

