import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.ai_service.service import AIService
from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.chatbot import repositories as chatbot_repo
from app.modules.chatbot.services import handle_chat_message


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret")


class FakeChatProvider:
    def __init__(self):
        self.last_user_prompt = None

    async def complete(self, system_prompt, user_prompt, json_mode=False, **kwargs):
        self.last_user_prompt = user_prompt
        return "This is a reply."


@pytest.mark.asyncio
async def test_first_message_has_no_history(db, settings):
    user, _ = await auth_services.register_user(db, settings, "hist@example.com", "supersecret1", "H", None)
    user_id = str(user["_id"])

    ai_service = AIService(settings)
    fake_provider = FakeChatProvider()
    ai_service._provider = fake_provider

    await handle_chat_message(ai_service, user_id, "Hello", db)
    assert "CONVERSATION SO FAR" not in fake_provider.last_user_prompt


@pytest.mark.asyncio
async def test_second_message_includes_prior_history(db, settings):
    user, _ = await auth_services.register_user(db, settings, "hist2@example.com", "supersecret1", "H", None)
    user_id = str(user["_id"])

    ai_service = AIService(settings)
    fake_provider = FakeChatProvider()
    ai_service._provider = fake_provider

    await handle_chat_message(ai_service, user_id, "What jobs suit me?", db)
    await handle_chat_message(ai_service, user_id, "What about the second one?", db)

    assert "What jobs suit me?" in fake_provider.last_user_prompt
    assert "This is a reply." in fake_provider.last_user_prompt


@pytest.mark.asyncio
async def test_history_persists_across_separate_calls(db, settings):
    user, _ = await auth_services.register_user(db, settings, "hist3@example.com", "supersecret1", "H", None)
    user_id = str(user["_id"])

    ai_service = AIService(settings)
    ai_service._provider = FakeChatProvider()

    await handle_chat_message(ai_service, user_id, "Message one", db)
    await handle_chat_message(ai_service, user_id, "Message two", db)

    stored = await chatbot_repo.get_conversation(db, user_id)
    assert len(stored) == 4  # 2 user + 2 assistant messages
    assert stored[0]["text"] == "Message one"
    assert stored[2]["text"] == "Message two"


@pytest.mark.asyncio
async def test_history_is_scoped_per_user(db, settings):
    user_a, _ = await auth_services.register_user(db, settings, "a2@example.com", "supersecret1", "A", None)
    user_b, _ = await auth_services.register_user(db, settings, "b2@example.com", "supersecret1", "B", None)

    ai_service = AIService(settings)
    ai_service._provider = FakeChatProvider()

    await handle_chat_message(ai_service, str(user_a["_id"]), "A's private message", db)

    b_history = await chatbot_repo.get_conversation(db, str(user_b["_id"]))
    assert b_history == []


@pytest.mark.asyncio
async def test_clear_conversation_removes_history(db, settings):
    user, _ = await auth_services.register_user(db, settings, "clear@example.com", "supersecret1", "C", None)
    user_id = str(user["_id"])

    ai_service = AIService(settings)
    ai_service._provider = FakeChatProvider()
    await handle_chat_message(ai_service, user_id, "Hi", db)

    assert len(await chatbot_repo.get_conversation(db, user_id)) == 2
    await chatbot_repo.clear_conversation(db, user_id)
    assert await chatbot_repo.get_conversation(db, user_id) == []
