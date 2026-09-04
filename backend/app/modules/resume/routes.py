from dataclasses import asdict
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limit
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.resume import repositories as repo
from app.modules.resume import services
from app.modules.resume.parsing.action_verbs import analyze_action_verbs
from app.modules.resume.parsing.skills_depth import analyze_skills_depth
from app.modules.resume.parsing.text_extraction import CorruptedFileError, UnsupportedFileTypeError
from app.modules.resume.schemas import AchievementCreate, AchievementOut, MasterResumeOut

router = APIRouter()


def _to_out(doc: dict) -> MasterResumeOut:
    parsed = doc.get("parsed", {})
    action_verbs = doc.get("action_verbs")
    skills_depth = doc.get("skills_depth")
    
    if action_verbs is None:
        combined = parsed.get("experience_raw", []) + parsed.get("projects_raw", [])
        action_verbs = asdict(analyze_action_verbs(combined))

    if skills_depth is None:
        skills_depth = asdict(analyze_skills_depth(parsed.get("skills", [])))

    strict_ats_score = doc.get("strict_ats_score")
    ats_status = doc.get("ats_status")
    if strict_ats_score is None or ats_status is None:
        parseability = doc.get("parseability", {})
        recruiter_impact = doc.get("recruiter_impact", {})
        has_email = bool(parseability.get("contact_info_found", {}).get("email"))
        has_phone = bool(parseability.get("contact_info_found", {}).get("phone"))
        is_multi_col = bool(parseability.get("likely_multi_column"))
        strict_ats_score, ats_status = services.compute_strict_ats_benchmark(
            parseability_score=parseability.get("score", 0),
            recruiter_score=recruiter_impact.get("score", 0),
            action_verb_score=action_verbs.get("score", 0),
            skills_depth_score=skills_depth.get("score", 0),
            is_multi_col=is_multi_col,
            has_email=has_email,
            has_phone=has_phone,
        )

    created_at_val = doc.get("created_at")
    created_at_str = created_at_val.isoformat() if hasattr(created_at_val, "isoformat") else str(created_at_val)

    return MasterResumeOut(
        id=str(doc["_id"]),
        version=doc["version"],
        file_name=doc["file_name"],
        file_type=doc["file_type"],
        parsed=parsed,
        parseability=doc.get("parseability") or {},
        recruiter_impact=doc.get("recruiter_impact") or {},
        action_verbs=action_verbs,
        skills_depth=skills_depth,
        strict_ats_score=strict_ats_score,
        ats_status=ats_status,
        created_at=created_at_str,
    )


@router.post(
    "/upload",
    response_model=MasterResumeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60, key_prefix="resume_upload"))],
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    file_bytes = await file.read()
    try:
        doc = await services.ingest_resume(
            db, settings, str(current_user["_id"]), file.filename, file_bytes
        )
    except (services.FileTooLargeError, services.EmptyFileError, UnsupportedFileTypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except CorruptedFileError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return _to_out(doc)


@router.get("/master", response_model=MasterResumeOut | None)
async def get_master_resume(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await repo.get_active_master_resume(db, str(current_user["_id"]))
    if doc is None:
        return None
    return _to_out(doc)


def _achievement_to_out(doc: dict) -> AchievementOut:
    created_at_val = doc.get("created_at")
    created_at_str = created_at_val.isoformat() if hasattr(created_at_val, "isoformat") else str(created_at_val)
    return AchievementOut(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc["description"],
        metrics=doc.get("metrics"),
        skills_tags=doc.get("skills_tags", []),
        created_at=created_at_str,
    )


@router.post("/achievements", response_model=AchievementOut, status_code=status.HTTP_201_CREATED)
async def create_achievement(
    body: AchievementCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await repo.create_achievement(db, str(current_user["_id"]), body.model_dump())
    return _achievement_to_out(doc)


@router.get("/achievements", response_model=list[AchievementOut])
async def list_achievements(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await repo.list_achievements(db, str(current_user["_id"]))
    return [_achievement_to_out(d) for d in docs]


@router.delete("/achievements/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(
    achievement_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    deleted = await repo.delete_achievement(db, str(current_user["_id"]), achievement_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found.")
