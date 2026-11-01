"""
These tests generate real PDF/DOCX files (see tests/fixtures/generate.py)
and run them through the actual PyMuPDF/python-docx extraction, the real
structurer, and the real Parseability Engine — proving the pipeline
works on genuine files, not hand-typed strings standing in for them.
"""
import os

import pytest

from app.modules.resume.parsing.parseability import analyze_parseability
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.resume.parsing.text_extraction import (
    CorruptedFileError,
    UnsupportedFileTypeError,
    extract_text_and_layout,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return f.read()


def test_extracts_text_from_single_column_pdf():
    extracted = extract_text_and_layout(_read("good_resume.pdf"), "good_resume.pdf")
    assert "Ananya Rao" in extracted["text"]
    assert "Python" in extracted["text"]
    assert extracted["file_type"] == "pdf"


def test_extracts_text_from_docx():
    extracted = extract_text_and_layout(_read("good_resume.docx"), "good_resume.docx")
    assert "Ananya Rao" in extracted["text"]
    assert extracted["file_type"] == "docx"


def test_rejects_unsupported_file_type():
    with pytest.raises(UnsupportedFileTypeError):
        extract_text_and_layout(b"hello", "resume.txt")


def test_rejects_file_with_wrong_signature():
    with pytest.raises(CorruptedFileError):
        extract_text_and_layout(b"not actually a pdf", "resume.pdf")


def test_structurer_extracts_personal_and_skills():
    extracted = extract_text_and_layout(_read("good_resume.pdf"), "good_resume.pdf")
    structured = structure_resume_text(extracted["text"])
    assert structured["personal"]["email"] == "ananya.rao@example.com"
    assert structured["personal"]["phone"] is not None
    assert "Python" in structured["skills"]
    assert structured["personal"]["github"] is not None


def test_parseability_scores_clean_single_column_resume_highly():
    extracted = extract_text_and_layout(_read("good_resume.pdf"), "good_resume.pdf")
    result = analyze_parseability(
        extracted["text"], extracted["blocks"], extracted["file_type"], extracted["has_tables"]
    )
    assert result.likely_multi_column is False
    assert result.contact_info_found["email"] is True
    assert result.score >= 70


def test_parseability_flags_multi_column_pdf():
    extracted = extract_text_and_layout(_read("two_column_resume.pdf"), "two_column_resume.pdf")
    result = analyze_parseability(
        extracted["text"], extracted["blocks"], extracted["file_type"], extracted["has_tables"]
    )
    assert result.likely_multi_column is True
    assert any(issue.code == "MULTI_COLUMN_LAYOUT" for issue in result.issues)


def test_parseability_flags_near_empty_scanned_pdf():
    extracted = extract_text_and_layout(_read("scanned_like_resume.pdf"), "scanned_like_resume.pdf")
    result = analyze_parseability(
        extracted["text"], extracted["blocks"], extracted["file_type"], extracted["has_tables"]
    )
    assert any(issue.code == "TEXT_TOO_SHORT" for issue in result.issues)
    assert result.score < 70


def test_parseability_flags_docx_tables():
    extracted = extract_text_and_layout(_read("docx_with_table.docx"), "docx_with_table.docx")
    result = analyze_parseability(
        extracted["text"], extracted["blocks"], extracted["file_type"], extracted["has_tables"]
    )
    assert extracted["has_tables"] is True
    assert any(issue.code == "CONTAINS_TABLES" for issue in result.issues)


def test_parseability_flags_missing_email():
    result = analyze_parseability("Some resume with no contact info at all here.", [], "pdf", False)
    assert result.contact_info_found["email"] is False
    assert any(issue.code == "MISSING_EMAIL" for issue in result.issues)


def test_section_header_with_trailing_colon_is_recognized():
    """Regression test: 'Skills:' must be recognized as a header, not
    swallowed as content of the previous section (a real bug reported
    during manual testing)."""
    text = "Name\nSkills:\nPython, FastAPI\n\nProjects:\nBuilt a tool\n"
    structured = structure_resume_text(text)
    assert "Python" in structured["skills"]
    assert "FastAPI" in structured["skills"]
    assert any("Built a tool" in p for p in structured["projects_raw"])
    # The header text itself must never leak into skills as content.
    assert not any("Skills" in s for s in structured["skills"])


def test_one_skill_per_line_is_not_collapsed_into_one_string():
    """Regression test: real PDF extraction often puts one skill per
    line with no delimiter -- these must become separate skill entries,
    not a single merged string."""
    text = "Name\nSkills\nPython\nFastAPI\nMongoDB\nDocker\nExperience\nDid stuff\n"
    structured = structure_resume_text(text)
    assert structured["skills"] == ["Python", "FastAPI", "MongoDB", "Docker"]


def test_categorized_skill_subheadings_are_preserved_separately_from_spoken_languages():
    text = """Jordan Lee
TECHNICAL SKILLS
Languages
Python, Java, SQL
Backend
FastAPI, Flask
Databases and Tools
PostgreSQL, Git
Core Concepts
Data Structures, Operating Systems
PROJECTS
Course Planner
Built a course planner.
LANGUAGES
English, Kannada, Hindi
"""
    structured = structure_resume_text(text)

    assert structured["skills_categorized"] == [
        "Languages: Python, Java, SQL",
        "Backend: FastAPI, Flask",
        "Databases and Tools: PostgreSQL, Git",
        "Core Concepts: Data Structures, Operating Systems",
    ]
    assert structured["languages"] == ["English", "Kannada", "Hindi"]


def test_structural_skill_subheadings_contacts_projects_and_internships_parse_consistently():
    resume_text = """
    Jordan Lee
    Bengaluru, Karnataka, India | jordan@example.com | +91 90000 12345

    EDUCATION
    Bachelor of Science in Information Systems
    Example University, Bengaluru | Aug 2021 - May 2025
    Pre-University Course (Science)
    Example Pre-University College, Karnataka | Jun 2019 - May 2021
    Percentage: 91.2%

    TECHNICAL SKILLS
    Languages
    Python, Java, TypeScript
    Backend
    FastAPI, Flask
    Databases and Tools
    PostgreSQL, Git, pytest

    PROJECTS
    Service Monitor - Reliability Dashboard
    Jan 2025 - Apr 2025 | Python, FastAPI, PostgreSQL
    Built a service monitor for distributed application health.

    INTERNSHIP EXPERIENCE
    Software Development Intern - Example Labs
    May 2024 - Jul 2024 | Hybrid
    Implemented two API endpoints using Flask and SQLite.

    ADDITIONAL INFORMATION
    Availability
    Available for entry-level full-time roles from August 2025.
    Languages
    English, Kannada, Hindi
    """

    structured = structure_resume_text(resume_text)

    assert structured["personal"]["name"] == "Jordan Lee"
    assert structured["personal"]["location"] == "Bengaluru, Karnataka, India"
    assert structured["personal"]["phone"] == "+91 90000 12345"
    assert structured["education"][1]["degree"] == "Pre-University Course (Science)"
    assert "Pre-University College" in structured["education"][1]["institution"]
    assert "Backend" not in structured["skills"]
    assert "Databases and Tools" not in structured["skills"]
    assert set(structured["languages"]) == {"English", "Kannada", "Hindi"}
    assert structured["projects"][0]["dates"] == "Jan 2025 - Apr 2025"
    assert "Python" in structured["projects"][0]["tech_stack"]
    assert len(structured["internships"]) == 1
    assert structured["internships"][0]["company"] == "Example Labs"
    assert structured["internships"][0]["role"] == "Software Development Intern"
    assert structured["internships"][0]["dates"] == "May 2024 - Jul 2024"
    assert structured["internships"][0]["location"] == "Hybrid"


@pytest.mark.asyncio
async def test_four_pillar_audit_integration():
    from mongomock_motor import AsyncMongoMockClient
    from app.core.config import Settings
    from app.modules.resume.services import ingest_resume

    db = AsyncMongoMockClient()["test_db"]
    settings = Settings(MAX_UPLOAD_MB=10)
    pdf_bytes = _read("good_resume.pdf")

    doc = await ingest_resume(
        db=db,
        settings=settings,
        user_id="test_user_123",
        filename="good_resume.pdf",
        file_bytes=pdf_bytes,
    )

    assert doc["version"] == 1
    assert "parseability" in doc
    assert "recruiter_impact" in doc
    assert "action_verbs" in doc
    assert "skills_depth" in doc
    assert "strict_ats_score" in doc
    assert "ats_status" in doc

    assert doc["parseability"]["score"] >= 70
    assert doc["action_verbs"]["score"] >= 50
    assert doc["skills_depth"]["score"] >= 50
    assert doc["strict_ats_score"] >= 50
    assert doc["ats_status"]["status"] in {"passed", "review", "at_risk"}
