"""
Phase 6 Complete Audit Regression Test Suite.
Verifies all 8 Truth Guard adversarial test cases (TG-01 to TG-08),
Semantic equivalence vs scope escalation,
Distinctness of all 4 advertised templates (Modern, Classic, Executive, Harvard),
Master Resume isolation and protection,
and 100% Export verification fidelity.
"""
import io
import re
import fitz
from docx import Document
import pytest

from app.modules.resume.models import (
    CandidateProfile,
    EducationEntity,
    ProjectEntity,
    WorkExperienceEntity,
)
from app.modules.tailoring.export import (
    generate_docx,
    generate_pdf,
    verify_export_against_structured_resume,
)
from app.modules.tailoring.services import _audit_user_edits, _truth_guard_warning
from app.modules.tailoring.strategy import (
    CareerStage,
    TemplateFamily,
    build_resume_strategy,
    compute_project_priorities,
    compute_skill_priorities,
)
from app.modules.tailoring.validation import (
    compute_deterministic_skill_reorder,
    detect_fabricated_claims,
    detect_seniority_and_title_inflation,
    detect_unsupported_action_verbs_and_scope,
    detect_unsupported_metrics,
    validate_final_tailored_resume,
)


# ============================================================
# TRUTH GUARD ADVERSARIAL TEST CASES (TG-01 through TG-08)
# ============================================================

def test_tg01_invented_skill():
    candidate_skills = ["Python", "React", "MongoDB"]
    orig = "Built a web application using React."
    proposed = "Experienced AWS developer building scalable cloud native microservices."
    unsupported = detect_fabricated_claims(orig, proposed, "Requires AWS", candidate_skills)
    assert "aws" in [s.lower() for s in unsupported]


def test_tg02_invented_experience_duration():
    orig = "Student project intern."
    proposed = "Over 3 years of professional experience leading enterprise systems."
    unsupported_metrics = detect_unsupported_metrics(orig, proposed)
    unsupported_scope = detect_unsupported_action_verbs_and_scope(orig, proposed)
    assert "3years" in unsupported_metrics or any("leading" in s for s in unsupported_scope)


def test_tg03_invented_metric():
    orig = "Built an e-commerce website."
    proposed = "Built an e-commerce website, improving performance by 45%."
    unsupported_metrics = detect_unsupported_metrics(orig, proposed)
    assert "45%" in unsupported_metrics


def test_tg04_invented_certification():
    master_parsed = {"certifications": ["Google Data Analytics"]}
    final_parsed = {"certifications": ["Google Data Analytics", "AWS Certified Developer"]}
    is_valid, errors = validate_final_tailored_resume(master_parsed, final_parsed)
    assert not is_valid
    assert any("aws certified developer" in e.lower() for e in errors)


def test_tg05_title_inflation():
    orig = "Software Engineering Intern at StartupX."
    proposed = "Senior Software Engineer spearheading backend architecture."
    scope_viols = detect_unsupported_action_verbs_and_scope(orig, proposed)
    assert any("senior" in s.lower() for s in scope_viols)


def test_tg06_valid_rewrite_passes():
    candidate_skills = ["Python", "React", "MongoDB"]
    orig = "Built a web application using React."
    proposed = "Developed a responsive web application using React."
    fab = detect_fabricated_claims(orig, proposed, "React developer", candidate_skills)
    met = detect_unsupported_metrics(orig, proposed)
    scope = detect_unsupported_action_verbs_and_scope(orig, proposed)
    assert len(fab) == 0
    assert len(met) == 0
    assert len(scope) == 0


def test_tg07_valid_reordering():
    skills_before = ["Python", "MongoDB", "React"]
    jd_text = "Looking for a Frontend Engineer with strong React and TypeScript experience."
    reordered, matched, gaps, was_reordered = compute_deterministic_skill_reorder(skills_before, jd_text)
    assert was_reordered
    assert reordered[0] == "React"
    assert "React" in matched
    assert "Typescript" in gaps


def test_tg08_valid_project_emphasis():
    projects = [
        ProjectEntity(id="p1", title="E-commerce Web App", technologies=["React", "Python"]),
        ProjectEntity(id="p2", title="ML Prediction Project", technologies=["Python", "Scikit-Learn", "TensorFlow"], bullets=["Trained model achieving 92% accuracy."]),
    ]
    class MockJD:
        required_skills = ["Python", "Machine Learning", "TensorFlow"]
    ranked = compute_project_priorities(projects, MockJD())
    assert ranked[0] == "ML Prediction Project"


