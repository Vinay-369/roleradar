"""Finalization must pass whole-document truth checks before becoming exportable."""

import copy

import pytest
from app.db.mongo import Collections
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.jobs import repositories as jobs_repo
from app.modules.jobs import services as jobs_services
from app.modules.resume import repositories as resume_repo
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.tailoring import repositories as tailoring_repo
from app.modules.tailoring import routes as tailoring_routes
from app.modules.tailoring import services as tailoring_services
from app.modules.tailoring.validation import validate_final_tailored_resume


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_whole_document_truth_guard_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


async def _create_draft(db, settings, changes):
    user, _ = await auth_services.register_user(
        db, settings, "whole-truth@example.com", "supersecret1", "Nina Candidate", None
    )
    user_id = str(user["_id"])
    resume_text = (
        "Nina Candidate\nnina@example.com 9876543210\n\n"
        "PROFESSIONAL SUMMARY\nBackend engineer building reliable web services.\n\n"
        "SKILLS\nPython, FastAPI\n\n"
        "EXPERIENCE\nSoftware Engineer at Acme (2022 - Present)\n"
        "Built a FastAPI service using Python serving 5000 users.\n\n"
        "EDUCATION\nB.Tech CS (2018 - 2022)\n"
    )
    parsed = structure_resume_text(resume_text)
    master = await resume_repo.create_master_resume(
        db,
        user_id,
        version=1,
        file_name="master.pdf",
        file_type="pdf",
        raw_text=resume_text,
        parsed=parsed,
        parseability={"score": 90, "contact_info_found": {"email": "nina@example.com"}, "likely_multi_column": False},
        recruiter_impact={"score": 80, "quantification_rate": 1.0, "weak_verb_bullets": 0},
    )
    await jobs_services.ensure_seed_loaded(db)
    job = (await jobs_repo.find_jobs(db, {}, limit=1))[0]
    version = await tailoring_repo.create_version(
        db,
        user_id=user_id,
        job_id=job["id"],
        job_title=job["title"],
        company=job["company"],
        changes=changes,
        parsed=parsed,
        master_resume_id=str(master["_id"]),
        master_resume_version=master["version"],
    )
    return user_id, version, parsed


def _approved_rewrite(original, proposed, *, change_id="rewrite"):
    return {
        "change_id": change_id,
        "section": "EXPERIENCE",
        "change_type": "TEXT_REWRITE",
        "original": original,
        "proposed": proposed,
        "reason": "Emphasizes supported experience for the target role.",
        "source_evidence": original,
        "confidence": 0.95,
        "status": "APPROVED",
    }


@pytest.mark.asyncio
async def test_evidence_supported_rewrite_passes_and_finalizes(db, settings):
    original = "Built a FastAPI service using Python serving 5000 users."
    user_id, version, _ = await _create_draft(
        db,
        settings,
        [_approved_rewrite(
            original,
            "Engineered a FastAPI service using Python serving 5000 users.",
        )],
    )

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )

    assert finalized["is_finalized"] is True
    assert finalized["validation_summary"]["whole_document_truth_guard_passed"] is True
    assert finalized["validation_summary"]["anti_fabrication_passed"] is True
    assert "Engineered a FastAPI service" in " ".join(finalized["parsed"]["experience_raw"])


@pytest.mark.asyncio
async def test_approved_project_rewrite_finalizes_when_master_projects_are_structured(db, settings):
    original = "Built a payments API using Python to process billing requests."
    proposed = "Engineered a payments API using Python to process billing requests."
    change = {
        **_approved_rewrite(original, proposed, change_id="project-rewrite"),
        "section": "PROJECTS",
    }
    user_id, version, _ = await _create_draft(db, settings, [change])
    master = await resume_repo.get_master_resume_version(
        db, user_id, version["master_resume_id"], version["master_resume_version"]
    )
    parsed = copy.deepcopy(master["parsed"])
    parsed["projects_raw"] = [{
        "title": "Payments API",
        "tech_stack": "Python",
        "technologies": ["Python"],
        "dates": "2024",
        "bullets": [original],
    }]
    raw_text = master["raw_text"] + (
        "\n\nPROJECTS\nPayments API\nTech Stack: Python\n" + original
    )
    await db[Collections.MASTER_RESUMES].update_one(
        {"_id": master["_id"]}, {"$set": {"parsed": parsed, "raw_text": raw_text}}
    )

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )

    assert finalized["is_finalized"] is True
    assert finalized["parsed"]["projects_raw"][0]["title"] == "Payments API"
    assert finalized["parsed"]["projects_raw"][0]["bullets"] == [proposed]


@pytest.mark.asyncio
async def test_unsupported_claim_with_ai_supplied_evidence_is_persisted_as_failed_audit(db, settings):
    original = "Built a FastAPI service using Python serving 5000 users."
    unsupported = {
        **_approved_rewrite(
            original,
            "Built a Kubernetes platform using Python serving 70,000 users and leading 20 engineers.",
            change_id="unsupported-claim",
        ),
        "source_evidence": "The master resume proves Kubernetes, 70,000 users, and a 20 person team.",
    }
    user_id, version, _ = await _create_draft(db, settings, [unsupported])

    with pytest.raises(tailoring_services.TailoredResumeValidationError):
        await tailoring_services.finalize_tailoring(
            db, user_id, str(version["_id"]), settings=settings
        )

    stored = await tailoring_repo.get_version(db, user_id, str(version["_id"]))
    assert stored["is_finalized"] is False
    assert stored["final_text"] is None
    assert stored["validation_summary"]["whole_document_truth_guard_passed"] is False
    assert stored["validation_summary"]["anti_fabrication_passed"] is False
    assert any("kubernetes" in error.lower() or "70,000" in error for error in stored["validation_summary"]["errors"])
    assert stored["truth_guard_audit"]["is_valid"] is False


