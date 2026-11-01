"""The finalized model, PDF preview, and PDF/DOCX exports must agree."""

from io import BytesIO

import fitz
import pytest
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.auth import services as auth_services
from app.modules.jobs import repositories as jobs_repo
from app.modules.jobs import services as jobs_services
from app.modules.resume import repositories as resume_repo
from app.modules.tailoring import repositories as tailoring_repo
from app.modules.tailoring import routes as tailoring_routes
from app.modules.tailoring import services as tailoring_services
from app.modules.tailoring.export import generate_docx, render_docx_from_structured, render_pdf_from_structured, render_text_from_structured


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_preview_export_consistency_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


def _resume_data():
    return {
        "personal": {
            "name": "Nina Candidate",
            "email": "nina@example.com",
            "phone": "+1 555 010 0100",
            "location": "Seattle, WA",
        },
        "summary": "Backend engineer building reliable services.",
        "skills": ["Python", "FastAPI"],
        "experience_raw": [
            "Software Engineer at Acme (2022 - Present)",
            "Built a FastAPI service using Python for internal reporting.",
        ],
        "projects_raw": [{
            "title": "Payments API",
            "tech_stack": "Python, FastAPI",
            "dates": "2021",
            "bullets": ["Built a payment API using Python and FastAPI."],
        }],
        "education_raw": [{
            "institution": "Acme University",
            "degree": "B.S. Computer Science",
            "dates": "2018 - 2022",
            "cgpa": "3.8",
        }],
        "certifications": ["Cloud Practitioner"],
    }


def _change(change_id, section, original, proposed, status, change_type="TEXT_REWRITE"):
    return {
        "change_id": change_id,
        "section": section,
        "change_type": change_type,
        "original": original,
        "proposed": proposed,
        "reason": "Reviewable change backed by the master resume.",
        "source_evidence": original,
        "confidence": 0.95,
        "status": status,
    }


async def _make_version(db, settings, *, changes=None, strategy=None):
    user, _ = await auth_services.register_user(
        db, settings, "preview-export@example.com", "supersecret1", "Nina Candidate", None
    )
    user_id = str(user["_id"])
    parsed = _resume_data()
    raw_text = (
        "Nina Candidate\nnina@example.com +1 555 010 0100\nSeattle, WA\n\n"
        "PROFESSIONAL SUMMARY\nBackend engineer building reliable services.\n\n"
        "SKILLS\nPython, FastAPI\n\n"
        "EXPERIENCE\nSoftware Engineer at Acme (2022 - Present)\n"
        "Built a FastAPI service using Python for internal reporting.\n\n"
        "PROJECTS\nPayments API (Python, FastAPI)\nBuilt a payment API using Python and FastAPI.\n\n"
        "EDUCATION\nAcme University\nB.S. Computer Science (2018 - 2022)\n3.8\n\n"
        "CERTIFICATIONS\nCloud Practitioner\n"
    )
    master = await resume_repo.create_master_resume(
        db,
        user_id,
        version=1,
        file_name="master.pdf",
        file_type="pdf",
        raw_text=raw_text,
        parsed=parsed,
        parseability={"score": 90, "contact_info_found": {"email": "nina@example.com", "phone": "+1 555 010 0100"}, "likely_multi_column": False},
        recruiter_impact={"score": 80, "quantification_rate": 0.0, "weak_verb_bullets": 0},
    )
    await jobs_services.ensure_seed_loaded(db)
    job = (await jobs_repo.find_jobs(db, {}, limit=1))[0]
    version = await tailoring_repo.create_version(
        db,
        user_id=user_id,
        job_id=job["id"],
        job_title=job["title"],
        company=job["company"],
        changes=changes or [],
        parsed=parsed,
        structured={},
        master_resume_id=str(master["_id"]),
        master_resume_version=1,
        resume_strategy=strategy or {
            "template_family": "ATS_PROFESSIONAL",
            "template_variant": "modern",
            "page_budget": 2,
            "section_order": ["summary", "skills", "experience", "projects", "education", "certifications"],
        },
    )
    return user_id, user, master, version


