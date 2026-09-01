"""
Dedicated Test Suite for Phase 7: Tailoring Approval Pipeline & Whole-Document Truth Guard Audit.
Validates:
- valid rewrite
- invented metric
- altered metric
- invented technology
- invented outcome
- invented responsibility
- unsupported certification
- NEEDS_USER_INPUT enforcement against direct API approval bypass
- cross-project claim blocking
"""
import pytest
from mongomock_motor import AsyncMongoMockClient
from app.core.ai_service.schemas import ChangeStatus, ChangeType
from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.jobs import services as jobs_services
from app.modules.jobs import repositories as jobs_repo
from app.modules.resume import repositories as resume_repo
from app.modules.tailoring import services as tailoring_services
from app.modules.tailoring.validation import (
    detect_entity_boundary_violations,
    detect_fabricated_claims,
    detect_unsupported_metrics,
    validate_final_tailored_resume,
)


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


@pytest.fixture
def master_resume_dict():
    return {
        "personal": {
            "name": "VIKAS K",
            "email": "vikas@example.com",
            "phone": "+91 9876543210",
            "location": "Davangere, Karnataka",
        },
        "summary": "Full Stack Engineer with experience in Python, FastAPI, and React.",
        "skills": ["Python", "FastAPI", "React", "Docker", "PostgreSQL", "REST APIs"],
        "skills_categorized": ["Languages: Python, JavaScript", "Tools: Docker, Git"],
        "experience_raw": [
            "Software Engineer at Acme Corp (2023 - Present)",
            "• Engineered high-performance backend microservices in Python, reducing latency by 40%.",
        ],
        "projects_raw": [
            {
                "title": "AI Viral Potential Analyzer",
                "tech_stack": "Flask, OpenCV",
                "bullets": ["• Built computer vision pipeline achieving 91% accuracy across 10,000 video samples."],
            },
            {
                "title": "ShopVerse Platform",
                "tech_stack": "React, Node.js",
                "bullets": ["• Deployed cloud payment architecture processing $500k in monthly volume."],
            },
        ],
        "education_raw": [
            {
                "institution": "Bapuji Institute of Engineering and Technology",
                "degree": "B.E in Computer Science (2023 - 2027)",
                "cgpa": "9.1 / 10.0",
            }
        ],
        "certifications": ["Smart India Hackathon Finalist 2024"],
        "achievements": [],
        "languages": ["Telugu", "English", "Kannada", "Hindi"],
    }


def test_valid_rewrite_preserves_truth_and_metrics(master_resume_dict):
    orig = "• Engineered high-performance backend microservices in Python, reducing latency by 40%."
    valid_proposed = "• Architected resilient backend REST microservices utilizing Python and FastAPI, decreasing latency by 40%."
    
    # 1. Truth Guard checks
    fabricated_terms = detect_fabricated_claims(orig, valid_proposed, "Requirements: Python, FastAPI", master_resume_dict["skills"])
    assert len(fabricated_terms) == 0

    unsupported_metrics = detect_unsupported_metrics(orig, valid_proposed)
    assert len(unsupported_metrics) == 0


def test_invented_metric_is_detected_and_rejected():
    orig = "• Engineered backend microservices in Python."
    # Fabricating a metric (40% or 10,000 req/sec) not in original:
    invented_metric_proposed = "• Engineered backend microservices in Python, reducing latency by 40%."

    unsupported_metrics = detect_unsupported_metrics(orig, invented_metric_proposed)
    assert len(unsupported_metrics) >= 1
    assert "40%" in unsupported_metrics


def test_altered_metric_is_detected_and_rejected():
    orig = "• Engineered backend microservices in Python, reducing latency by 40%."
    # Arbitrarily inflating 40% to 80%:
    altered_metric_proposed = "• Engineered backend microservices in Python, reducing latency by 80%."

    unsupported_metrics = detect_unsupported_metrics(orig, altered_metric_proposed)
    assert len(unsupported_metrics) >= 1
    assert "80%" in unsupported_metrics


def test_invented_technology_is_detected_and_rejected(master_resume_dict):
    orig = "• Engineered backend microservices in Python, reducing latency by 40%."
    # Fabricating unevidenced technologies: Kubernetes and Terraform
    bad_tech_proposed = "• Engineered backend microservices in Python using Kubernetes and Terraform, reducing latency by 40%."

    fabricated_terms = detect_fabricated_claims(
        orig, bad_tech_proposed, "Requirements: Kubernetes, Terraform", master_resume_dict["skills"]
    )
    assert len(fabricated_terms) >= 1
    assert any(t in ["kubernetes", "terraform"] for t in fabricated_terms)