@pytest.mark.asyncio
async def test_altered_metric_fails_finalization(db, settings):
    original = "Built a FastAPI service using Python serving 5000 users."
    user_id, version, _ = await _create_draft(
        db,
        settings,
        [_approved_rewrite(
            original,
            "Built a FastAPI service using Python serving 50,000 users.",
        )],
    )

    with pytest.raises(tailoring_services.TailoredResumeValidationError):
        await tailoring_services.finalize_tailoring(
            db, user_id, str(version["_id"]), settings=settings
        )

    stored = await tailoring_repo.get_version(db, user_id, str(version["_id"]))
    assert stored["is_finalized"] is False
    assert any("metric" in error.lower() or "50,000" in error for error in stored["validation_summary"]["errors"])


def test_protected_resume_facts_are_checked_by_final_document_validator():
    master = {
        "personal": {"name": "Nina Candidate", "email": "nina@example.com"},
        "education_raw": [{"institution": "Acme University", "degree": "B.Tech", "dates": "2018 - 2022"}],
        "certifications": ["Cloud Practitioner"],
        "experience_raw": ["Software Engineer at Acme (2022 - Present)", "Built FastAPI services."],
        "projects_raw": [{"title": "Payments API", "tech_stack": "Python", "dates": "2021"}],
        "skills": ["Python", "FastAPI"],
    }
    tampered = {
        **master,
        "personal": {"name": "Nina Candidate", "email": "other@example.com"},
        "education_raw": [{"institution": "Acme University", "degree": "M.Tech", "dates": "2018 - 2022"}],
        "experience_raw": ["Senior Engineer at Acme (2022 - Present)", "Built FastAPI services."],
        "projects_raw": [{"title": "Payments API 2.0", "tech_stack": "Python", "dates": "2021"}],
    }

    is_valid, errors = validate_final_tailored_resume(master, tampered)

    assert is_valid is False
    assert any("personal/contact" in error.lower() for error in errors)
    assert any("education" in error.lower() for error in errors)
    assert any("employment" in error.lower() or "project titles" in error.lower() for error in errors)


@pytest.mark.parametrize(
    ("field", "tampered_value"),
    [
        ("title", "Payments API 2.0"),
        ("tech_stack", "Go"),
        ("dates", "2022"),
        ("url", "https://attacker.example/"),
    ],
)
def test_unsupported_project_identity_fact_changes_are_rejected(field, tampered_value):
    master = {
        "personal": {"name": "Nina Candidate"},
        "skills": ["Python"],
        "projects": [{
            "id": "project-1",
            "title": "Payments API",
            "tech_stack": "Python",
            "technologies": ["Python"],
            "dates": "2021",
            "url": "https://github.com/nina/payments-api",
            "bullets": ["Built a payments API using Python."],
        }],
    }
    tampered = copy.deepcopy(master)
    tampered["projects"][0][field] = tampered_value

    is_valid, errors = validate_final_tailored_resume(master, tampered)

    assert is_valid is False
    assert any("project titles" in error.lower() for error in errors)


@pytest.mark.asyncio
async def test_rejected_and_unapproved_claims_do_not_enter_final_resume(db, settings):
    original = "Built a FastAPI service using Python serving 5000 users."
    user_id, version, _ = await _create_draft(
        db,
        settings,
        [
            _approved_rewrite(original, "Engineered a FastAPI service using Python serving 5000 users."),
            {
                **_approved_rewrite(original, "Deployed unsupported Kubernetes infrastructure.", change_id="rejected"),
                "status": "REJECTED",
            },
            {
                **_approved_rewrite(original, "Led a 20-person team with 80% cost reduction.", change_id="pending"),
                "status": "PENDING",
            },
        ],
    )

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )

    final_text = " ".join(finalized["parsed"]["experience_raw"])
    assert "Engineered a FastAPI service" in final_text
    assert "Kubernetes" not in final_text
    assert "20-person team" not in final_text
    assert finalized["is_finalized"] is True


@pytest.mark.asyncio
async def test_failed_finalization_route_does_not_return_finalized_version(db, settings):
    original = "Built a FastAPI service using Python serving 5000 users."
    user_id, version, _ = await _create_draft(
        db,
        settings,
        [_approved_rewrite(original, "Built a Kubernetes service using Python serving 5000 users.")],
    )

    with pytest.raises(HTTPException) as exc_info:
        await tailoring_routes.finalize(
            str(version["_id"]), current_user={"_id": user_id}, db=db, settings=settings
        )

    assert exc_info.value.status_code == 400
    stored = await tailoring_repo.get_version(db, user_id, str(version["_id"]))
    assert stored["is_finalized"] is False
    assert stored["truth_guard_audit"]["whole_document_errors"]