def _pdf_text(content):
    doc = fitz.open(stream=content, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def _docx_text_in_order(content):
    document = Document(BytesIO(content))
    text = []
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            text.append(Paragraph(child, document).text)
        elif child.tag == qn("w:tbl"):
            table = Table(child, document)
            text.extend(cell.text for row in table.rows for cell in row.cells)
    return "\n".join(text)


def test_modern_docx_uses_compact_page_geometry_for_word_rendering():
    document = Document(BytesIO(generate_docx(_resume_data(), candidate_name="Nina Candidate", template="modern")))

    assert document.sections[0].top_margin.inches == pytest.approx(0.35)
    assert document.sections[0].bottom_margin.inches == pytest.approx(0.35)
    assert any(
        run.font.size is not None and run.font.size.pt == pytest.approx(9.0)
        for paragraph in document.paragraphs
        for run in paragraph.runs
    )
    assert any(
        paragraph.text == "PROFESSIONAL SUMMARY"
        and paragraph.paragraph_format.space_before.pt == pytest.approx(3)
        for paragraph in document.paragraphs
    )


def test_renderers_prefer_updated_raw_experience_when_both_representations_exist():
    master_bullet = "Built a FastAPI service using Python for internal reporting."
    approved_bullet = "Engineered a FastAPI service using Python for internal reporting."
    parsed = _resume_data()
    parsed["experience"] = [{
        "company": "Acme",
        "role": "Software Engineer",
        "dates": "2022 - Present",
        "bullets": [master_bullet],
    }]
    parsed["experience_raw"] = ["Software Engineer at Acme (2022 - Present)", approved_bullet]

    rendered = (
        render_text_from_structured(parsed),
        _pdf_text(render_pdf_from_structured(parsed)),
        _docx_text_in_order(render_docx_from_structured(parsed)),
    )

    for output in rendered:
        assert approved_bullet in output
        assert master_bullet not in output


def test_text_preview_preserves_internships_and_optional_sections():
    parsed = _resume_data()
    parsed.update({
        "internships_raw": [{
            "company": "Northwind Labs",
            "role": "Research Intern",
            "dates": "Summer 2023",
            "bullets": ["Evaluated a data quality workflow."],
        }],
        "publications": ["A study of resilient service design."],
        "research": ["Studied fault recovery in distributed systems."],
        "additional_sections": [{"heading": "VOLUNTEERING", "items": ["Mentored first-year students."]}],
        "_ordered_sections": ["education", "internships", "research", "publications"],
    })

    text = render_text_from_structured(parsed)

    for expected in (
        "INTERNSHIPS", "Northwind Labs", "Evaluated a data quality workflow.",
        "PUBLICATIONS", "A study of resilient service design.", "RESEARCH EXPERIENCE",
        "Studied fault recovery in distributed systems.", "VOLUNTEERING", "Mentored first-year students.",
    ):
        assert expected in text
    positions = [text.index(heading) for heading in ("EDUCATION", "INTERNSHIPS", "RESEARCH EXPERIENCE", "PUBLICATIONS")]
    assert positions == sorted(positions)


def test_exporters_retain_populated_sections_omitted_from_strategy_order():
    parsed = _resume_data()
    parsed["internships_raw"] = [{
        "company": "Example Labs",
        "role": "Software Development Intern",
        "dates": "May 2024 - Jul 2024",
        "bullets": ["Implemented two API endpoints using Flask and SQLite."],
    }]
    parsed["_ordered_sections"] = ["summary", "skills", "projects", "education", "certifications"]

    pdf = _pdf_text(render_pdf_from_structured(parsed))
    docx = _docx_text_in_order(render_docx_from_structured(parsed))

    for output in (pdf, docx):
        assert "INTERNSHIPS" in output
        assert "Example Labs" in output
        assert "Implemented two API endpoints" in output


@pytest.mark.asyncio
async def test_approved_content_matches_finalized_structure_and_pdf_docx_exports(db, settings):
    original = "Built a FastAPI service using Python for internal reporting."
    approved_text = "Engineered a FastAPI service using Python for internal reporting."
    changes = [
        _change("approved-exp", "EXPERIENCE", original, approved_text, "APPROVED"),
        _change("rejected-skill", "SKILLS", "", "Kubernetes", "REJECTED", "KEYWORD_INJECTION"),
        _change("pending-project", "PROJECTS", "", "Launched a 95% faster payments platform.", "PENDING"),
    ]
    strategy = {
        "template_family": "ATS_PROFESSIONAL",
        "template_variant": "executive",
        "page_budget": 2,
        "section_order": ["education", "projects", "experience", "skills", "summary", "certifications"],
    }
    user_id, user, _, version = await _make_version(db, settings, changes=changes, strategy=strategy)

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )
    assert finalized["is_finalized"] is True
    final_structured_text = " ".join(finalized["parsed"]["experience_raw"] + finalized["parsed"]["skills"])
    assert approved_text in final_structured_text
    assert "Kubernetes" not in final_structured_text
    assert "95% faster" not in final_structured_text
    assert finalized["parsed"]["_ordered_sections"] == finalized["resume_strategy"]["section_order"]

    pdf_response = await tailoring_routes.export_pdf(
        str(version["_id"]), template=None, current_user=user, db=db
    )
    docx_response = await tailoring_routes.export_docx(
        str(version["_id"]), template=None, current_user=user, db=db
    )
    pdf_text = _pdf_text(pdf_response.body)
    docx_text = _docx_text_in_order(docx_response.body)
    headings = [
        "EDUCATION",
        "PROJECTS",
        "PROFESSIONAL EXPERIENCE",
        "TECHNICAL SKILLS",
        "PROFESSIONAL SUMMARY",
        "CERTIFICATIONS",
    ]
    for exported_text in (pdf_text, docx_text):
        assert approved_text in exported_text
        assert "Kubernetes" not in exported_text
        assert "95% faster" not in exported_text
        positions = [exported_text.index(heading) for heading in headings]
        assert positions == sorted(positions)