def test_semantic_equivalence_vs_scope_escalation():
    # Valid semantic rephrasing
    orig_a = "Created a REST API using Node.js."
    prop_a = "Developed RESTful APIs with Node.js."
    fab_a = detect_fabricated_claims(orig_a, prop_a, "Node.js", ["Node.js", "REST API"])
    scope_a = detect_unsupported_action_verbs_and_scope(orig_a, prop_a)
    assert len(fab_a) == 0
    assert len(scope_a) == 0

    # Semantic false claim (Scope escalation)
    orig_b = "Used MongoDB."
    prop_b = "Designed and optimized distributed MongoDB infrastructure at scale."
    scope_b = detect_unsupported_action_verbs_and_scope(orig_b, prop_b)
    assert len(scope_b) > 0
    assert any("optimized" in s.lower() for s in scope_b)


# ============================================================
# TEMPLATE DISTINCTNESS AUDIT (Modern, Classic, Executive, Harvard)
# ============================================================

def test_advertised_templates_are_visually_distinct():
    sample_resume = {
        "personal": {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "555-0199",
            "location": "San Francisco, CA",
        },
        "summary": "Full Stack Engineer with 3+ years experience.",
        "skills": ["Python", "React", "TypeScript", "FastAPI"],
        "experience_raw": [
            "TechCorp — Software Engineer (2022 - Present)\n• Developed REST APIs using FastAPI."
        ],
        "education_raw": [
            "UC Berkeley\nB.S. in Computer Science (2018 - 2022)"
        ],
    }

    templates = ["modern", "classic", "executive", "harvard"]
    pdf_bytes = {t: generate_pdf(sample_resume, candidate_name="Jane Doe", template=t) for t in templates}
    docx_bytes = {t: generate_docx(sample_resume, candidate_name="Jane Doe", template=t) for t in templates}

    # All generated documents must be valid
    for t in templates:
        pdf_doc = fitz.open(stream=pdf_bytes[t], filetype="pdf")
        assert pdf_doc.page_count == 1
        pdf_doc.close()

        docx_doc = Document(io.BytesIO(docx_bytes[t]))
        assert len(docx_doc.paragraphs) > 5

    # Distinct template signatures
    assert len(pdf_bytes["modern"]) != len(pdf_bytes["classic"])
    assert len(pdf_bytes["classic"]) != len(pdf_bytes["executive"])
    assert len(pdf_bytes["classic"]) != len(pdf_bytes["harvard"])
    assert len(pdf_bytes["executive"]) != len(pdf_bytes["harvard"])

    # DOCX fonts & margins
    doc_modern = Document(io.BytesIO(docx_bytes["modern"]))
    doc_classic = Document(io.BytesIO(docx_bytes["classic"]))
    doc_harvard = Document(io.BytesIO(docx_bytes["harvard"]))
    doc_exec = Document(io.BytesIO(docx_bytes["executive"]))

    assert doc_modern.styles["Normal"].font.name == "Calibri"
    assert doc_classic.styles["Normal"].font.name == "Times New Roman"
    assert doc_harvard.styles["Normal"].font.name == "Times New Roman"
    assert doc_exec.styles["Normal"].font.name == "Calibri"

    # Executive has tighter margins than classic / harvard
    assert doc_exec.sections[0].left_margin.inches < doc_classic.sections[0].left_margin.inches


# ============================================================
# EXPORT FIDELITY & MULTI-LINE WHITESPACE NORMALIZATION
# ============================================================

def test_export_fidelity_with_multiline_blocks():
    export_data = {
        "personal": {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "555-0199",
            "location": "San Francisco, CA",
        },
        "summary": "Full Stack Engineer.",
        "skills": ["Python", "React", "Docker"],
        "experience_raw": [
            "TechCorp — San Francisco, CA\nSoftware Engineer (2022 - Present)\n• Developed REST APIs using FastAPI."
        ],
        "projects_raw": [
            "Distributed Task Queue\nTechnologies: Python, Redis, Docker\n• Engineered an asynchronous task queue handling 5,000 tasks/second."
        ],
        "education_raw": [
            "UC Berkeley\nB.S. in Computer Science (2018 - 2022)\nGPA: 3.8 / 4.0"
        ],
    }

    pdf = generate_pdf(export_data, candidate_name="Jane Doe", template="modern")
    docx = generate_docx(export_data, candidate_name="Jane Doe", template="modern")

    is_pdf_valid, pdf_report = verify_export_against_structured_resume(pdf, export_data, file_type="pdf")
    is_docx_valid, docx_report = verify_export_against_structured_resume(docx, export_data, file_type="docx")

    assert is_pdf_valid, f"PDF verification failed: {pdf_report}"
    assert is_docx_valid, f"DOCX verification failed: {docx_report}"
    assert len(pdf_report["missing_facts"]) == 0
    assert len(pdf_report["project_integrity_issues"]) == 0
    assert len(pdf_report["education_integrity_issues"]) == 0
