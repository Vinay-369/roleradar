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
