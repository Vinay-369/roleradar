import json
import pytest
import httpx
from app.core.config import Settings
from app.core.ai_service.factory import build_provider
from app.core.ai_service.providers.cloud_fallback_provider import CloudFallbackProvider
from app.core.ai_service.service import AIService
from app.core.ai_service.schemas import TailoringResult


def test_cloud_fallback_requires_api_key():
    settings = Settings(CLOUD_FALLBACK_API_KEY="")
    with pytest.raises(RuntimeError, match="CLOUD_FALLBACK_API_KEY is not set"):
        CloudFallbackProvider(settings)


@pytest.mark.asyncio
async def test_gemini_fallback_call_structure(monkeypatch):
    captured_request = {}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None):
            captured_request["url"] = url
            captured_request["json"] = json

            class MockResponse:
                status_code = 200

                def json(self):
                    return {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {"text": '{"response": "Gemini response text"}'}
                                    ]
                                }
                            }
                        ]
                    }

            return MockResponse()

    monkeypatch.setattr("app.core.ai_service.providers.cloud_fallback_provider.httpx.AsyncClient", MockAsyncClient)

    settings = Settings(
        AI_PROVIDER="cloud_fallback",
        CLOUD_FALLBACK_PROVIDER="gemini",
        CLOUD_FALLBACK_API_KEY="test_gemini_key",
        CLOUD_FALLBACK_MODEL="gemini-2.0-flash",
    )
    provider = CloudFallbackProvider(settings)
    result = await provider.complete("System prompt", "User prompt", json_mode=True)

    assert "key=test_gemini_key" in captured_request["url"]
    assert captured_request["json"]["generationConfig"]["response_mime_type"] == "application/json"
    assert "Gemini response text" in result


@pytest.mark.asyncio
async def test_openai_compatible_fallback_call_structure(monkeypatch):
    captured_request = {}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None):
            captured_request["url"] = url
            captured_request["json"] = json
            captured_request["headers"] = headers

            class MockResponse:
                status_code = 200

                def json(self):
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"response": "Groq response text"}'
                                }
                            }
                        ]
                    }

            return MockResponse()

    monkeypatch.setattr("app.core.ai_service.providers.cloud_fallback_provider.httpx.AsyncClient", MockAsyncClient)

    settings = Settings(
        AI_PROVIDER="cloud_fallback",
        CLOUD_FALLBACK_PROVIDER="groq",
        CLOUD_FALLBACK_API_KEY="test_groq_key",
        CLOUD_FALLBACK_MODEL="llama-3.3-70b-versatile",
    )
    provider = CloudFallbackProvider(settings)
    result = await provider.complete("System prompt", "User prompt", json_mode=True)

    assert captured_request["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured_request["headers"]["Authorization"] == "Bearer test_groq_key"
    assert captured_request["json"]["response_format"] == {"type": "json_object"}
    assert "Groq response text" in result


@pytest.mark.asyncio
async def test_ai_service_integration_with_cloud_fallback(monkeypatch):
    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None):
            class MockResponse:
                status_code = 200

                def json(self):
                    return {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "text": (
                                                '{"changes": [{'
                                                '"change_id": "chg_1", '
                                                '"original": "Worked on backend.", '
                                                '"proposed": "Architected FastAPI backend services.", '
                                                '"reason": "Aligns with FastAPI requirement in JD.", '
                                                '"source_evidence": "Master resume mentions FastAPI projects.", '
                                                '"confidence": 0.95, '
                                                '"status": "PENDING"'
                                                '}]}'
                                            )
                                        }
                                    ]
                                }
                            }
                        ]
                    }

            return MockResponse()

    monkeypatch.setattr("app.core.ai_service.providers.cloud_fallback_provider.httpx.AsyncClient", MockAsyncClient)

    settings = Settings(
        AI_PROVIDER="cloud_fallback",
        CLOUD_FALLBACK_PROVIDER="gemini",
        CLOUD_FALLBACK_API_KEY="test_key",
    )
    ai_service = AIService(settings)

    from app.core.ai_service.schemas import StructuredTailoringResult

    tailoring_res = await ai_service.generate_resume_rewrite(
        master_resume_json='{"skills": ["Python", "FastAPI"]}',
        jd_text="Looking for FastAPI developer.",
        user_id="test_user"
    )

    assert isinstance(tailoring_res, StructuredTailoringResult)
    assert len(tailoring_res.changes) == 1
    assert tailoring_res.changes[0].proposed == "Architected FastAPI backend services."
