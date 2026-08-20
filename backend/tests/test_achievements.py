import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.resume import repositories as resume_repo


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret")


@pytest.mark.asyncio
async def test_create_and_list_achievement(db, settings):
    user, _ = await auth_services.register_user(db, settings, "ach@example.com", "supersecret1", "A", None)
    user_id = str(user["_id"])

    await resume_repo.create_achievement(db, user_id, {
        "title": "Won college hackathon", "description": "Built a resume parser in 24 hours",
        "metrics": "1st place out of 40 teams", "skills_tags": ["Python", "Teamwork"],
    })

    achievements = await resume_repo.list_achievements(db, user_id)
    assert len(achievements) == 1
    assert achievements[0]["title"] == "Won college hackathon"


@pytest.mark.asyncio
async def test_achievements_are_scoped_to_owner(db, settings):
    user_a, _ = await auth_services.register_user(db, settings, "a@example.com", "supersecret1", "A", None)
    user_b, _ = await auth_services.register_user(db, settings, "b@example.com", "supersecret1", "B", None)

    await resume_repo.create_achievement(db, str(user_a["_id"]), {
        "title": "A's achievement", "description": "d", "metrics": None, "skills_tags": [],
    })

    b_achievements = await resume_repo.list_achievements(db, str(user_b["_id"]))
    assert b_achievements == []


@pytest.mark.asyncio
async def test_delete_achievement(db, settings):
    user, _ = await auth_services.register_user(db, settings, "del@example.com", "supersecret1", "D", None)
    user_id = str(user["_id"])
    doc = await resume_repo.create_achievement(db, user_id, {
        "title": "T", "description": "D", "metrics": None, "skills_tags": [],
    })

    deleted = await resume_repo.delete_achievement(db, user_id, str(doc["_id"]))
    assert deleted is True
    assert await resume_repo.list_achievements(db, user_id) == []


@pytest.mark.asyncio
async def test_cannot_delete_another_users_achievement(db, settings):
    user_a, _ = await auth_services.register_user(db, settings, "owner@example.com", "supersecret1", "O", None)
    user_b, _ = await auth_services.register_user(db, settings, "intruder@example.com", "supersecret1", "I", None)

    doc = await resume_repo.create_achievement(db, str(user_a["_id"]), {
        "title": "T", "description": "D", "metrics": None, "skills_tags": [],
    })

    deleted = await resume_repo.delete_achievement(db, str(user_b["_id"]), str(doc["_id"]))
    assert deleted is False
