import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.applications import services as app_services
from app.modules.auth import services as auth_services
from app.modules.jobs import services as jobs_services
from app.modules.resume import repositories as resume_repo


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret")


async def _setup(db, settings):
    user, _ = await auth_services.register_user(db, settings, "apps@example.com", "supersecret1", "A", None)
    user_id = str(user["_id"])
    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    return user_id, jobs[0]["id"]


@pytest.mark.asyncio
async def test_save_application_defaults_to_saved_status(db, settings):
    user_id, job_id = await _setup(db, settings)
    app_doc = await app_services.save_application(db, user_id, job_id, tailored_resume_id=None, notes=None)
    assert app_doc["status"] == "SAVED"
    assert app_doc["job_id"] == job_id


@pytest.mark.asyncio
async def test_duplicate_application_is_rejected(db, settings):
    user_id, job_id = await _setup(db, settings)
    await app_services.save_application(db, user_id, job_id, tailored_resume_id=None, notes=None)
    with pytest.raises(app_services.DuplicateApplicationError):
        await app_services.save_application(db, user_id, job_id, tailored_resume_id=None, notes=None)


@pytest.mark.asyncio
async def test_withdrawn_application_allows_reapplying(db, settings):
    user_id, job_id = await _setup(db, settings)
    first = await app_services.save_application(db, user_id, job_id, tailored_resume_id=None, notes=None)
    await app_services.update_application(db, user_id, str(first["_id"]), {"status": "WITHDRAWN"})

    # Should not raise -- withdrawn applications don't block a fresh one.
    second = await app_services.save_application(db, user_id, job_id, tailored_resume_id=None, notes=None)
    assert second["status"] == "SAVED"


@pytest.mark.asyncio
async def test_package_falls_back_to_master_resume_when_no_tailored_version(db, settings):
    user_id, job_id = await _setup(db, settings)
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="r.pdf", file_type="pdf",
        raw_text="MASTER RESUME TEXT",
        parsed={"skills": []},
        parseability={"score": 80, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {}, "likely_multi_column": False, "word_count": 5},
        recruiter_impact={"score": 70, "bullets_analyzed": 0, "quantified_bullets": 0, "weak_verb_bullets": 0,
                           "quantification_rate": 0, "issues": []},
    )
    app_doc = await app_services.save_application(db, user_id, job_id, tailored_resume_id=None, notes=None)
    package = await app_services.build_application_package(db, user_id, str(app_doc["_id"]))

    assert package["resume_source"] == "master"
    assert package["resume_text"] == "MASTER RESUME TEXT"
    # Smart Apply package prep never submits anything -- it only ever
    # returns text and a checklist for the human to act on.
    assert "apply_url" in package
    assert isinstance(package["checklist"], list)
    assert any("yourself" in step.lower() for step in package["checklist"])


@pytest.mark.asyncio
async def test_package_with_no_resume_at_all_is_honest_about_it(db, settings):
    user_id, job_id = await _setup(db, settings)
    app_doc = await app_services.save_application(db, user_id, job_id, tailored_resume_id=None, notes=None)
    package = await app_services.build_application_package(db, user_id, str(app_doc["_id"]))
    assert package["resume_source"] == "none"
    assert package["resume_text"] is None
