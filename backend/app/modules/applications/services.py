"""
Application tracking + Smart Apply (Features 14, 15).

Smart Apply here means exactly what we agreed: RoleRadar prepares a
package (tailored resume text, checklist, the real apply_url) and the
candidate submits it themselves on the actual company site. There is
no scraping, no browser automation, no silent submission on the
user's behalf anywhere in this module -- that boundary is enforced by
what this module simply does not implement, not by a runtime check.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.applications import repositories as repo
from app.modules.jobs import repositories as jobs_repo
from app.modules.resume import repositories as resume_repo
from app.modules.tailoring import repositories as tailoring_repo


from app.db.mongo import Collections


class DuplicateApplicationError(Exception):
    pass


class JobNotFoundError(Exception):
    pass


class ApplicationNotFoundError(Exception):
    pass


async def save_application(
    db: AsyncIOMotorDatabase,
    user_id: str,
    job_id: str,
    tailored_resume_id: str | None,
    notes: str | None,
) -> dict:
    job = await jobs_repo.get_job_by_id(db, job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found.")

    existing = await repo.find_active_application(db, user_id, job_id)
    if existing is not None:
        raise DuplicateApplicationError(
            f"You already have an active application for this role (status: {existing['status']})."
        )

    match_score = None  # populated from live matching if the caller has it; kept simple for Phase 6 scope

    return await repo.create_application(
        db, user_id, job_id, job["title"], job["company"], job["apply_url"],
        tailored_resume_id, match_score, notes,
    )


async def update_application(db: AsyncIOMotorDatabase, user_id: str, application_id: str, updates: dict) -> dict:
    app = await repo.update_application(db, user_id, application_id, updates)
    if app is None:
        raise ApplicationNotFoundError(f"Application {application_id} not found.")
    return app


async def delete_application(db: AsyncIOMotorDatabase, user_id: str, application_id: str) -> None:
    deleted = await repo.delete_application(db, user_id, application_id)
    if not deleted:
        raise ApplicationNotFoundError(f"Application {application_id} not found.")


async def build_application_package(db: AsyncIOMotorDatabase, user_id: str, application_id: str) -> dict:
    app = await repo.get_application(db, user_id, application_id)
    if app is None:
        raise ApplicationNotFoundError(f"Application {application_id} not found.")

    resume_text = None
    resume_source = "none"
    tailored_version_id = app.get("tailored_resume_id")

    if tailored_version_id:
        version = await tailoring_repo.get_version(db, user_id, tailored_version_id)
        if version and version.get("is_finalized") and version.get("final_text"):
            resume_text = version["final_text"]
            resume_source = "tailored"
        else:
            tailored_version_id = None

    # Check if there is any finalized tailored version for this job
    if resume_text is None and app.get("job_id"):
        cursor = db[Collections.RESUME_VERSIONS].find(
            {"user_id": user_id, "job_id": app["job_id"], "is_finalized": True}
        ).sort("created_at", -1)
        versions = await cursor.to_list(length=1)
        if versions and versions[0].get("final_text"):
            resume_text = versions[0]["final_text"]
            resume_source = "tailored"
            tailored_version_id = str(versions[0]["_id"])

    if resume_text is None:
        master = await resume_repo.get_active_master_resume(db, user_id)
        if master:
            resume_text = master["raw_text"]
            resume_source = "master"

    checklist = [
        "Review your tailored resume and verified key qualifications",
        f"Open the official employer application portal: {app['apply_url']}",
        "Upload/attach your ATS-optimized PDF or DOCX resume",
        "Confirm your contact details and links (GitHub, LinkedIn)",
        "Submit the application yourself directly on the employer's official portal",
    ]

    return {
        "job_title": app["job_title"],
        "company": app["company"],
        "apply_url": app["apply_url"],
        "resume_text": resume_text,
        "resume_source": resume_source,
        "cover_letter": None,
        "checklist": checklist,
        "tailored_version_id": tailored_version_id,
    }

