from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_db
from app.modules.applications import repositories as repo
from app.modules.applications import services
from app.modules.applications.schemas import (
    ApplicationOut,
    ApplicationPackageOut,
    CreateApplicationRequest,
    UpdateApplicationRequest,
)
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


def _to_out(doc: dict) -> ApplicationOut:
    return ApplicationOut(
        id=str(doc["_id"]),
        job_id=doc["job_id"],
        job_title=doc["job_title"],
        company=doc["company"],
        apply_url=doc["apply_url"],
        tailored_resume_id=doc.get("tailored_resume_id"),
        status=doc["status"],
        match_score_at_save=doc.get("match_score_at_save"),
        notes=doc.get("notes"),
        created_at=doc["created_at"].isoformat(),
        updated_at=doc["updated_at"].isoformat(),
    )


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def save_application(
    body: CreateApplicationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        app_doc = await services.save_application(
            db, str(current_user["_id"]), body.job_id, body.tailored_resume_id, body.notes
        )
    except services.JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except services.DuplicateApplicationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_out(app_doc)


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    apps = await repo.list_applications(db, str(current_user["_id"]))
    return [_to_out(a) for a in apps]


@router.put("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: str,
    body: UpdateApplicationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "status" in updates:
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
    try:
        app_doc = await services.update_application(db, str(current_user["_id"]), application_id, updates)
    except services.ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_out(app_doc)


@router.get("/{application_id}/package", response_model=ApplicationPackageOut)
async def get_package(
    application_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        package = await services.build_application_package(db, str(current_user["_id"]), application_id)
    except services.ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ApplicationPackageOut(**package)