@pytest.mark.asyncio
async def test_draft_preview_rebuilds_from_master_and_omits_rejected_proposals(db, settings):
    original_summary = "Backend engineer building reliable services."
    proposed_summary = "Backend engineer experienced with Python and FastAPI services."
    user_id, user, _, version = await _make_version(
        db,
        settings,
        changes=[
            _change("summary-change", "SUMMARY", original_summary, proposed_summary, "APPROVED"),
            _change("skill-pending", "SKILLS", "", "Kubernetes", "PENDING", "KEYWORD_INJECTION"),
        ],
    )
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]},
        {
            "$set": {
                "structured": {
                    "summary": {
                        "change_id": "summary-change",
                        "original": original_summary,
                        "proposed": proposed_summary,
                    },
                    "skills": {"additions": [{"change_id": "skill-pending", "skill": "Kubernetes"}]},
                },
                "parsed.summary": proposed_summary,
                "parsed.skills": ["Python", "FastAPI", "Kubernetes"],
            }
        },
    )

    approved_preview = await tailoring_routes.preview_pdf(
        str(version["_id"]), template="modern", current_user=user, db=db
    )
    assert proposed_summary in _pdf_text(approved_preview.body)
    assert "Kubernetes" not in _pdf_text(approved_preview.body)
    assert "DRAFT PREVIEW - NOT FINALIZED" in _pdf_text(approved_preview.body)
    assert approved_preview.headers["X-Resume-Finalized"] == "false"

    await tailoring_repo.update_change_status(
        db, user_id, str(version["_id"]), "summary-change", "REJECTED"
    )
    rejected_preview = await tailoring_routes.preview_pdf(
        str(version["_id"]), template="modern", current_user=user, db=db
    )
    preview_text = _pdf_text(rejected_preview.body)

    assert original_summary in preview_text
    assert proposed_summary not in preview_text
    assert "Kubernetes" not in preview_text
    assert "DRAFT PREVIEW - NOT FINALIZED" in preview_text
    assert rejected_preview.headers["X-Resume-Finalized"] == "false"


