"""
Resume ingestion service. Orchestrates: file validation -> text/layout
extraction -> deterministic structuring -> Parseability Engine scoring
-> storage as a new immutable version. No AI call in this path — see
module docstrings for why each step is deterministic-first.
"""
from dataclasses import asdict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.modules.resume import repositories as repo
from app.modules.resume.parsing.parseability import analyze_parseability
from app.modules.resume.parsing.recruiter_impact import analyze_recruiter_impact
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.resume.parsing.text_extraction import (
    CorruptedFileError,
    UnsupportedFileTypeError,
    extract_text_and_layout,
)


class FileTooLargeError(Exception):
    pass


class EmptyFileError(Exception):
    pass


def validate_upload(filename: str, file_bytes: bytes, settings: Settings) -> None:
    if not filename.lower().endswith((".pdf", ".docx")):
        raise UnsupportedFileTypeError("Only .pdf and .docx files are supported.")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise FileTooLargeError(f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit.")

    if len(file_bytes) == 0:
        raise EmptyFileError("Uploaded file is empty.")


async def ingest_resume(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    user_id: str,
    filename: str,
    file_bytes: bytes,
) -> dict:
    validate_upload(filename, file_bytes, settings)

    extracted = extract_text_and_layout(file_bytes, filename)
    parsed = structure_resume_text(extracted["text"])
    parseability = analyze_parseability(
        extracted["text"], extracted["blocks"], extracted["file_type"], extracted["has_tables"]
    )
    recruiter_impact = analyze_recruiter_impact(
        parsed["experience_raw"] + parsed["projects_raw"]
    )

    await repo.deactivate_previous(db, user_id)
    version = await repo.get_next_version(db, user_id)
    doc = await repo.create_master_resume(
        db,
        user_id=user_id,
        version=version,
        file_name=filename,
        file_type=extracted["file_type"],
        raw_text=extracted["text"],
        parsed=parsed,
        parseability=asdict(parseability),
        recruiter_impact=asdict(recruiter_impact),
    )

    from app.modules.matching import repositories as matching_repo
    await matching_repo.invalidate_user_matches(db, user_id)
    return doc
