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


async def build_application_package(db: AsyncIOMotorDatabase, user_id: str, application_id: str) -> dict:
    app = await repo.get_application(db, user_id, application_id)
    if app is None:
        raise ApplicationNotFoundError(f"Application {application_id} not found.")

    resume_text = None
    resume_source = "none"

    if app.get("tailored_resume_id"):
        version = await tailoring_repo.get_version(db, user_id, app["tailored_resume_id"])
        if version and version.get("is_finalized") and version.get("final_text"):
            resume_text = version["final_text"]
            resume_source = "tailored"

    if resume_text is None:
        master = await resume_repo.get_active_master_resume(db, user_id)
        if master:
            resume_text = master["raw_text"]
            resume_source = "master"

    checklist = [
        "Review the tailored resume once more before submitting",
        f"Open the official application page: {app['apply_url']}",
        "Attach the downloaded PDF/DOCX resume",
        "Double check contact details are current",
        "Submit the application yourself on the company's site",
        "Come back and mark this application as Applied",
    ]

    return {
        "job_title": app["job_title"],
        "company": app["company"],
        "apply_url": app["apply_url"],
        "resume_text": resume_text,
        "resume_source": resume_source,
        "cover_letter": None,  # Phase 7 (AIService.generate_cover_letter) will populate this
        "checklist": checklist,
    }
