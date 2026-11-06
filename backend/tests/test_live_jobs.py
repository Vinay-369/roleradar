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
import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.modules.jobs.live_provider import AdzunaConfigError, AdzunaJobProvider
from app.modules.jobs import services as jobs_services
from app.modules.jobs.providers import CuratedJobProvider

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
    assert job["skills_required"] == []
    assert "Python" in job["inferred_skills"]
    assert "FastAPI" in job["inferred_skills"]
    assert job["fresher_friendly"] is True
    assert job["job_type"] == "full_time"
    # Salary converted from raw INR to LPA.
    assert job["salary_min"] == 5.0
    assert job["salary_max"] == 8.0
    assert job["salary_disclosed"] is True
    assert job["salary_currency"] == "INR"
    assert job["salary_period"] == "YEAR"
    assert job["salary_unit"] == "LPA"


def test_attach_compensation_meta_repairs_legacy_adzuna_salary_metadata():
    from app.modules.jobs.routes import _attach_compensation_meta

    job = {
        "source": "adzuna",
        "salary_min": 5.0,
        "salary_max": 8.0,
        "salary_currency": "INR",
        "compensation_type": "NUMERIC",
        "compensation_text": "₹5–8 LPA",
    }

    _attach_compensation_meta(job)

    assert job["salary_period"] == "YEAR"
    assert job["salary_unit"] == "LPA"


