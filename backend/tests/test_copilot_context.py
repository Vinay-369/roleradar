import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.applications import services as app_services
from app.modules.auth import services as auth_services
from app.modules.chatbot.context import build_copilot_context
from app.modules.jobs import services as jobs_services
from app.modules.profile import services as profile_services
from app.modules.profile.schemas import AutoApplySettings, CandidateCategory, OnboardingRequest
from app.modules.resume import repositories as resume_repo


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret")


@pytest.mark.asyncio
async def test_context_is_honest_when_nothing_exists_yet(db, settings):
    user, _ = await auth_services.register_user(db, settings, "empty@example.com", "supersecret1", "E", None)
    context = await build_copilot_context(str(user["_id"]), db)

    assert context.profile_summary is None
    assert context.resume_intelligence is None
    assert context.top_job_matches == []
    assert any("onboarding" in note.lower() for note in context.missing_context_notes)
    assert any("resume" in note.lower() for note in context.missing_context_notes)


@pytest.mark.asyncio
async def test_context_reflects_real_profile_and_resume_once_they_exist(db, settings):
    user, _ = await auth_services.register_user(db, settings, "full@example.com", "supersecret1", "F", None)
    user_id = str(user["_id"])

    await profile_services.complete_onboarding(db, user_id, OnboardingRequest(
        category=CandidateCategory.FRESHER,
        target_roles=["Backend Developer"],
        min_lpa=4,
        auto_apply_settings=AutoApplySettings(),
        consent_text="I consent.",
    ))

    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="r.pdf", file_type="pdf",
        raw_text="Python FastAPI",
        parsed={"skills": ["Python", "FastAPI"]},
        parseability={"score": 88, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {}, "likely_multi_column": False, "word_count": 5},
        recruiter_impact={"score": 75, "bullets_analyzed": 0, "quantified_bullets": 0, "weak_verb_bullets": 0,
                           "quantification_rate": 0, "issues": []},
    )

    await jobs_services.ensure_seed_loaded(db)

    context = await build_copilot_context(user_id, db)

    assert context.profile_summary["category"] == "FRESHER"
    assert context.profile_summary["target_roles"] == ["Backend Developer"]
    assert context.resume_intelligence["skills"] == ["Python", "FastAPI"]
    assert context.resume_intelligence["parseability_score"] == 88
    assert len(context.top_job_matches) > 0
    # No fabricated data: every match must reference a real seeded job.
    from app.modules.jobs import repositories as jobs_repo
    real_job_ids = {j["id"] for j in await jobs_repo.find_jobs(db, {}, limit=100)}
    assert all(m["job_id"] in real_job_ids for m in context.top_job_matches)


@pytest.mark.asyncio
async def test_context_never_leaks_another_users_applications(db, settings):
    user_a, _ = await auth_services.register_user(db, settings, "a@example.com", "supersecret1", "A", None)
    user_b, _ = await auth_services.register_user(db, settings, "b@example.com", "supersecret1", "B", None)
    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    job = (await jobs_repo.find_jobs(db, {}, limit=1))[0]

    await app_services.save_application(db, str(user_a["_id"]), job["id"], None, None)

    context_b = await build_copilot_context(str(user_b["_id"]), db)
    assert context_b.active_applications == []
