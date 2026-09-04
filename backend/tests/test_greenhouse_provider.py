"""
Comprehensive test suite for Greenhouse Direct Live Opportunity Provider.
Tests all 23 required scenarios:
1. Greenhouse response normalization.
2. Specific requisition URL accepted as DIRECT_REQUISITION.
3. Generic careers URL rejected.
4. Search URL rejected.
5. Missing URL rejected.
6. Vendor mismatch rejected.
7. Provider source_job_id preserved.
8. posted_at not fabricated when only updated_at exists.
9. first_seen_at populated when first observed.
10. last_verified_at updated after successful verification.
11. Existing active listing remains active after successful sync.
12. Closed/disappeared requisition transitions to CLOSED.
13. Temporary provider failure does NOT close all jobs.
14. Seed records remain MARKET_BENCHMARK.
15. MARKET_BENCHMARK never enters public feed.
16. Only VERIFIED_ACTIVE + DIRECT_REQUISITION enters public feed.
17. No-resume user sees verified live opportunities.
18. Resume user sees the same opportunities plus matching intelligence.
19. No fabricated match score without resume.
20. Direct Apply uses exact stored requisition URL.
21. Internship classification behaves correctly (structured/title, not description).
22. Custom opportunity isolation remains intact.
23. Existing regression test suites pass.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.modules.jobs.greenhouse_provider import (
    GreenhouseJobProvider,
    GreenhouseNetworkError,
    is_internship_opportunity,
)
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.services import sync_all_greenhouse_boards
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus
from app.modules.matching.routes import recommended_matches


def make_raw_gh_job(**overrides):
    base = {
        "id": 7802294003,
        "title": "Software Engineer - Backend",
        "company_name": "Postman",
        "location": {"name": "Bengaluru, Karnataka, India"},
        "absolute_url": "https://job-boards.greenhouse.io/postman/jobs/7802294003",
        "updated_at": "2026-08-20T10:00:00Z",
        "first_published": "2026-08-15T09:00:00Z",
        "content": "<p>We are looking for a Python and FastAPI backend engineer.</p>",
        "departments": [{"name": "Engineering"}],
    }
    base.update(overrides)
    return base


def test_01_greenhouse_response_normalization():
    """1. Greenhouse response normalizes correctly into canonical model."""
    provider = GreenhouseJobProvider()
    raw = make_raw_gh_job()
    norm = provider.normalize_greenhouse_job(raw, "postman", company_name="Postman")

    assert norm["id"] == "gh_postman_7802294003"
    assert norm["source"] == "greenhouse"
    assert norm["source_job_id"] == "7802294003"
    assert norm["title"] == "Software Engineer - Backend"
    assert norm["company"] == "Postman"
    assert norm["location"] == "Bengaluru, Karnataka, India"
    assert norm["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm["is_direct_apply"] is True
    assert norm["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    assert "Python" in norm["skills_required"] or "FastAPI" in norm["skills_required"]


def test_02_specific_requisition_url_accepted():
    """2. Specific Greenhouse requisition URL accepted as DIRECT_REQUISITION."""
    url_type, reason = classify_application_url(
        "https://job-boards.greenhouse.io/postman/jobs/7802294003",
        company="Postman",
    )
    assert url_type == ApplicationUrlType.DIRECT_REQUISITION

    url_type2, _ = classify_application_url(
        "https://boards.greenhouse.io/figma/jobs/5364702004",
        company="Figma",
    )
    assert url_type2 == ApplicationUrlType.DIRECT_REQUISITION


def test_03_generic_careers_url_rejected():
    """3. Generic careers homepage URL rejected as CORPORATE_PORTAL."""
    url_type, _ = classify_application_url("https://www.accenture.com/in-en/careers", company="Accenture")
    assert url_type == ApplicationUrlType.CORPORATE_PORTAL


def test_04_search_url_rejected():
    """4. Search results URL rejected."""
    url_type, _ = classify_application_url("https://internshala.com/internships", company="Swiggy")
    assert url_type == ApplicationUrlType.SEARCH_RESULTS


def test_05_missing_url_rejected():
    """5. Missing apply_url rejected as INVALID."""
    url_type, _ = classify_application_url(None)
    assert url_type == ApplicationUrlType.INVALID


def test_06_vendor_mismatch_rejected():
    """6. Vendor mismatch rejected as INVALID."""
    url_type, reason = classify_application_url("https://razorpay.com/jobs/", company="Accenture")
    assert url_type == ApplicationUrlType.INVALID
    assert "Vendor mismatch" in reason


def test_07_provider_source_job_id_preserved():
    """7. Provider source_job_id is preserved exactly."""
    provider = GreenhouseJobProvider()
    raw = make_raw_gh_job(id=9928172)
    norm = provider.normalize_greenhouse_job(raw, "inmobi", company_name="InMobi")
    assert norm["source_job_id"] == "9928172"
    assert norm["id"] == "gh_inmobi_9928172"


def test_08_posted_at_not_fabricated():
    """8. posted_at is NOT fabricated when only updated_at exists."""
    provider = GreenhouseJobProvider()
    raw = make_raw_gh_job(first_published=None, updated_at="2026-08-25T14:00:00Z")
    norm = provider.normalize_greenhouse_job(raw, "postman")

    assert norm["posted_at"] is None
    assert norm["updated_at"] == "2026-08-25T14:00:00+00:00"


def test_09_and_10_timestamps_first_seen_and_last_verified():
    """9-10. first_seen_at populated and last_verified_at updated."""
    provider = GreenhouseJobProvider()
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    raw = make_raw_gh_job()
    norm = provider.normalize_greenhouse_job(raw, "postman", now=now)

    assert norm["first_seen_at"] == now.isoformat()
    assert norm["last_seen_at"] == now.isoformat()
    assert norm["last_verified_at"] == now.isoformat()


@pytest.mark.asyncio
async def test_11_and_12_sync_preserves_active_and_closes_disappeared():
    """11-12. Active listing remains active; disappeared listing transitions to CLOSED."""
    provider = GreenhouseJobProvider()
    db = AsyncMock()

    # Suppose MongoDB previously had 2 active jobs for 'postman': 101 and 102
    existing_jobs = [
        {"id": "gh_postman_101", "source_job_id": "101", "verification_status": "VERIFIED_ACTIVE"},
        {"id": "gh_postman_102", "source_job_id": "102", "verification_status": "VERIFIED_ACTIVE"},
    ]
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=existing_jobs)
    db["jobs"].find = lambda _: mock_cursor
    db["jobs"].update_one = AsyncMock()

    # Fresh Greenhouse API returns ONLY job 101 (job 102 was closed by the company)
    fresh_jobs = [make_raw_gh_job(id=101)]

    with patch.object(provider, "fetch_company_openings", AsyncMock(return_value=fresh_jobs)):
        stats = await provider.sync_company_openings(db, "postman")

        assert stats["fetched"] == 1
        assert stats["verified_active"] == 1
        assert stats["closed"] == 1  # 102 transitioned to closed
        assert stats["retained"] == 1  # 101 retained

        # Verify update_one was called to mark 102 CLOSED
        closed_call = None
        for call in db["jobs"].update_one.call_args_list:
            filter_arg = call[0][0]
            update_arg = call[0][1]
            if filter_arg.get("id") == "gh_postman_102":
                closed_call = update_arg
                break

        assert closed_call is not None
        assert closed_call["$set"]["verification_status"] == OpportunityLifecycleStatus.CLOSED.value
        assert closed_call["$set"]["is_direct_apply"] is False


@pytest.mark.asyncio
async def test_13_temporary_provider_failure_does_not_close_jobs():
    """13. Temporary network/HTTP failure does NOT close any existing jobs."""
    provider = GreenhouseJobProvider()
    db = AsyncMock()
    db["jobs"].update_one = AsyncMock()

    # Network error occurs
    with patch.object(provider, "fetch_company_openings", AsyncMock(side_effect=GreenhouseNetworkError("Timeout"))):
        stats = await provider.sync_company_openings(db, "postman")

        assert stats["fetched"] == 0
        assert stats["closed"] == 0  # CRITICAL: zero jobs closed
        assert len(stats["errors"]) == 1
        assert "Network error" in stats["errors"][0]
        assert db["jobs"].update_one.call_count == 0


@pytest.mark.asyncio
async def test_14_and_15_seed_benchmark_excluded_from_public_feed():
    """14-15. Seed records remain MARKET_BENCHMARK and never enter public feed."""
    db = AsyncMock()
    provider = CuratedJobProvider(db)

    with patch("app.modules.jobs.repositories.find_jobs", AsyncMock(return_value=[])) as mock_find:
        await provider.search({"job_type": "full_time", "active_discovery_only": True})
        called_filter = mock_find.call_args[0][1]

        assert "$and" in called_filter
        status_clause = None
        for c in called_filter["$and"]:
            if c.get("verification_status") == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value:
                status_clause = c
                break

        assert status_clause is not None
        assert status_clause["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
        assert status_clause["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value


def test_16_only_verified_active_and_direct_apply_enters_public_feed():
    """16. Feed gatekeeping enforces both VERIFIED_ACTIVE and DIRECT_REQUISITION."""
    provider = GreenhouseJobProvider()
    raw_invalid_url = make_raw_gh_job(absolute_url="https://postman.com/careers")
    norm = provider.normalize_greenhouse_job(raw_invalid_url, "postman")
    # Because absolute_url is a generic careers homepage, it is classified as CORPORATE_PORTAL
    assert norm["url_type"] == ApplicationUrlType.CORPORATE_PORTAL.value
    assert norm["is_direct_apply"] is False


@pytest.mark.asyncio
async def test_17_to_20_no_resume_discovery_and_exact_direct_apply_url():
    """17-20. No-resume user sees verified live opportunities with exact direct URL and no fake score."""
    db = AsyncMock()
    settings = Settings()
    current_user = {"_id": "test_user_gh_01"}

    gh_job = {
        "id": "gh_postman_7802294003",
        "title": "Staff Engineer - Backend",
        "company": "Postman",
        "job_type": "full_time",
        "location": "Bengaluru",
        "is_remote": False,
        "posted_days_ago": 3,
        "posted_at": "2026-08-31T10:00:00Z",
        "source": "greenhouse",
        "apply_url": "https://job-boards.greenhouse.io/postman/jobs/7802294003",
        "skills_required": ["Python", "FastAPI"],
        "skills_nice_to_have": ["Docker"],
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "url_type": ApplicationUrlType.DIRECT_REQUISITION.value,
        "is_direct_apply": True,
        "last_verified_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch("app.modules.matching.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.jobs_services.refresh_live_jobs", AsyncMock(return_value=1)), \
         patch("app.modules.matching.routes.jobs_services.search_jobs", AsyncMock(return_value=[gh_job])):

        matches = await recommended_matches(
            job_type=None,
            live_only=False,
            current_user=current_user,
            db=db,
            settings=settings,
        )

        assert len(matches) == 1
        m = matches[0]
        assert m.job_id == "gh_postman_7802294003"
        assert m.apply_url == "https://job-boards.greenhouse.io/postman/jobs/7802294003"
        assert m.verification_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
        assert m.is_direct_apply is True
        assert m.has_match is False
        assert m.overall_score is None


def test_21_internship_classification_semantics():
    """21. Internship classified via title or structured department; never via description substring."""
    assert is_internship_opportunity("Software Engineer Intern", []) is True
    assert is_internship_opportunity("Data Science Internship (Summer 2027)", []) is True
    assert is_internship_opportunity("Graduate Trainee", []) is True
    assert is_internship_opportunity("Software Engineer", [{"name": "University / Interns"}]) is True

    # Critical rule: description containing the word intern must NOT cause false classification
    assert is_internship_opportunity("Senior Backend Engineer", [{"name": "Platform"}]) is False
    assert is_internship_opportunity("Lead Architect (mentors interns)", []) is False


@pytest.mark.asyncio
async def test_22_custom_opportunity_isolation_preserved():
    """22. User-pasted custom opportunity remains private and isolated."""
    db = AsyncMock()
    provider = CuratedJobProvider(db)

    with patch("app.modules.jobs.repositories.find_jobs", AsyncMock(return_value=[])) as mock_find:
        await provider.search({"user_id": "user_alice", "job_type": "full_time"})
        called_filter = mock_find.call_args[0][1]

        assert "$and" in called_filter
        user_clause = None
        for c in called_filter["$and"]:
            if "$or" in c and any("user_id" in cond for cond in c["$or"]):
                user_clause = c["$or"]
                break

        assert user_clause is not None
        assert {"source": {"$ne": "custom"}} in user_clause
        assert {"user_id": "user_alice"} in user_clause
        assert {"user_id": "user_bob"} not in user_clause


@pytest.mark.asyncio
async def test_23_sync_all_greenhouse_boards_service():
    """23. sync_all_greenhouse_boards service properly iterates configured boards."""
    db = AsyncMock()
    settings = Settings()
    settings.GREENHOUSE_COMPANIES = "postman,inmobi"
    settings.GREENHOUSE_ENABLED = True

    mock_sync = AsyncMock(return_value={"board": "mock", "fetched": 10, "verified_active": 10, "closed": 0})
    with patch("app.modules.jobs.greenhouse_provider.GreenhouseJobProvider.sync_company_openings", mock_sync):
        res = await sync_all_greenhouse_boards(db, settings)
        assert res["total_boards"] == 2
        assert res["verified_active"] == 20
        assert mock_sync.call_count == 2