@pytest.mark.asyncio
async def test_draft_preview_reparses_pinned_source_and_excludes_unsupported_project_technology(db, settings):
    source_text = """Nina Candidate
Seattle, WA | nina@example.com | +1 555 010 0100

PROFESSIONAL SUMMARY
Information science student with software project experience.

EDUCATION
B.E. in Information Science and Engineering
North University | Aug 2022 - May 2026
Pre-University Course (Science)
City College | Jun 2020 - May 2022

TECHNICAL SKILLS
Languages
Python, Java, SQL
Backend
Flask, FastAPI
Databases and Tools
MySQL, Git

PROJECTS
Library Records CLI
Feb 2024 - Apr 2024 | Java, MySQL
Created a command-line application to manage library records using prepared SQL statements.

INTERNSHIP EXPERIENCE
Software Development Intern - Supervised Training Lab
May 2025 - Jul 2025 | Hybrid
Implemented two API endpoints in a supervised training project using Flask and SQLite.

ACHIEVEMENTS
Department Research Showcase
2024
Received second place for a database project.

LANGUAGES
English, Kannada, Hindi

ADDITIONAL INFORMATION
Availability
Available for entry-level full-time roles from July 2026.
"""
    original = "Created a command-line application to manage library records using prepared SQL statements."
    unsupported = "Built a Python-based CLI tool to manage library records using prepared SQL statements."
    user_id, user, master, version = await _make_version(
        db,
        settings,
        changes=[_change("project-python", "PROJECTS", original, unsupported, "APPROVED")],
    )
    stale_parsed = _resume_data()
    stale_parsed.update({
        "skills_categorized": [],
        "languages": ["Backend", "FastAPI", "English", "Kannada", "Hindi"],
        "internships": [
            {"company": "Supervised Training Lab", "role": "Software Development Intern", "bullets": []},
            {"company": "Hybrid", "role": "Software Engineer", "dates": "May 2025 - Jul 2025", "bullets": []},
        ],
        "projects_raw": [{
            "title": "Library Records CLI",
            "tech_stack": "Feb 2024 - Apr 2024 | Java, MySQL",
            "bullets": [original],
        }],
        "education_raw": [{
            "institution": "Pre-University Course (Science",
            "degree": "Degree / Studies",
            "dates": "Jun 2020 - May 2022",
        }],
    })
    await db[Collections.MASTER_RESUMES].update_one(
        {"_id": master["_id"]},
        {"$set": {"raw_text": source_text, "parsed": stale_parsed}},
    )
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]},
        {"$set": {"structured.project_bullets": [{
            "change_id": "project-python",
            "bullet_index": 0,
            "original": original,
            "proposed": unsupported,
        }]}},
    )

    response = await tailoring_routes.preview_pdf(
        str(version["_id"]), template="modern", current_user=user, db=db
    )
    preview_text = _pdf_text(response.body)
    internship_text = preview_text.split("INTERNSHIPS", 1)[1].split("PROJECTS", 1)[0]
    language_text = preview_text.split("LANGUAGES", 1)[1].split("ADDITIONAL INFORMATION", 1)[0]

    assert "Software Development Intern" in internship_text
    assert "Software Engineer" not in internship_text
    assert "Python-based CLI" not in preview_text
    assert "Java, MySQL" in preview_text
    assert "Feb 2024 - Apr 2024" in preview_text
    assert "Pre-University Course (Science)" in preview_text
    assert "Degree / Studies" not in preview_text
    assert "Backend" not in language_text
    assert "FastAPI" not in language_text
    assert all(language in language_text for language in ("English", "Kannada", "Hindi"))
    assert "Languages:" in preview_text
    assert "Backend:" in preview_text
    assert response.headers["X-Resume-Excluded-Changes"] == "project-python"
    assert "DRAFT PREVIEW - NOT FINALIZED" in preview_text

    stored_master = await db[Collections.MASTER_RESUMES].find_one({"_id": master["_id"]})
    assert stored_master["parsed"]["education_raw"][0]["degree"] == "Degree / Studies"
    assert stored_master["parsed"]["languages"][0] == "Backend"

    with pytest.raises(tailoring_services.TailoredResumeValidationError):
        await tailoring_services.finalize_tailoring(
            db, user_id, str(version["_id"]), settings=settings
        )
    still_unfinalized = await tailoring_repo.get_version(db, user_id, str(version["_id"]))
    assert still_unfinalized["is_finalized"] is False

    await tailoring_repo.update_change_status(
        db, user_id, str(version["_id"]), "project-python", "REJECTED"
    )
    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )
    assert finalized["is_finalized"] is True
    pdf_response = await tailoring_routes.export_pdf(
        str(version["_id"]), template="modern", current_user=user, db=db
    )
    docx_response = await tailoring_routes.export_docx(
        str(version["_id"]), template="modern", current_user=user, db=db
    )
    for exported_text in (_pdf_text(pdf_response.body), _docx_text_in_order(docx_response.body)):
        assert "Seattle, WA" in exported_text
        assert "+1 555 010 0100" in exported_text
        assert "Python-based CLI" not in exported_text
        assert "Java, MySQL" in exported_text
        assert "Feb 2024 - Apr 2024" in exported_text
        assert "Pre-University Course (Science)" in exported_text
        assert "Degree / Studies" not in exported_text
        assert "English" in exported_text and "Kannada" in exported_text and "Hindi" in exported_text
        assert "Backend" not in exported_text.split("LANGUAGES", 1)[1]


