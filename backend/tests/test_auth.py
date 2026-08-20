"""
Auth flow tests against an in-memory Mongo (mongomock-motor), so they
run anywhere without a live database — but exercise the real
repository/service code, not mocks of it.
"""
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.auth import services


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret")


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_token(db, settings):
    user, token = await services.register_user(
        db, settings, "ananya@example.com", "supersecret1", "Ananya Rao", None
    )
    assert user["email"] == "ananya@example.com"
    assert user["password_hash"] != "supersecret1"  # never store plaintext
    assert isinstance(token, str) and len(token) > 10


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(db, settings):
    await services.register_user(db, settings, "dup@example.com", "supersecret1", "A", None)
    with pytest.raises(services.EmailAlreadyRegisteredError):
        await services.register_user(db, settings, "dup@example.com", "anotherpass1", "B", None)


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_password(db, settings):
    await services.register_user(db, settings, "login@example.com", "correctpass1", "C", None)
    user, token = await services.authenticate_user(db, settings, "login@example.com", "correctpass1")
    assert user["email"] == "login@example.com"
    assert token


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(db, settings):
    await services.register_user(db, settings, "wrong@example.com", "correctpass1", "D", None)
    with pytest.raises(services.InvalidCredentialsError):
        await services.authenticate_user(db, settings, "wrong@example.com", "wrongpass1")


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(db, settings):
    with pytest.raises(services.InvalidCredentialsError):
        await services.authenticate_user(db, settings, "nobody@example.com", "whatever1")
