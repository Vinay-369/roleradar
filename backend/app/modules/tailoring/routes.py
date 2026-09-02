import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai_service.service import AIService, get_ai_service
from app.core.config import Settings, get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.tailoring import repositories as repo
from app.modules.tailoring import services
from app.modules.tailoring.export import generate_docx, generate_pdf
from app.modules.tailoring.schemas import (
    ChangeStatusUpdate,
    GenerateTailoringRequest,
    ResumeUpdateRequest,
    TailoredResumeOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_ai_service() -> AIService:
    return get_ai_service(get_settings())


def _to_out(doc: dict) -> TailoredResumeOut:
    return TailoredResumeOut(
        id=str(doc["_id"]),
        job_id=doc["job_id"],
        job_title=doc["job_title"],
        company=doc["company"],
        changes=doc["changes"],
        is_finalized=doc["is_finalized"],
        final_text=doc.get("final_text"),
        parsed=doc.get("parsed"),
        audit=doc.get("audit"),
        tailored_scores=doc.get("tailored_scores"),
        sections_evaluated=doc.get("sections_evaluated", []),
        sections_changed=doc.get("sections_changed", []),
        unmatched_gaps=doc.get("unmatched_gaps", []),
        validation_summary=doc.get("validation_summary"),
        one_page_fit=doc.get("one_page_fit"),
        candidate_classification=doc.get("candidate_classification"),
        resume_strategy=doc.get("resume_strategy"),
        evidence_mapping=doc.get("evidence_mapping"),
        matched_skills=doc.get("matched_skills"),
        missing_skills=doc.get("missing_skills"),
        partial_skills=doc.get("partial_skills"),
        ats_readability_findings=doc.get("ats_readability_findings"),
        master_resume_id=doc.get("master_resume_id"),
        master_resume_version=doc.get("master_resume_version"),
        opportunity_type=doc.get("opportunity_type"),
        opportunity_id=doc.get("opportunity_id"),
        jd_analysis_summary=doc.get("jd_analysis_summary"),
        created_at=doc["created_at"].isoformat() if hasattr(doc["created_at"], "isoformat") else str(doc["created_at"]),
    )


@router.post("/generate", response_model=TailoredResumeOut, status_code=status.HTTP_201_CREATED)
async def generate(
    body: GenerateTailoringRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    ai_service: AIService = Depends(_get_ai_service),
):
    try:
        version = await services.generate_tailoring(
            db, ai_service, str(current_user["_id"]),
            job_id=body.job_id,
            custom_company=body.custom_company,
            custom_role_title=body.custom_role_title,
            custom_jd_text=body.custom_jd_text,
        )
    except services.NoMasterResumeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except services.MissingJobOrJDError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except services.JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Tailoring generation encountered an error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Tailoring generation failed: {exc}. Please try again later.",
        )
    return _to_out(version)


@router.get("/job/{job_id}", response_model=TailoredResumeOut)
async def get_version_for_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    version = await repo.get_version_by_job(db, str(current_user["_id"]), job_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tailored resume for this job.")
    return _to_out(version)


@router.get("/{version_id}", response_model=TailoredResumeOut)
async def get_version(
    version_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    version = await repo.get_version(db, str(current_user["_id"]), version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailored version not found.")
    return _to_out(version)


@router.get("", response_model=list[TailoredResumeOut])
async def list_versions(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    versions = await repo.list_versions(db, str(current_user["_id"]))
    return [_to_out(v) for v in versions]


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    version_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        await services.delete_tailored_version(db, str(current_user["_id"]), version_id)
    except services.VersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.put("/{version_id}/changes/{change_id}", response_model=TailoredResumeOut)
async def update_change(
    version_id: str,
    change_id: str,
    body: ChangeStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        version = await services.set_change_status(
            db, str(current_user["_id"]), version_id, change_id, body.status
        )
    except services.InvalidChangeStatusError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except services.VersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_out(version)


@router.put("/{version_id}/resume", response_model=TailoredResumeOut)
async def update_resume(
    version_id: str,
    body: ResumeUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        version = await services.update_parsed_resume(
            db, str(current_user["_id"]), version_id, body.parsed
        )
    except services.VersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_out(version)


@router.post("/{version_id}/finalize", response_model=TailoredResumeOut)
async def finalize(
    version_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        version = await services.finalize_tailoring(db, str(current_user["_id"]), version_id, settings=settings)
    except services.VersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_out(version)


def _require_exportable(version: dict) -> None:
    if not version.get("parsed") and not version.get("final_text"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume content not available for export.",
        )


@router.get("/{version_id}/export/pdf")
async def export_pdf(
    version_id: str,
    template: str = Query(default="modern", description="modern | classic | technical | harvard | minimal"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    version = await repo.get_version(db, str(current_user["_id"]), version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
    _require_exportable(version)

    content = version.get("parsed") or version.get("final_text")
    candidate_name = current_user.get("full_name", "")
    pdf_bytes = generate_pdf(content, candidate_name=candidate_name, template=template)
    company_slug = version.get("company", "Company").replace(" ", "_")
    filename = f"resume_{company_slug}_{template}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{version_id}/export/docx")
async def export_docx(
    version_id: str,
    template: str = Query(default="modern", description="modern | classic | technical | harvard | minimal"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    version = await repo.get_version(db, str(current_user["_id"]), version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
    _require_exportable(version)

    content = version.get("parsed") or version.get("final_text")
    candidate_name = current_user.get("full_name", "")
    docx_bytes = generate_docx(content, candidate_name=candidate_name, template=template)
    company_slug = version.get("company", "Company").replace(" ", "_")
    filename = f"resume_{company_slug}_{template}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
