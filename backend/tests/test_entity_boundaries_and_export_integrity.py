"""
Tests for Phase 5 Entity Boundaries / Truth Guard & Phase 6 Export Text Integrity.
"""
import pytest
from app.modules.resume.models import EvidenceUnit
from app.modules.tailoring.export import (
    render_pdf_from_structured,
    verify_export_text_integrity,
)
from app.modules.tailoring.validation import detect_entity_boundary_violations

SAMPLE_STRUCTURED_RESUME = {
    "personal": {
        "name": "VIKAS K",
        "email": "vikas@example.com",
        "phone": "+91 9876543210",
        "location": "Davangere, Karnataka",
    },
    "summary": "Software Engineer with experience in full-stack web and ML.",
    "skills": ["Python", "Flask", "React", "Docker"],
    "skills_categorized": ["Languages: Python, Java", "Tools: Docker, Git"],
    "experience_raw": [
        "Software Engineer at BetaCorp (2024 - Present)",
        "• Architected backend microservices processing 50,000 req/sec.",
    ],
    "projects_raw": [
        {
            "title": "AI Viral Potential Analyzer",
            "tech_stack": "Flask, OpenCV",
            "bullets": ["• Built predictive classification model achieving 91% accuracy across 10,000 samples."],
        },
        {
            "title": "ShopVerse E-Commerce",
            "tech_stack": "React, Node.js",
            "bullets": ["• Engineered payment gateway integration handling $500k in monthly volume."],
        },
    ],
    "education_raw": [
        {
            "institution": "Bapuji Institute of Engineering and Technology",
            "degree": "B.E in Computer Science and Engineering (2023 - 2027)",
            "cgpa": "9.1 / 10.0",
        }
    ],
    "certifications": ["Smart India Hackathon 2024"],
    "achievements": [],
    "languages": ["Telugu", "English", "Kannada", "Hindi"],
    "links": [],
}


def test_detect_entity_boundary_violations():
    ev_proj0 = EvidenceUnit(
        id="ev_proj_0_0",
        section="PROJECTS",
        entity_id="proj_0",
        original_text="Built predictive classification model achieving 91% accuracy.",
        normalized_text="Built predictive classification model achieving 91% accuracy.",
        metrics=["91%"],
    )
    ev_proj1 = EvidenceUnit(
        id="ev_proj_1_0",
        section="PROJECTS",
        entity_id="proj_1",
        original_text="Engineered payment gateway integration handling $500k in monthly volume.",
        normalized_text="Engineered payment gateway integration handling $500k in monthly volume.",
        metrics=["$500k"],
    )
    all_evs = [ev_proj0, ev_proj1]

    # Valid rewrite for proj_0 preserving its own metric:
    valid_rewrite = "Architected predictive classification model achieving 91% accuracy."
    violations = detect_entity_boundary_violations("proj_0", valid_rewrite, all_evs)
    assert len(violations) == 0

    # Cross-entity metric migration: attempting to put proj_1's $500k into proj_0!
    bad_rewrite = "Architected predictive classification model processing $500k transactions."
    violations = detect_entity_boundary_violations("proj_0", bad_rewrite, all_evs)
    assert len(violations) >= 1
    assert any("$500k" in v for v in violations)


def test_verify_export_text_integrity():
    pdf_bytes = render_pdf_from_structured(SAMPLE_STRUCTURED_RESUME, candidate_name="VIKAS K", template="modern")
    assert len(pdf_bytes) > 1000

    # Verify that candidate facts, institutions, and metrics survive round-trip
    required_facts = [
        "VIKAS K",
        "vikas@example.com",
        "AI Viral Potential Analyzer",
        "ShopVerse E-Commerce",
        "Bapuji Institute of Engineering and Technology",
        "91%",
        "$500k",
        "Telugu, English, Kannada, Hindi",
    ]

    is_valid, missing = verify_export_text_integrity(pdf_bytes, file_type="pdf", required_facts=required_facts)
    assert is_valid is True, f"Missing facts in exported PDF: {missing}"


def test_truth_guard_blocks_fabricated_technologies_and_metrics():
    from app.modules.tailoring.services import _truth_guard_warning
    from app.modules.resume.models import CandidateProfile

    profile = CandidateProfile.from_parsed_dict(SAMPLE_STRUCTURED_RESUME)
    master_skills = SAMPLE_STRUCTURED_RESUME["skills"]

    # 1. Fabricating a new unverified technology (e.g. adding Kubernetes / AWS when candidate only has Docker)
    orig_b = "Built predictive classification model achieving 91% accuracy."
    bad_tech_b = "Built predictive classification model using Kubernetes and AWS achieving 91% accuracy."
    warning = _truth_guard_warning(
        orig_b,
        bad_tech_b,
        jd_text="Requirements: AWS, Kubernetes",
        master_skills=master_skills,
        entity_id="proj_0",
        all_evidence_units=profile.evidence_units,
    )
    assert warning is not None
    assert "Kubernetes" in warning or "AWS" in warning or "Technical competency" in warning

    # 2. Fabricating a new unverified metric (e.g. inventing 99.99% or $1M when not in original)
    bad_metric_b = "Built predictive classification model achieving 99.99% accuracy."
    warning = _truth_guard_warning(
        orig_b,
        bad_metric_b,
        jd_text="Requirements: High accuracy ML",
        master_skills=master_skills,
        entity_id="proj_0",
        all_evidence_units=profile.evidence_units,
    )
    assert warning is not None
    assert "99.99%" in warning or "Measurable claim" in warning


def test_truth_guard_blocks_cross_project_metric_contamination():
    from app.modules.tailoring.services import _truth_guard_warning
    from app.modules.resume.models import CandidateProfile

    profile = CandidateProfile.from_parsed_dict(SAMPLE_STRUCTURED_RESUME)
    master_skills = SAMPLE_STRUCTURED_RESUME["skills"]

    # Candidate has $500k in proj_1 (ShopVerse) and 50,000 req/sec in exp_0 (BetaCorp).
    # Attempting to move $500k into proj_0 (AI Viral Potential Analyzer):
    orig_proj0 = "Built predictive classification model achieving 91% accuracy across 10,000 samples."
    contaminated_proj0 = "Built predictive classification model handling $500k in monthly volume."

    warning = _truth_guard_warning(
        orig_proj0,
        contaminated_proj0,
        jd_text="Requirements: High volume financial processing",
        master_skills=master_skills,
        entity_id="proj_0",
        all_evidence_units=profile.evidence_units,
    )
    assert warning is not None
    assert "$500k" in warning or "another entity" in warning or "Measurable claim" in warning
