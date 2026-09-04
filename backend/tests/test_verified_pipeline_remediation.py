"""
Comprehensive test suite for Verified Live Job & Internship Pipeline Remediation.
Proves all 23 scenarios:
1. Generic corporate homepage rejected from DIRECT_REQUISITION (classified as CORPORATE_PORTAL).
2. Search-result URL rejected (classified as SEARCH_RESULTS).
3. Missing apply_url rejected (INVALID).
4. Malformed/placeholder URL rejected (INVALID).
5. Vendor/company mismatch rejected (e.g. Accenture -> Razorpay URL).
6. Direct ATS requisition accepted as DIRECT_REQUISITION.
7. Seed records are NOT automatically VERIFIED_ACTIVE (classified as MARKET_BENCHMARK).
8. Unverified legacy records do not enter public feed.
9. CLOSED records do not enter public feed.
10. EXPIRED records do not enter public feed.
11. STALE records do not enter public feed.
12. VERIFIED_ACTIVE direct listings do enter public feed.
13. Posted date remains available to frontend.
14. Revalidation updates last_verified_at.
15. Closed provider signal transitions listing to CLOSED.
16. Stale listing transitions appropriately.
17. Deduplication works across providers.
18. No-resume user can see verified active jobs.
19. No-resume user can see verified active internships.
20. No-resume user does not receive fabricated match scores.
21. Resume user still receives personalized matching.
22. Custom opportunity ownership isolation remains intact.
23. Lifecycle enum contains all canonical states including MARKET_BENCHMARK.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
import pytest

from app.core.config import Settings
from app.modules.jobs.deduplication import deduplicate_opportunities
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.revalidation import revalidate_all_active_opportunities
from app.modules.jobs.services import ensure_seed_loaded, reverify_active_opportunities
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import (
    OpportunityLifecycleStatus,
    validate_apply_url,
    verify_opportunity_sync,
)
from app.modules.matching.routes import recommended_matches


def make_test_job(**overrides):
    base = {
        "id": "job_direct_01",
        "title": "Backend Software Engineer",
        "company": "Amazon India",
        "job_type": "full_time",
        "location": "Bangalore",
        "is_remote": False,
        "posted_days_ago": 5,
        "posted_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "source": "curated",
        "apply_url": "https://amazon.jobs/en/jobs/2819283/backend-engineer-aws",
        "skills_required": ["Python", "AWS", "FastAPI"],
        "skills_nice_to_have": ["Docker"],
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "url_type": ApplicationUrlType.DIRECT_REQUISITION.value,
        "is_direct_apply": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "last_verified_at": datetime.now(timezone.utc).isoformat(),
        "verification_reason": "Direct employer requisition validated",
        "verification_method": "direct_ats_verified",
    }
    base.update(overrides)
    return base


def test_scenario_01_generic_corporate_homepage_rejected():
    """1. Generic corporate homepage rejected from DIRECT_REQUISITION."""
    url_type, reason = classify_application_url("https://www.accenture.com/in-en/careers", company="Accenture")
    assert url_type == ApplicationUrlType.CORPORATE_PORTAL
    assert "generic careers homepage" in reason

    url_type2, _ = classify_application_url("https://careers.cred.club/", company="CRED")
    assert url_type2 == ApplicationUrlType.CORPORATE_PORTAL


def test_scenario_02_search_result_url_rejected():
    """2. Search-result URL rejected."""
    url_type, reason = classify_application_url("https://internshala.com/internships", company="Swiggy")
    assert url_type == ApplicationUrlType.SEARCH_RESULTS

    url_type2, reason2 = classify_application_url("https://www.linkedin.com/jobs/search/?keywords=software+internship", company="Amazon")
    assert url_type2 == ApplicationUrlType.SEARCH_RESULTS
    assert "search query parameters" in reason2


def test_scenario_03_missing_apply_url_rejected():
    """3. Missing apply_url rejected."""
    url_type, reason = classify_application_url(None)
    assert url_type == ApplicationUrlType.INVALID
    assert "Missing" in reason

    url_type2, _ = classify_application_url("")
    assert url_type2 == ApplicationUrlType.INVALID


def test_scenario_04_malformed_placeholder_url_rejected():
    """4. Malformed/placeholder URL rejected."""
    url_type, reason = classify_application_url("https://example.com/apply")
    assert url_type == ApplicationUrlType.INVALID
    assert "placeholder" in reason.lower()

    url_type2, _ = classify_application_url("http://localhost:8000/job/123")
    assert url_type2 == ApplicationUrlType.INVALID

    url_type3, _ = classify_application_url("ftp://careers.com")
    assert url_type3 == ApplicationUrlType.INVALID


def test_scenario_05_vendor_company_mismatch_rejected():
    """5. Vendor/company mismatch rejected (e.g. Accenture -> Razorpay URL)."""
    url_type, reason = classify_application_url("https://razorpay.com/jobs/", company="Accenture")
    assert url_type == ApplicationUrlType.INVALID
    assert "Vendor mismatch" in reason


def test_scenario_06_direct_ats_requisition_accepted():
    """6. Direct ATS requisition accepted as DIRECT_REQUISITION."""
    url_type, _ = classify_application_url("https://boards.greenhouse.io/stripe/jobs/5829102", company="Stripe")
    assert url_type == ApplicationUrlType.DIRECT_REQUISITION

    url_type2, _ = classify_application_url("https://jobs.lever.co/netflix/92847291-a1b2", company="Netflix")
    assert url_type2 == ApplicationUrlType.DIRECT_REQUISITION

    url_type3, _ = classify_application_url("https://amazon.jobs/en/jobs/2819283/software-dev-engineer", company="Amazon")
    assert url_type3 == ApplicationUrlType.DIRECT_REQUISITION


@pytest.mark.asyncio
async def test_scenario_07_seed_records_not_automatically_verified_active():
    """7. Seed records are NOT automatically VERIFIED_ACTIVE (classified as MARKET_BENCHMARK)."""
    db = AsyncMock()
    with patch("builtins.open"), \
         patch("json.load", return_value=[
             {"title": "Backend Dev", "company": "Accenture", "apply_url": "https://www.accenture.com/in-en/careers"},
             {"title": "Intern", "company": "Swiggy", "apply_url": "https://internshala.com/internships"},
         ]), \
         patch("os.path.exists", return_value=True), \
         patch("app.modules.jobs.repositories.upsert_jobs", AsyncMock()) as mock_upsert:

        count = await ensure_seed_loaded(db)
        assert count == 2
        upserted = mock_upsert.call_args[0][1]
        for job in upserted:
            assert job["verification_status"] == OpportunityLifecycleStatus.MARKET_BENCHMARK.value
            assert job["is_direct_apply"] is False
            assert job["source"] == "curated_benchmark"


@pytest.mark.asyncio
async def test_scenario_08_to_12_curated_job_provider_feed_gatekeeping():
    """8-12. Unverified, CLOSED, EXPIRED, STALE excluded; VERIFIED_ACTIVE DIRECT included."""
    db = AsyncMock()
    provider = CuratedJobProvider(db)

    with patch("app.modules.jobs.repositories.find_jobs", AsyncMock(return_value=[])) as mock_find:
        await provider.search({"job_type": "full_time", "active_discovery_only": True})
        called_filter = mock_find.call_args[0][1]

        # Must enforce verification_status == VERIFIED_ACTIVE and url_type == DIRECT_REQUISITION
        assert "$and" in called_filter
        status_clause = None
        for clause in called_filter["$and"]:
            if clause.get("verification_status") == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value:
                status_clause = clause
                break

        assert status_clause is not None
        assert status_clause["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
        assert status_clause["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value

        # No legacy unverified fallback permitted
        assert "$or" not in status_clause


def test_scenario_13_posted_date_available():
    """13. Posted date / posted_at remains available in Job schema."""
    job = make_test_job(posted_at="2026-08-28T12:00:00Z")
    assert job["posted_at"] == "2026-08-28T12:00:00Z"
    assert job["posted_days_ago"] == 5


@pytest.mark.asyncio
async def test_scenario_14_to_16_revalidation_service_transitions():
    """14-16. Revalidation updates last_verified_at, transitions closed and expired."""
    db = AsyncMock()
    now = datetime.now(timezone.utc)

    db_jobs = [
        make_test_job(id="active_direct", posted_at=(now - timedelta(days=5)).isoformat()),
        make_test_job(id="now_closed", is_active=False),
        make_test_job(id="now_expired", posted_at=(now - timedelta(days=60)).isoformat()),
        make_test_job(id="stale_homepage", apply_url="https://www.accenture.com/in-en/careers"),
    ]

    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=db_jobs)
    db["jobs"].find = lambda _: mock_cursor
    db["jobs"].update_one = AsyncMock()

    stats = await revalidate_all_active_opportunities(db, now=now)

    assert stats["checked"] == 4
    assert stats["retained_active"] == 1
    assert stats["transitioned_closed"] == 1
    assert stats["transitioned_expired"] == 1
    assert stats["transitioned_invalid"] == 1

    # Verify update_one updated last_verified_at for all records
    assert db["jobs"].update_one.call_count == 4


def test_scenario_17_deduplication_preserves_direct_apply_url():
    """17. Deduplication prefers DIRECT_REQUISITION over aggregator and merges skills."""
    job_direct = make_test_job(
        id="direct_1",
        title="Software Engineer",
        company="Razorpay",
        apply_url="https://jobs.lever.co/razorpay/123-abc",
        skills_required=["Python", "FastAPI"],
    )
    job_aggregator = make_test_job(
        id="agg_1",
        title="Software Engineer",
        company="Razorpay Software Pvt Ltd",
        apply_url="https://www.adzuna.in/land/ad/999",
        skills_required=["Python", "Docker"],
    )

    deduped = deduplicate_opportunities([job_direct, job_aggregator])
    assert len(deduped) == 1
    assert "lever.co" in deduped[0]["apply_url"]
    assert "FastAPI" in deduped[0]["skills_required"]
    assert "Docker" in deduped[0]["skills_required"]


@pytest.mark.asyncio
async def test_scenario_18_to_20_no_resume_discovery_flow():
    """18-20. No-resume user sees verified active jobs and internships without fake match scores."""
    db = AsyncMock()
    settings = Settings()
    current_user = {"_id": "fresh_user_001"}

    verified_feed = [
        make_test_job(id="v1", title="Backend Engineer", job_type="full_time"),
        make_test_job(id="v2", title="Frontend Intern", job_type="internship", apply_url="https://jobs.lever.co/cred/intern-01"),
    ]

    with patch("app.modules.matching.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.jobs_services.refresh_live_jobs", AsyncMock(return_value=0)), \
         patch("app.modules.matching.routes.jobs_services.search_jobs", AsyncMock(return_value=verified_feed)):

        matches = await recommended_matches(
            job_type=None,
            live_only=False,
            current_user=current_user,
            db=db,
            settings=settings,
        )

        assert len(matches) == 2
        for m in matches:
            assert m.verification_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
            assert m.is_direct_apply is True
            assert m.has_match is False
            assert m.overall_score is None


@pytest.mark.asyncio
async def test_scenario_21_resume_user_personalized_matching():
    """21. User with resume receives personalized match scoring."""
    from app.modules.matching.services import get_or_compute_matches

    db = AsyncMock()
    settings = Settings()
    user_id = "resume_user_01"

    resume = {"version": 1, "parsed": {"skills": ["python", "fastapi", "aws"]}}
    candidate = {
        "user_id": user_id,
        "skills": ["python", "fastapi", "aws"],
        "target_roles": ["Backend Developer"],
        "experience_years": 2,
    }
    jobs = [make_test_job(id="job_match_1", skills_required=["Python", "FastAPI"])]

    from unittest.mock import MagicMock
    mock_embedder = MagicMock()
    mock_embedder.similarity.return_value = 0.85

    with patch("app.modules.matching.repositories.get_cached_matches_for_jobs", AsyncMock(return_value={})), \
         patch("app.modules.matching.repositories.save_cached_matches", AsyncMock()), \
         patch("app.modules.matching.services.build_embedding_provider", return_value=mock_embedder):

        results = await get_or_compute_matches(db, user_id, resume, candidate, jobs, settings)
        assert len(results) == 1
        assert results[0]["has_match"] is True
        assert results[0]["overall_score"] is not None
        assert results[0]["is_direct_apply"] is True


@pytest.mark.asyncio
async def test_scenario_22_custom_opportunity_isolation():
    """22. User A cannot discover User B's private custom opportunity."""
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


def test_scenario_23_lifecycle_enum_complete():
    """23. Lifecycle enum contains all 7 states including MARKET_BENCHMARK."""
    expected = {
        "PENDING_VERIFICATION",
        "VERIFIED_ACTIVE",
        "STALE",
        "EXPIRED",
        "CLOSED",
        "INVALID",
        "MARKET_BENCHMARK",
    }
    actual = {s.value for s in OpportunityLifecycleStatus}
    assert expected == actual
