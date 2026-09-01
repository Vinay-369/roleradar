from pydantic import BaseModel

from app.core.ai_service.schemas import ChangeStatus


class GenerateTailoringRequest(BaseModel):
    job_id: str | None = None
    # For a user-pasted JD not in the curated job set. If provided (and
    # job_id is not), a lightweight custom job entry is created first.
    custom_company: str | None = None
    custom_role_title: str | None = None
    custom_jd_text: str | None = None


class ChangeOut(BaseModel):
    change_id: str
    section: str = "EXPERIENCE"
    change_type: str = "TEXT_REWRITE"
    original: str
    proposed: str
    reason: str
    source_evidence: str
    confidence: float
    status: ChangeStatus
    target_bullet_index: int | None = None
    fabrication_warning: str | None = None
    before_order: list[str] | None = None
    after_order: list[str] | None = None
    applied_safely: bool | None = None
    validation_error: str | None = None


class TailoredResumeOut(BaseModel):
    id: str
    job_id: str
    job_title: str
    company: str
    changes: list[ChangeOut]
    is_finalized: bool
    final_text: str | None = None
    parsed: dict | None = None
    audit: dict | None = None
    tailored_scores: dict | None = None
    sections_evaluated: list[str] = []
    sections_changed: list[str] = []
    unmatched_gaps: list[str] = []
    validation_summary: dict | None = None
    one_page_fit: bool | None = None
    candidate_classification: dict | None = None
    resume_strategy: dict | None = None
    evidence_mapping: list[dict] | None = None
    matched_skills: list[str] | None = None
    missing_skills: list[str] | None = None
    partial_skills: list[str] | None = None
    ats_readability_findings: dict | None = None
    created_at: str


class ChangeStatusUpdate(BaseModel):
    status: ChangeStatus  # APPROVED or REJECTED only, enforced in service layer


class ResumeUpdateRequest(BaseModel):
    parsed: dict

