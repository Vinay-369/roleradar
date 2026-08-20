from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.resume import repositories as repo
from app.modules.resume import services
from app.modules.resume.parsing.text_extraction import CorruptedFileError, UnsupportedFileTypeError
from app.modules.resume.schemas import AchievementCreate, AchievementOut, MasterResumeOut

router = APIRouter()


def _to_out(doc: dict) -> MasterResumeOut:
    return MasterResumeOut(
        id=str(doc["_id"]),
        version=doc["version"],
        file_name=doc["file_name"],
        file_type=doc["file_type"],
        parsed=doc["parsed"],
        parseability=doc["parseability"],
        recruiter_impact=doc["recruiter_impact"],
        created_at=doc["created_at"].isoformat(),
    )


@router.post("/upload", response_model=MasterResumeOut, status_code=status.HTTP_201_CREATED)
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
    return AchievementOut(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc["description"],
        metrics=doc.get("metrics"),
        skills_tags=doc.get("skills_tags", []),
        created_at=doc["created_at"].isoformat(),
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
