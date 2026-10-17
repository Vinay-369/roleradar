"""Regression coverage for independently grounding proposed skill additions."""

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.ai_service.schemas import (
    ChangeStatus,
    SkillAddition,
    SkillsTailoring,
    StructuredTailoringResult,
)
from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.jobs import repositories as jobs_repo
from app.modules.jobs import services as jobs_services
from app.modules.resume import repositories as resume_repo
from app.modules.tailoring import services as tailoring_services


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_skill_addition_grounding_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


async def _generate_with_skill_addition(db, settings, *, skill, source_evidence, extra_resume_text=""):
    user, _ = await auth_services.register_user(
        db, settings, "skill-addition@example.com", "supersecret1", "T", None
    )
    user_id = str(user["_id"])
    resume_text = (
        "T Rao\ntrao@example.com 9876543210\n\nSkills\nPython, FastAPI\n\n"
        "Experience\nBuilt a REST API serving 10,000 requests per day.\n"
        f"{extra_resume_text}\nEducation\nB.Tech CS\n"
    )
    await resume_repo.create_master_resume(
        db,
        user_id,
        version=1,
        file_name="t.pdf",
        file_type="pdf",
        raw_text=resume_text,
        parsed={
            "skills": ["Python", "FastAPI"],
            "experience_raw": ["Built a REST API serving 10,000 requests per day."],
        },
        parseability={"score": 90, "contact_info_found": {}, "likely_multi_column": False},
        recruiter_impact={"score": 80, "quantification_rate": 1.0, "weak_verb_bullets": 0},
    )
    await jobs_services.ensure_seed_loaded(db)
    job = (await jobs_repo.find_jobs(db, {}, limit=1))[0]

    class StubAIService:
        async def generate_resume_rewrite(self, **_kwargs):
            return StructuredTailoringResult(
                skills=SkillsTailoring(
                    additions=[SkillAddition(
                        skill=skill,
                        source_evidence=source_evidence,
                        change_id="skill-addition-1",
                    )]
                )
            )

    version = await tailoring_services.generate_tailoring(
        db, StubAIService(), user_id, job_id=job["id"]
    )
    change = next(c for c in version["changes"] if c["change_id"] == "skill-addition-1")
    return user_id, version, change


@pytest.mark.asyncio
async def test_ai_supplied_source_evidence_cannot_ground_a_fabricated_skill(db, settings):
    user_id, version, change = await _generate_with_skill_addition(
        db,
        settings,
        skill="Kubernetes",
        source_evidence="Used Kubernetes to deploy production services.",
    )

    assert change["status"] == "NEEDS_USER_INPUT"
    assert change["source_evidence"] == "Used Kubernetes to deploy production services."
    assert "independently verified" in change["fabrication_warning"].lower()
    assert "lacks" not in change["fabrication_warning"].lower()

    with pytest.raises(tailoring_services.InvalidChangeStatusError):
        await tailoring_services.set_change_status(
            db,
            user_id,
            str(version["_id"]),
            "skill-addition-1",
            ChangeStatus.APPROVED,
        )

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )
    assert "Kubernetes" not in finalized["parsed"].get("skills", [])


@pytest.mark.asyncio
async def test_resume_supported_skill_addition_can_be_approved_and_finalized(db, settings):
    user_id, version, change = await _generate_with_skill_addition(
        db,
        settings,
        skill="Docker",
        source_evidence="Built Docker images for the service.",
        extra_resume_text="Built Docker images for the service.",
    )

    assert change["status"] == "PENDING"
    assert change.get("fabrication_warning") is None

    await tailoring_services.set_change_status(
        db, user_id, str(version["_id"]), "skill-addition-1", ChangeStatus.APPROVED
    )
    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )

    assert "Docker" in finalized["parsed"]["skills"]


@pytest.mark.asyncio
async def test_absent_keyword_keeps_addition_for_user_input_without_claiming_absence(db, settings):
    _, _, change = await _generate_with_skill_addition(
        db,
        settings,
        skill="Terraform",
        source_evidence="Provisioned infrastructure using Terraform.",
    )

    assert change["status"] == "NEEDS_USER_INPUT"
    assert change["proposed"] == "Terraform"
    assert "could not be independently verified" in change["fabrication_warning"].lower()
    assert "does not mean you lack the skill" in change["fabrication_warning"].lower()
