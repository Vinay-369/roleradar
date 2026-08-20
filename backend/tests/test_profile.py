import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.profile import repositories as profile_repo
from app.modules.profile import services as profile_services
from app.modules.profile.schemas import AutoApplySettings, CandidateCategory, OnboardingRequest


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret")


@pytest.mark.asyncio
async def test_onboarding_creates_profile_and_flips_completed_flag(db, settings):
    user, _ = await auth_services.register_user(
        db, settings, "onboard@example.com", "supersecret1", "Ananya", None
    )
    user_id = str(user["_id"])

    body = OnboardingRequest(
        category=CandidateCategory.FRESHER,
        target_roles=["Backend Developer"],
        min_lpa=4,
        preferred_locations=["Bangalore"],
        auto_apply_settings=AutoApplySettings(),
        consent_text="I consent.",
    )

    profile = await profile_services.complete_onboarding(db, user_id, body)
    assert profile["category"] == "FRESHER"
    assert profile["target_roles"] == ["Backend Developer"]

    stored = await profile_repo.get_profile(db, user_id)
    assert stored is not None
    assert stored["min_lpa"] == 4

    updated_user = await db["users"].find_one({"_id": user["_id"]})
    assert updated_user["onboarding_completed"] is True


def test_onboarding_requires_at_least_one_target_role():
    with pytest.raises(Exception):
        OnboardingRequest(
            category=CandidateCategory.FRESHER,
            target_roles=[],
            consent_text="I consent.",
        )