@pytest.mark.asyncio
async def test_finalization_revalidates_approved_summary_claims_against_master_source(db, settings):
    source_summary = "Backend engineer building reliable services."
    unsupported_summary = (
        "Software engineer with solid experience building developer tooling, "
        "automated data processing pipelines, and backend platforms."
    )
    user_id, _, _, version = await _make_version(
        db,
        settings,
        changes=[_change("summary-scope", "SUMMARY", source_summary, unsupported_summary, "APPROVED")],
    )

    with pytest.raises(tailoring_services.TailoredResumeValidationError, match="summary-scope"):
        await tailoring_services.finalize_tailoring(
            db, user_id, str(version["_id"]), settings=settings
        )

    stored = await tailoring_repo.get_version(db, user_id, str(version["_id"]))
    assert stored["is_finalized"] is False
    assert stored["changes"][0]["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_manual_editor_changes_survive_finalization_and_export(db, settings):
    original = "Built a FastAPI service using Python for internal reporting."
    approved_text = "Engineered a FastAPI service using Python for internal reporting."
    user_id, user, _, version = await _make_version(
        db,
        settings,
        changes=[_change("approved-exp", "EXPERIENCE", original, approved_text, "APPROVED")],
    )
    edited = _resume_data()
    edited["summary"] = "Backend engineer with supported Python and FastAPI delivery experience."
    edited["skills"] = ["FastAPI", "Python"]

    saved = await tailoring_services.update_parsed_resume(
        db, user_id, str(version["_id"]), edited
    )
    assert saved["manual_edits"]["summary"] == edited["summary"]
    assert saved["is_finalized"] is False

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )

    assert finalized["parsed"]["summary"] == edited["summary"]
    assert finalized["parsed"]["skills"] == edited["skills"]
    assert approved_text in " ".join(finalized["parsed"]["experience_raw"])
    response = await tailoring_routes.export_pdf(
        str(version["_id"]), template=None, current_user=user, db=db
    )
    assert edited["summary"] in _pdf_text(response.body)


@pytest.mark.asyncio
async def test_approved_summary_is_not_overwritten_by_unchanged_editor_snapshot(db, settings):
    approved_summary = "Backend engineer experienced with Python and FastAPI services."
    user_id, _, _, version = await _make_version(
        db,
        settings,
        changes=[_change(
            "approved-summary",
            "SUMMARY",
            "Backend engineer building reliable services.",
            approved_summary,
            "APPROVED",
        )],
    )
    # Saving the unchanged master-based editor snapshot creates no override.
    await tailoring_services.update_parsed_resume(
        db, user_id, str(version["_id"]), _resume_data()
    )

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )

    assert finalized["parsed"]["summary"] == approved_summary


@pytest.mark.asyncio
@pytest.mark.parametrize("exporter", [tailoring_routes.export_pdf, tailoring_routes.export_docx])
async def test_failed_render_integrity_check_blocks_export_with_report(db, settings, monkeypatch, exporter):
    user_id, user, _, version = await _make_version(db, settings)
    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )
    assert finalized["is_finalized"] is True
    monkeypatch.setattr(tailoring_routes, "generate_pdf", lambda *args, **kwargs: b"invalid document")
    monkeypatch.setattr(tailoring_routes, "generate_docx", lambda *args, **kwargs: b"invalid document")

    with pytest.raises(HTTPException) as exc_info:
        await exporter(str(version["_id"]), template=None, current_user=user, db=db)

    assert exc_info.value.status_code == 500
    assert isinstance(exc_info.value.detail, dict)
    assert exc_info.value.detail["report"]
    stored = await tailoring_repo.get_version(db, user_id, str(version["_id"]))
    assert stored["is_finalized"] is True
