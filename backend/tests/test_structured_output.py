"""
Phase 0 foundation test: proves the AI structured-output validation +
repair-retry mechanism works, using a fake provider so it never depends
on a live model being available (CI-safe, demo-safe).
"""
import pytest
from pydantic import BaseModel

from app.core.ai_service.structured_output import generate_structured, AIOutputError


class DummySchema(BaseModel):
    name: str
    score: int


class AlwaysValidProvider:
    async def complete(self, system_prompt, user_prompt, json_mode=False):
        return '{"name": "Docker", "score": 80}'


class FailsOnceThenValidProvider:
    def __init__(self):
        self.calls = 0

    async def complete(self, system_prompt, user_prompt, json_mode=False):
        self.calls += 1
        if self.calls == 1:
            return "not json at all"
        return '{"name": "Kubernetes", "score": 60}'


class AlwaysInvalidProvider:
    async def complete(self, system_prompt, user_prompt, json_mode=False):
        return "still not json"


@pytest.mark.asyncio
async def test_valid_output_parses_on_first_try():
    result = await generate_structured(
        AlwaysValidProvider(), "sys", "user", DummySchema, max_retries=2
    )
    assert result.name == "Docker"
    assert result.score == 80


@pytest.mark.asyncio
async def test_repair_retry_recovers_from_bad_json():
    provider = FailsOnceThenValidProvider()
    result = await generate_structured(provider, "sys", "user", DummySchema, max_retries=2)
    assert result.name == "Kubernetes"
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_fails_safely_after_exhausting_retries():
    with pytest.raises(AIOutputError):
        await generate_structured(
            AlwaysInvalidProvider(), "sys", "user", DummySchema, max_retries=1
        )
