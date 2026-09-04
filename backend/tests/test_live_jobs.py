"""
Tests for the Adzuna live job integration.

IMPORTANT: these tests do NOT hit the real Adzuna API (this sandbox
has no general internet access -- confirmed directly, non-allowlisted
domains return 403 from the egress proxy). They verify two things
that don't require network access:
  1. The response-transform logic is correct against a fixture shaped
     exactly like Adzuna's documented API response.
  2. The whole feature fails safely (never crashes, never blocks
     curated jobs) when unconfigured or when the HTTP call fails.

You must verify the actual live HTTP call works once you have real
Adzuna credentials -- see the README.
"""
import httpx
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.jobs.live_provider import AdzunaConfigError, AdzunaJobProvider
from app.modules.jobs import services as jobs_services

# A fixture shaped like Adzuna's documented /jobs/{country}/search response.
ADZUNA_FIXTURE_RESPONSE = {
    "results": [
        {
            "id": "4567890123",
            "title": "Python Backend Developer",
            "company": {"display_name": "Real Company Pvt Ltd"},
            "location": {"display_name": "Bangalore, Karnataka"},
            "description": "We need a Python developer with FastAPI and Docker experience. Entry level role, freshers welcome.",
            "redirect_url": "https://www.adzuna.in/land/ad/4567890123?se=abc123",
            "salary_min": 500000,
            "salary_max": 800000,
            "created": "2026-08-10T09:00:00Z",
            "category": {"label": "IT Jobs"},
        },
        {
            "id": "9998887776",
            "title": "Data Science Intern",
            "company": {"display_name": "AnotherCo"},
            "location": {"display_name": "Remote"},
            "description": "Remote internship working with Pandas and Machine Learning models.",
            "redirect_url": "https://www.adzuna.in/land/ad/9998887776?se=xyz789",
            "salary_min": None,
            "salary_max": None,
            "created": "2026-08-15T09:00:00Z",
            "category": {"label": "IT Jobs"},
        },
    ],
    "count": 2,
}


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def configured_settings():
    return Settings(JWT_SECRET="test", ADZUNA_APP_ID="fake-id", ADZUNA_APP_KEY="fake-key", JOB_SOURCE_MODE="hybrid")


def test_provider_refuses_to_init_without_credentials():
    settings = Settings(JWT_SECRET="test", ADZUNA_APP_ID="", ADZUNA_APP_KEY="")  # no Adzuna keys
    with pytest.raises(AdzunaConfigError):
        AdzunaJobProvider(settings)


