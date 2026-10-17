"""Regression tests for binding finalization to its generated master version."""

import pytest
from bson import ObjectId
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

from app.core.ai_service.schemas import ChangeStatus
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
    return client["roleradar_master_resume_version_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


async def _create_master(db, user_id, version, *, experience_bullet):
    resume_text = (
        "Test Candidate\ntest@example.com 9876543210\n\n"
        "Skills\nPython\n\nExperience\n" + experience_bullet + "\n\nEducation\nB.Tech CS\n"
    )
    return await resume_repo.create_master_resume(
        db,
        user_id,
        version=version,
        file_name=f"v{version}.pdf",
        file_type="pdf",
        raw_text=resume_text,
        parsed={
            "personal": {"name": "Test Candidate", "email": "test@example.com"},
            "skills": ["Python"],
            "experience_raw": [experience_bullet],
            "education_raw": ["B.Tech CS"],
        },
        parseability={"score": 90, "contact_info_found": {"email": "test@example.com"}, "likely_multi_column": False},
        recruiter_impact={"score": 80, "quantification_rate": 0.0, "weak_verb_bullets": 0},
    )


async def _create_draft(db, user_id, job, master, changes=None, recorded_version=None):
    return await tailoring_repo.create_version(
        db,
        user_id=user_id,
        job_id=job["id"],
        job_title=job["title"],
        company=job["company"],
        changes=changes or [],
        parsed=master["parsed"],
        master_resume_id=str(master["_id"]),
        master_resume_version=recorded_version if recorded_version is not None else master["version"],
    )


async def _setup(db, settings):
    user, _ = await auth_services.register_user(
        db, settings, "master-version@example.com", "supersecret1", "Test Candidate", None
    )
    user_id = str(user["_id"])
    master_v1 = await _create_master(
        db, user_id, 1, experience_bullet="Built the V1 experience service using Python."
    )
    await jobs_services.ensure_seed_loaded(db)
    job = (await jobs_repo.find_jobs(db, {}, limit=1))[0]
    return user_id, master_v1, job


@pytest.mark.asyncio
async def test_finalization_uses_recorded_master_after_active_master_changes(db, settings):
    user_id, master_v1, job = await _setup(db, settings)
    draft = await _create_draft(db, user_id, job, master_v1)

    await resume_repo.deactivate_previous(db, user_id)
    await _create_master(
        db, user_id, 2, experience_bullet="Built the current V2 experience service using Python."
    )

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(draft["_id"]), settings=settings
    )

    assert finalized["master_resume_id"] == str(master_v1["_id"])
    assert finalized["master_resume_version"] == 1
    assert finalized["parsed"]["experience_raw"] == ["Built the V1 experience service using Python."]
    assert "Built the V1 experience service using Python." in finalized["final_text"]
    assert "Built the current V2 experience service using Python." not in finalized["final_text"]


@pytest.mark.asyncio
async def test_approved_change_is_applied_to_recorded_master_version(db, settings):
    user_id, master_v1, job = await _setup(db, settings)
    draft = await _create_draft(
        db,
        user_id,
        job,
        master_v1,
        changes=[{
            "change_id": "rewrite-v1-bullet",
            "section": "EXPERIENCE",
            "change_type": "TEXT_REWRITE",
            "original": "Built the V1 experience service using Python.",
            "proposed": "Developed the V1 experience service in Python.",
            "status": ChangeStatus.APPROVED.value,
        }],
    )

    await resume_repo.deactivate_previous(db, user_id)
    await _create_master(
        db, user_id, 2, experience_bullet="Built the current V2 experience service using Python."
    )

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(draft["_id"]), settings=settings
    )

    assert finalized["parsed"]["experience_raw"] == [
        "Developed the V1 experience service in Python."
    ]
    assert "Built the current V2 experience service using Python." not in finalized["final_text"]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_source", ["missing_id", "version_mismatch"])
async def test_missing_recorded_master_version_fails_without_active_fallback(db, settings, missing_source):
    user_id, active_master, job = await _setup(db, settings)
    draft = await _create_draft(db, user_id, job, active_master)
    if missing_source == "missing_id":
        updates = {"master_resume_id": str(ObjectId())}
    else:
        await resume_repo.deactivate_previous(db, user_id)
        await _create_master(
            db, user_id, 2, experience_bullet="Built the current V2 experience service using Python."
        )
        updates = {"master_resume_version": 2}
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": draft["_id"]}, {"$set": updates}
    )

    with pytest.raises(tailoring_services.NoMasterResumeError):
        await tailoring_services.finalize_tailoring(
            db, user_id, str(draft["_id"]), settings=settings
        )

    stored = await tailoring_repo.get_version(db, user_id, str(draft["_id"]))
    assert stored["is_finalized"] is False
    assert stored["final_text"] is None


@pytest.mark.asyncio
async def test_finalize_route_maps_missing_source_version_to_existing_error_response(db, settings):
    user_id, active_master, job = await _setup(db, settings)
    draft = await _create_draft(db, user_id, job, active_master)
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": draft["_id"]}, {"$set": {"master_resume_id": "not-an-object-id"}}
    )

    with pytest.raises(HTTPException) as exc_info:
        await tailoring_routes.finalize(
            str(draft["_id"]), current_user={"_id": user_id}, db=db, settings=settings
        )

    assert exc_info.value.status_code == 400
    stored = await tailoring_repo.get_version(db, user_id, str(draft["_id"]))
    assert stored["is_finalized"] is False
