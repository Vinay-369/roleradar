"""
Tailoring service (Feature 9). Orchestrates:
  master resume + JD -> AIService.generate_resume_rewrite() -> stored
  draft with per-change PENDING/NEEDS_USER_INPUT status -> user
  approves/rejects each change -> finalize() applies ONLY approved
  changes to produce the final tailored text.

The finalize step is the load-bearing Truth Guard enforcement point:
no matter what the model proposed, a change that isn't explicitly
APPROVED never reaches final_text. This is checked in code, not
trusted from the model's own "status" field, because Feature 3
requires deterministic logic -- not the LLM -- to own this guarantee.
"""
import json
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai_service.schemas import ChangeStatus
from app.core.ai_service.service import AIService
from app.modules.jobs import repositories as jobs_repo
from app.modules.jobs import services as jobs_services
from app.modules.resume import repositories as resume_repo
from app.modules.tailoring import repositories as repo


class NoMasterResumeError(Exception):
    pass


class JobNotFoundError(Exception):
    pass


class MissingJobOrJDError(Exception):
    pass


class VersionNotFoundError(Exception):
    pass


class InvalidChangeStatusError(Exception):
    pass


async def generate_tailoring(
    db: AsyncIOMotorDatabase,
    ai_service: AIService,
    user_id: str,
    job_id: str | None = None,
    custom_company: str | None = None,
    custom_role_title: str | None = None,
    custom_jd_text: str | None = None,
) -> dict:
    resume = await resume_repo.get_active_master_resume(db, user_id)
    if resume is None:
        raise NoMasterResumeError("Upload a master resume before tailoring.")

    if job_id:
        job = await jobs_repo.get_job_by_id(db, job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found.")
    elif custom_jd_text:
        job = await jobs_services.create_custom_job(
            db,
            company=custom_company or "Custom Application",
            title=custom_role_title or "Target Role",
            jd_text=custom_jd_text,
        )
    else:
        raise MissingJobOrJDError("Provide either job_id or a pasted custom_jd_text.")

    resume_payload = dict(resume["parsed"])
    master_resume_json = json.dumps(resume_payload)
    result = await ai_service.generate_resume_rewrite(
        master_resume_json=master_resume_json,
        jd_text=job["jd_text"],
        user_id=user_id,
        company=job.get("company", ""),
        role=job.get("title", ""),
    )

    changes = []
    for change in result.changes:
        change_dict = change.model_dump(mode="json")
        if not change_dict.get("change_id"):
            change_dict["change_id"] = str(uuid.uuid4())[:8]
        changes.append(change_dict)

    version = await repo.create_version(db, user_id, job["id"], job["title"], job["company"], changes)
    return version


async def set_change_status(
    db: AsyncIOMotorDatabase, user_id: str, version_id: str, change_id: str, status: ChangeStatus
) -> dict:
    if status not in (ChangeStatus.APPROVED, ChangeStatus.REJECTED):
        raise InvalidChangeStatusError("Users may only set a change to APPROVED or REJECTED.")

    version = await repo.update_change_status(db, user_id, version_id, change_id, status.value)
    if version is None:
        raise VersionNotFoundError(f"Version {version_id} not found.")
    return version


async def finalize_tailoring(db: AsyncIOMotorDatabase, user_id: str, version_id: str) -> dict:
    """
    Builds final_text by starting from the master resume's raw text and
    applying ONLY changes with status == APPROVED. Every other status
    (PENDING, REJECTED, NEEDS_USER_INPUT) is excluded -- a change
    sitting at PENDING at finalize time is treated as not-approved,
    never as approved-by-default, so an unreviewed AI suggestion can
    never silently ship.
    """
    version = await repo.get_version(db, user_id, version_id)
    if version is None:
        raise VersionNotFoundError(f"Version {version_id} not found.")

    resume = await resume_repo.get_active_master_resume(db, user_id)
    final_text = resume["raw_text"] if resume else ""

    for change in version["changes"]:
        if change["status"] == ChangeStatus.APPROVED.value:
            if change["original"] and change["original"] in final_text:
                final_text = final_text.replace(change["original"], change["proposed"])

    return await repo.finalize_version(db, user_id, version_id, final_text) or version