def test_transform_maps_real_job_correctly(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform(ADZUNA_FIXTURE_RESPONSE["results"][0])

    assert job["id"] == "adzuna_4567890123"
    assert job["source"] == "adzuna"
    assert job["title"] == "Python Backend Developer"
    assert job["company"] == "Real Company Pvt Ltd"
    assert job["apply_url"] == "https://www.adzuna.in/land/ad/4567890123?se=abc123"
    assert "Python" in job["skills_required"]
    assert "FastAPI" in job["skills_required"] or "FastAPI" in job["skills_nice_to_have"]
    assert job["fresher_friendly"] is True
    assert job["job_type"] == "full_time"
    # Salary converted from raw INR to LPA.
    assert job["salary_min"] == 5.0
    assert job["salary_max"] == 8.0
    assert job["salary_disclosed"] is True


def test_transform_detects_internship_from_title(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform(ADZUNA_FIXTURE_RESPONSE["results"][1])

    assert job["job_type"] == "internship"
    assert job["is_remote"] is True
    assert job["salary_disclosed"] is False
    assert job["salary_min"] is None


def test_transform_never_fabricates_apply_url_if_adzuna_omits_it(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    result_without_url = {**ADZUNA_FIXTURE_RESPONSE["results"][0]}
    del result_without_url["redirect_url"]
    job = provider._transform(result_without_url)
    assert job["apply_url"] == ""  # honest empty, never a fabricated link


@pytest.mark.asyncio
async def test_search_returns_empty_list_on_http_failure(configured_settings, monkeypatch):
    """A network error or Adzuna outage must never crash the jobs page —
    it should just mean zero live results, curated jobs still work."""

    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr("app.modules.jobs.live_provider.httpx.AsyncClient", lambda **kw: FailingAsyncClient())

    provider = AdzunaJobProvider(configured_settings)
    results = await provider.search({"skill": "python"})
    assert results == []


@pytest.mark.asyncio
async def test_refresh_live_jobs_is_a_safe_noop_in_curated_only_mode(db):
    """Default mode (JOB_SOURCE_MODE="curated") must never attempt an
    external call at all -- zero-config-required demo path."""
    settings = Settings(JWT_SECRET="test", GREENHOUSE_ENABLED=False)  # JOB_SOURCE_MODE defaults to "curated"
    count = await jobs_services.refresh_live_jobs(db, settings, {})
    assert count == 0


@pytest.mark.asyncio
async def test_refresh_live_jobs_is_a_safe_noop_when_hybrid_but_unconfigured(db):
    """hybrid mode without real credentials must degrade gracefully,
    not throw and break the jobs page."""
    settings = Settings(JWT_SECRET="test", JOB_SOURCE_MODE="hybrid", GREENHOUSE_ENABLED=False)  # no keys set
    count = await jobs_services.refresh_live_jobs(db, settings, {})
    assert count == 0


@pytest.mark.asyncio
async def test_upserted_live_jobs_appear_in_normal_curated_search(db):
    """Once upserted, a live job must be discoverable through the exact
    same search path as curated jobs -- proving downstream consumers
    (matching, ATS, dashboard) need no special-case code for it."""
    from app.modules.jobs import repositories as jobs_repo
    from app.modules.jobs.providers import CuratedJobProvider

    live_job = AdzunaJobProvider.__new__(AdzunaJobProvider)  # bypass __init__ credential check for this unit test
    fake_settings = Settings(JWT_SECRET="test", ADZUNA_APP_ID="x", ADZUNA_APP_KEY="y")
    live_job._settings = fake_settings
    transformed = live_job._transform(ADZUNA_FIXTURE_RESPONSE["results"][0])

    await jobs_repo.upsert_jobs(db, [transformed])

    provider = CuratedJobProvider(db)
    results = await provider.search({})
    assert any(j["id"] == "adzuna_4567890123" for j in results)


@pytest.mark.asyncio
async def test_search_builds_what_or_from_multiple_skills(configured_settings, monkeypatch):
    """Proves the live query is genuinely personalized -- driven by the
    candidate's real skills via OR-matching, not a single fixed term or
    an empty/generic search."""
    captured_params = {}

    class CapturingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            captured_params.update(params or {})

            class FakeResponse:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"results": []}

            return FakeResponse()

    monkeypatch.setattr("app.modules.jobs.live_provider.httpx.AsyncClient", lambda **kw: CapturingAsyncClient())

    provider = AdzunaJobProvider(configured_settings)
    await provider.search({"skills": ["Python", "FastAPI", "Docker"], "location": "Bangalore"})

    assert captured_params["what_or"] == "Python FastAPI Docker"
    assert captured_params["where"] == "Bangalore"


@pytest.mark.asyncio
async def test_internship_filter_biases_query_toward_internships(configured_settings, monkeypatch):
    captured_params = {}

    class CapturingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            captured_params.update(params or {})

            class FakeResponse:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"results": []}

            return FakeResponse()

    monkeypatch.setattr("app.modules.jobs.live_provider.httpx.AsyncClient", lambda **kw: CapturingAsyncClient())

    provider = AdzunaJobProvider(configured_settings)
    await provider.search({"skills": ["Python"], "job_type": "internship"})

    assert "intern" in captured_params["what_or"]
