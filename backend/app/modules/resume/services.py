"""
Resume ingestion service. Orchestrates: file validation -> text/layout
extraction -> deterministic structuring -> 4-Pillar Quality Audit
(Parseability Engine, Recruiter Impact, Action Verbs, Skills Depth)
-> storage as a new immutable version. No AI call in this path — see
module docstrings for why each step is deterministic-first.
"""
from dataclasses import asdict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.modules.resume import repositories as repo
from app.modules.resume.parsing.action_verbs import analyze_action_verbs
from app.modules.resume.parsing.parseability import analyze_parseability
from app.modules.resume.parsing.recruiter_impact import analyze_recruiter_impact
from app.modules.resume.parsing.skills_depth import analyze_skills_depth
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


def compute_strict_ats_benchmark(
    parseability_score: int,
    recruiter_score: int,
    action_verb_score: int,
    skills_depth_score: int,
    is_multi_col: bool,
    has_email: bool,
    has_phone: bool,
) -> tuple[int, dict]:
    """
    Computes strict enterprise ATS benchmark and pass/review/at-risk status.
    Combines 4 pillars with critical enterprise gate penalties (contact info, layout format).
    """
    base_score = round(
        parseability_score * 0.30
        + recruiter_score * 0.30
        + action_verb_score * 0.20
        + skills_depth_score * 0.20
    )

    # Critical gate deductions
    deductions = 0
    if not has_email:
        deductions += 15
    if not has_phone:
        deductions += 10
    if is_multi_col:
        deductions += 20

    strict_score = max(15, min(100, base_score - deductions))

    if strict_score >= 80:
        status_info = {
            "status": "passed",
            "label": "STRONG ATS READINESS — Review Before Applying",
            "color": "text-signal-700 bg-signal-500/10 border-signal-500/30",
        }
    elif strict_score >= 65:
        status_info = {
            "status": "review",
            "label": "REVIEW QUEUE — Optimization Recommended",
            "color": "text-amber-700 bg-amber-500/10 border-amber-500/30",
        }
    else:
        status_info = {
            "status": "at_risk",
            "label": "AT RISK OF AUTO-REJECTION — Critical Issues Found",
            "color": "text-alert-700 bg-alert-600/10 border-alert-600/30",
        }

    return strict_score, status_info


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
    
    # 4-Pillar Deterministic Quality Audit
    parseability = analyze_parseability(
        extracted["text"], extracted["blocks"], extracted["file_type"], extracted["has_tables"]
    )
    combined_bullets = parsed.get("experience_raw", []) + parsed.get("projects_raw", [])
    recruiter_impact = analyze_recruiter_impact(combined_bullets)
    action_verbs = analyze_action_verbs(combined_bullets)
    skills_depth = analyze_skills_depth(parsed.get("skills", []))

    has_email = bool(parseability.contact_info_found.get("email"))
    has_phone = bool(parseability.contact_info_found.get("phone"))
    is_multi_col = parseability.likely_multi_column

    strict_ats_score, ats_status = compute_strict_ats_benchmark(
        parseability_score=parseability.score,
        recruiter_score=recruiter_impact.score,
        action_verb_score=action_verbs.score,
        skills_depth_score=skills_depth.score,
        is_multi_col=is_multi_col,
        has_email=has_email,
        has_phone=has_phone,
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
        action_verbs=asdict(action_verbs),
        skills_depth=asdict(skills_depth),
        strict_ats_score=strict_ats_score,
        ats_status=ats_status,
    )

    from app.modules.matching import repositories as matching_repo
    await matching_repo.invalidate_user_matches(db, user_id)
    return doc