def test_transform_detects_internship_from_title(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform(ADZUNA_FIXTURE_RESPONSE["results"][1])

    assert job["job_type"] == "internship"
    assert job["is_remote"] is True
    assert job["salary_disclosed"] is False
    assert job["salary_min"] is None


def test_transform_extracts_salary_from_description_when_adzuna_has_no_salary(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform({
        **ADZUNA_FIXTURE_RESPONSE["results"][0],
        "salary_min": None,
        "salary_max": None,
        "description": "Backend Developer. Compensation: ₹8–12 LPA based on experience.",
    })
    assert job["salary_min"] == 8
    assert job["salary_max"] == 12
    assert job["salary_disclosed"] is True
    assert job["compensation_text"] == "₹8–12 LPA"


def test_transform_extracts_monthly_internship_stipend(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform({
        **ADZUNA_FIXTURE_RESPONSE["results"][1],
        "description": "Remote internship. Stipend: ₹25,000/month.",
    })
    assert job["stipend_min"] == 25000
    assert job["stipend"] == 25000
    assert job["stipend_period"] == "MONTH"
    assert job["salary_disclosed"] is True


def test_transform_keeps_missing_compensation_undisclosed(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform({
        **ADZUNA_FIXTURE_RESPONSE["results"][0],
        "salary_min": None,
        "salary_max": None,
        "description": "Backend Developer. Work with a growing engineering team.",
    })
    assert job["salary_min"] is None
    assert job["stipend_min"] is None
    assert job["salary_disclosed"] is False
    assert job["compensation_text"] is None


def test_transform_extracts_experience_from_description_and_does_not_use_99(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform({
        **ADZUNA_FIXTURE_RESPONSE["results"][0],
        "description": "Requirements: 5+ years of experience with Python.",
    })
    assert job["experience_min"] == 5
    assert job["experience_max"] is None


def test_transform_leaves_experience_unspecified_when_description_has_no_requirement(configured_settings):
    provider = AdzunaJobProvider(configured_settings)
    job = provider._transform({
        **ADZUNA_FIXTURE_RESPONSE["results"][0],
        "description": "Build backend services with Python.",
    })
    assert job["experience_min"] is None
    assert job["experience_max"] is None


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
    settings = Settings(JWT_SECRET="test", JOB_SOURCE_MODE="curated", GREENHOUSE_ENABLED=False)
    count = await jobs_services.refresh_live_jobs(db, settings, {})
    assert count == 0


@pytest.mark.asyncio
async def test_refresh_live_jobs_report_preserves_provider_and_detail_errors(db, monkeypatch):
    settings = Settings(JOB_SOURCE_MODE="direct_ats")

    async def board_result(*args, **kwargs):
        return {
            "total_boards": 1,
            "verified_active": 2,
            "errors": ["Provider request failed."],
            "detail_enriched": 1,
            "detail_enrichment_failed": 3,
            "detail_enrichment_skipped": 4,
            "results": [{"board": "sample", "status": "partial", "verified_active": 2, "errors": ["Provider request failed."]}],
        }

    for provider in ("ashby", "greenhouse", "lever", "smartrecruiters"):
        monkeypatch.setattr(f"app.modules.jobs.services.sync_all_{provider}_boards", board_result)

    report = await jobs_services.refresh_live_jobs(db, settings, {}, include_report=True)
    assert report["added_count"] == 8
    assert report["status"] == "partial"
    assert len(report["providers"]) == 4
    assert all(result["status"] == "partial" for result in report["providers"])
    assert all("Provider" in error for error in report["errors"])
    assert report["detail_enriched"] == 4
    assert report["detail_enrichment_failed"] == 12
    assert report["detail_enrichment_skipped"] == 16


@pytest.mark.asyncio
async def test_sync_configured_board_timeout_is_bounded_and_cancels_provider(db):
    settings = Settings(
        GREENHOUSE_COMPANIES="slow-board",
        GREENHOUSE_ENABLED=True,
        JOB_PROVIDER_SYNC_TIMEOUT_SECONDS=0.01,
    )
    started = asyncio.Event()
    cancelled = asyncio.Event()

    class SlowProvider:
        def __init__(self, settings):
            pass

        async def sync_company_openings(self, db, board, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

    result = await jobs_services._sync_configured_boards(
        db, settings, SlowProvider, "GREENHOUSE_COMPANIES", "GREENHOUSE_ENABLED"
    )

    assert started.is_set()
    assert cancelled.is_set()
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["errors"] == ["Board synchronization exceeded its time limit."]


@pytest.mark.asyncio
async def test_refresh_retains_successful_provider_results_when_another_provider_fails(db, monkeypatch):
    settings = Settings(JOB_SOURCE_MODE="direct_ats", JOB_REFRESH_TIMEOUT_SECONDS=1)

    async def successful(*args, **kwargs):
        return {
            "total_boards": 1,
            "fetched": 3,
            "verified_active": 2,
            "unique_requisitions": 2,
            "errors": [],
            "results": [{"board": "ok-board", "status": "success", "verified_active": 2}],
        }

    async def failed(*args, **kwargs):
        raise RuntimeError("provider secret details must not escape")

    monkeypatch.setattr(jobs_services, "sync_all_ashby_boards", successful)
    monkeypatch.setattr(jobs_services, "sync_all_greenhouse_boards", failed)
    monkeypatch.setattr(jobs_services, "sync_all_lever_boards", successful)
    monkeypatch.setattr(jobs_services, "sync_all_smartrecruiters_boards", successful)

    report = await jobs_services.refresh_live_jobs(db, settings, {}, include_report=True)

    assert report["status"] == "partial"
    assert report["added_count"] == 6
    assert next(p for p in report["providers"] if p["provider"] == "Greenhouse")["status"] == "failed"
    assert any("Greenhouse" in error for error in report["errors"])
    assert all("secret details" not in error for error in report["errors"])


@pytest.mark.asyncio
async def test_refresh_global_deadline_cancels_slow_provider_without_losing_completed_provider(db, monkeypatch):
    settings = Settings(JOB_SOURCE_MODE="direct_ats", JOB_REFRESH_TIMEOUT_SECONDS=0.02)
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow(*args, **kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    async def successful(*args, **kwargs):
        return {
            "total_boards": 1,
            "fetched": 1,
            "verified_active": 1,
            "unique_requisitions": 1,
            "errors": [],
            "results": [{"board": "ok-board", "status": "success", "verified_active": 1}],
        }

    monkeypatch.setattr(jobs_services, "sync_all_ashby_boards", slow)
    monkeypatch.setattr(jobs_services, "sync_all_greenhouse_boards", successful)
    monkeypatch.setattr(jobs_services, "sync_all_lever_boards", successful)
    monkeypatch.setattr(jobs_services, "sync_all_smartrecruiters_boards", successful)

    report = await jobs_services.refresh_live_jobs(db, settings, {}, include_report=True)

    assert started.is_set() and cancelled.is_set()
    assert report["added_count"] == 3
    assert report["status"] == "partial"
    assert next(p for p in report["providers"] if p["provider"] == "Ashby")["status"] == "timed_out"


@pytest.mark.asyncio
async def test_concurrent_refresh_requests_share_one_provider_run(db, monkeypatch):
    settings = Settings(JOB_SOURCE_MODE="direct_ats", JOB_REFRESH_TIMEOUT_SECONDS=1)
    release = asyncio.Event()
    started = asyncio.Event()
    calls = {"count": 0}

    async def shared(*args, **kwargs):
        calls["count"] += 1
        started.set()
        await release.wait()
        return {
            "total_boards": 1,
            "fetched": 1,
            "verified_active": 0,
            "unique_requisitions": 0,
            "errors": [],
            "results": [{"board": "empty-board", "status": "success", "verified_active": 0}],
        }

    for provider in ("ashby", "greenhouse", "lever", "smartrecruiters"):
        monkeypatch.setattr(jobs_services, f"sync_all_{provider}_boards", shared)

    first = asyncio.create_task(jobs_services.refresh_live_jobs(db, settings, {}, include_report=True))
    await started.wait()
    second = asyncio.create_task(jobs_services.refresh_live_jobs(db, settings, {}, include_report=True))
    await asyncio.sleep(0)
    release.set()
    first_report, second_report = await asyncio.gather(first, second)

    assert calls["count"] == 4
    assert first_report == second_report


@pytest.mark.asyncio
async def test_refresh_live_jobs_is_a_safe_noop_when_hybrid_but_unconfigured(db):
    """hybrid mode without real credentials must degrade gracefully,
    not throw and break the jobs page."""
    settings = Settings(
        JWT_SECRET="test",
        JOB_SOURCE_MODE="hybrid",
        ADZUNA_APP_ID="",
        ADZUNA_APP_KEY="",
        JSEARCH_RAPIDAPI_KEY="",
        JOOBLE_API_KEY="",
        GREENHOUSE_ENABLED=False,
    )
    count = await jobs_services.refresh_live_jobs(db, settings, {})
    assert count == 0


def test_scheduled_refresh_requires_an_enabled_configured_official_board():
    assert not jobs_services.has_configured_direct_ats_boards(Settings(
        _env_file=None,
        ASHBY_COMPANIES="",
        GREENHOUSE_COMPANIES="",
        LEVER_COMPANIES="",
        SMARTRECRUITERS_COMPANIES="",
    ))
    assert jobs_services.has_configured_direct_ats_boards(
        Settings(ASHBY_ENABLED=True, ASHBY_COMPANIES="company-board")
    )
    assert not jobs_services.has_configured_direct_ats_boards(
        Settings(
            _env_file=None,
            ASHBY_ENABLED=False,
            ASHBY_COMPANIES="company-board",
            GREENHOUSE_COMPANIES="",
            LEVER_COMPANIES="",
            SMARTRECRUITERS_COMPANIES="",
        )
    )


@pytest.mark.asyncio
async def test_scheduled_refresh_runs_immediately_then_repeats_until_cancelled(db, monkeypatch):
    settings = Settings(
        JOB_SOURCE_MODE="direct_ats",
        JOB_REFRESH_INTERVAL_MINUTES=10,
        ASHBY_ENABLED=True,
        ASHBY_COMPANIES="company-board",
    )
    refresh_count = 0
    sleep_intervals = []

    async def refresh(*args, **kwargs):
        nonlocal refresh_count
        refresh_count += 1
        return {"status": "success", "added_count": 2}

    async def stop_after_one_interval(seconds):
        sleep_intervals.append(seconds)
        raise asyncio.CancelledError

    monkeypatch.setattr(jobs_services, "refresh_live_jobs", refresh)
    monkeypatch.setattr(jobs_services.asyncio, "sleep", stop_after_one_interval)

    with pytest.raises(asyncio.CancelledError):
        await jobs_services.scheduled_job_refresh_loop(db, settings)

    assert refresh_count == 1
    assert sleep_intervals == [600]


def test_fresher_filter_includes_unknown_experience_without_marking_it_eligible():
    query = CuratedJobProvider(object())._build_mongo_query({"stage": "FRESHER"})
    stage_clause = next(
        clause for clause in query["$and"]
        if "$or" in clause and any(
            isinstance(option, dict) and (
                "experience_min" in option
                or any(
                    isinstance(sub_option, dict) and "experience_min" in sub_option
                    for sub_option in option.get("$and", [])
                )
            )
            for option in clause["$or"]
        )
    )

    unknown_experience_clause = next(
        option for option in stage_clause["$or"]
        if isinstance(option, dict)
        and "$and" in option
        and any(
            isinstance(sub_option, dict)
            and "experience_min" in sub_option
            and sub_option["experience_min"] is None
            for sub_option in option["$and"]
        )
    )
    assert {"experience_min": None} in unknown_experience_clause["$and"]
    assert {"experience_max": None} in unknown_experience_clause["$and"]
    assert {"fresher_eligible": {"$ne": False}} in unknown_experience_clause["$and"]


@pytest.mark.asyncio
async def test_fresher_stage_includes_undisclosed_experience_but_excludes_senior_jobs(db):
    from app.modules.jobs import repositories as jobs_repo

    base = {
        "company": "Official Employer",
        "source": "greenhouse",
        "url_type": "DIRECT_REQUISITION",
        "verification_status": "VERIFIED_ACTIVE",
        "location": "Bengaluru, India",
        "apply_url": "https://boards.greenhouse.io/company/jobs/123",
    }
    await jobs_repo.upsert_jobs(db, [
        {
            **base,
            "id": "entry_unknown_experience",
            "title": "Backend Engineer",
            "description": "Build and maintain backend services with the engineering team.",
            "experience_min": None,
            "experience_max": None,
        },
        {
            **base,
            "id": "senior_unknown_experience",
            "title": "Senior Backend Engineer",
            "description": "Build and maintain backend services with the engineering team.",
            "experience_min": None,
            "experience_max": None,
        },
        {
            **base,
            "id": "explicit_experience_required",
            "title": "Backend Engineer",
            "description": "Applicants must have 5+ years of professional experience.",
            "experience_min": None,
            "experience_max": None,
        },
    ])

    results = await CuratedJobProvider(db).search({"stage": "FRESHER"})
    result_ids = {job["id"] for job in results}

    assert "entry_unknown_experience" in result_ids
    assert "senior_unknown_experience" not in result_ids
    assert "explicit_experience_required" not in result_ids


@pytest.mark.asyncio
async def test_fresher_stage_rejects_explicit_experience_even_when_provider_flag_is_fresher(db):
    from app.modules.jobs import repositories as jobs_repo

    base = {
        "company": "Official Employer",
        "source": "greenhouse",
        "url_type": "DIRECT_REQUISITION",
        "verification_status": "VERIFIED_ACTIVE",
        "location": "Bengaluru, India",
        "apply_url": "https://boards.greenhouse.io/company/jobs/456",
    }
    await jobs_repo.upsert_jobs(db, [
        {
            **base,
            "id": "flagged_but_requires_experience",
            "title": "Software Engineer",
            "description": "Freshers may apply, but applicants must have 2+ years of experience.",
            "experience_min": 0,
            "experience_max": 2,
            "fresher_friendly": True,
            "fresher_eligible": True,
        },
        {
            **base,
            "id": "genuine_entry_level",
            "title": "Software Engineer",
            "description": "Entry-level role. Fresh graduates welcome.",
            "experience_min": 0,
            "experience_max": 1,
            "fresher_friendly": True,
            "fresher_eligible": True,
        },
    ])

    result_ids = {job["id"] for job in await CuratedJobProvider(db).search({"stage": "FRESHER"})}
    assert "flagged_but_requires_experience" not in result_ids
    assert "genuine_entry_level" in result_ids


@pytest.mark.asyncio
async def test_aggregator_jobs_remain_outside_direct_ats_curated_search(db):
    """Aggregator listings do not enter the strict direct-ATS discovery feed."""
    from app.modules.jobs import repositories as jobs_repo
    from app.modules.jobs.providers import CuratedJobProvider

    live_job = AdzunaJobProvider.__new__(AdzunaJobProvider)  # bypass __init__ credential check for this unit test
    fake_settings = Settings(JWT_SECRET="test", ADZUNA_APP_ID="x", ADZUNA_APP_KEY="y")
    live_job._settings = fake_settings
    transformed = live_job._transform(ADZUNA_FIXTURE_RESPONSE["results"][0])

    await jobs_repo.upsert_jobs(db, [transformed])

    provider = CuratedJobProvider(db)
    results = await provider.search({})
    assert not any(j["id"] == "adzuna_4567890123" for j in results)


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