def test_unsupported_certification_blocked_in_final_validation(master_resume_dict):
    final_with_invented_cert = dict(master_resume_dict)
    final_with_invented_cert["certifications"] = [
        "Smart India Hackathon Finalist 2024",
        "AWS Certified Solutions Architect Professional",  # Fabricated cert!
    ]

    is_valid, errors = validate_final_tailored_resume(master_resume_dict, final_with_invented_cert)
    assert is_valid is False
    assert len(errors) >= 1
    assert any("certification" in err.lower() and "aws" in err.lower() for err in errors)


def test_cross_project_claim_is_blocked():
    from app.modules.resume.models import EvidenceUnit

    ev_proj0 = EvidenceUnit(
        id="ev_0", section="PROJECTS", entity_id="proj_0",
        original_text="Built computer vision pipeline achieving 91% accuracy.",
        normalized_text="Built computer vision pipeline achieving 91% accuracy.",
        metrics=["91%"],
    )
    ev_proj1 = EvidenceUnit(
        id="ev_1", section="PROJECTS", entity_id="proj_1",
        original_text="Deployed cloud payment architecture processing $500k in monthly volume.",
        normalized_text="Deployed cloud payment architecture processing $500k in monthly volume.",
        metrics=["$500k"],
    )

    # Attempting to move $500k from proj_1 to proj_0:
    cross_claim = "Built computer vision pipeline processing $500k in monthly video traffic."
    violations = detect_entity_boundary_violations("proj_0", cross_claim, [ev_proj0, ev_proj1])
    assert len(violations) >= 1
    assert any("$500k" in v for v in violations)


@pytest.mark.asyncio
async def test_needs_user_input_cannot_be_approved_via_backend_api(db, settings):
    """
    Direct API attempt to approve a change flagged as NEEDS_USER_INPUT MUST be rejected with HTTP 400.
    """
    user, _ = await auth_services.register_user(db, settings, "api_guard_test@example.com", "supersecret1", "Tester", None)
    user_id = str(user["_id"])

    # Create master resume
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="master.pdf", file_type="pdf",
        raw_text="Vikas\nvikas@example.com\n\nSKILLS\nPython, Docker\n\nEXPERIENCE\nDev at ScaleTech\n• Built APIs in Python",
        parsed={"skills": ["Python", "Docker"], "experience_raw": ["Built APIs in Python"]},
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {"email": True, "phone": True}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 50, "bullets_analyzed": 1, "quantified_bullets": 0, "weak_verb_bullets": 0,
                           "quantification_rate": 0.0, "issues": []},
    )

    await jobs_services.ensure_seed_loaded(db)
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    job = jobs[0]

    # Create a version containing a NEEDS_USER_INPUT change
    from app.modules.tailoring import repositories as tailoring_repo
    version = await tailoring_repo.create_version(
        db,
        user_id,
        job["id"],
        job["title"],
        job["company"],
        changes=[
            {
                "change_id": "chg_unverified_aws",
                "section": "EXPERIENCE",
                "change_type": ChangeType.KEYWORD_INJECTION.value,
                "original": "Built APIs in Python",
                "proposed": "Built cloud APIs in Python using AWS EKS and Kafka",
                "status": ChangeStatus.NEEDS_USER_INPUT.value,
                "fabrication_warning": "Technical competency (AWS, Kafka) not found in master resume background",
            }
        ],
        sections_evaluated=["EXPERIENCE"],
        sections_changed=["EXPERIENCE"],
        unmatched_gaps=["AWS", "Kafka"],
        parsed={"skills": ["Python", "Docker"], "experience_raw": ["Built APIs in Python"]},
    )
    version_id = str(version["_id"])

    # Attempting to bypass frontend and approve NEEDS_USER_INPUT directly via backend:
    with pytest.raises(tailoring_services.InvalidChangeStatusError) as exc_info:
        await tailoring_services.set_change_status(
            db, user_id, version_id, "chg_unverified_aws", ChangeStatus.APPROVED
        )

    assert "lacks verified source evidence" in str(exc_info.value)
