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
    original: str
    proposed: str
    reason: str
    source_evidence: str
    confidence: float
    status: ChangeStatus


class TailoredResumeOut(BaseModel):
    id: str
    job_id: str
    job_title: str
    company: str
    changes: list[ChangeOut]
    is_finalized: bool
    final_text: str | None = None
    created_at: str


class ChangeStatusUpdate(BaseModel):
    status: ChangeStatus  # APPROVED or REJECTED only, enforced in service layer
