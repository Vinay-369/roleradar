"""
Comprehensive test suite for Lever Direct Live Opportunity Provider (Phase 13C).
Covers:
1. Valid Lever response normalization
2. Specific requisition URLs accepted as DIRECT_REQUISITION (hostedUrl and applyUrl)
3. Generic / search / invalid URLs rejected
4. Provider source_job_id and company board preserved
5. Zero Date Fabrication: posted_at from createdAt ms epoch, updated_at is None
6. Country integrity (India, United States, United Arab Emirates, None for Remote)
7. India relevance based on location geography (never description boilerplate)
8. Seniority & Fresher classification: SDE II/III/IV/Senior/Lead/Manager remain non-fresher
9. Fresher / Graduate Trainee classification (GET, Associate Engineer 0-1 yr)
10. Genuine Internship classification (structured commitment, department, title)
11. Full-time experience integrity: no fabricated experience_min=0
12. Empty response / 404 handling
13. Malformed item handling (missing id, missing location, missing applyUrl)
14. Network failure / timeout raises LeverNetworkError
15. Authoritative inventory reconciliation: disappeared listing transitions to CLOSED
16. Non-destructive sync failure: network error retains previous jobs without closing them
17. Deduplication: repeated sync results in a single canonical record
18. Multi-provider coexistence: Greenhouse + Lever in same collection
19. User isolation: custom job ownership unaffected
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.jobs.lever_provider import (
    LeverJobProvider,
    LeverNetworkError,
    LeverProviderError,
    is_internship_opportunity,
)
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.services import sync_all_lever_boards
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus


def make_raw_lever_job(**overrides):
    base = {
        "id": "c6085ba8-0df2-42fe-b586-773dfabfbba9",
        "text": "Software Engineer - Backend",
        "createdAt": 1783043640931,  # July 2026 epoch ms
        "workplaceType": "onsite",
        "hostedUrl": "https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9",
        "applyUrl": "https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9/apply",
        "categories": {
            "commitment": "Full-time Employment",
            "department": "Engineering",
            "team": "Core Platform",
            "location": "Bengaluru, Karnataka",
            "allLocations": ["Bengaluru, Karnataka"],
        },
        "descriptionPlain": "We are looking for a Python and FastAPI backend engineer.",
        "description": "<p>We are looking for a Python and FastAPI backend engineer.</p>",
        "lists": [
            {
                "text": "What you will do",
                "content": "<li>Build high scale microservices</li><li>Deploy on Kubernetes</li>",
            }
        ],
        "additionalPlain": "Paytm is India's leading fintech platform.",
    }
    base.update(overrides)
    return base


# --- 1. NORMALIZATION ---

def test_01_lever_response_normalization():
    """1. Lever response normalizes correctly into canonical model."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job()
    norm = provider.normalize_lever_job(raw, "paytm", company_name="Paytm")

    assert norm["id"] == "lever_paytm_c6085ba8-0df2-42fe-b586-773dfabfbba9"
    assert norm["source"] == "lever"
    assert norm["source_job_id"] == "c6085ba8-0df2-42fe-b586-773dfabfbba9"
    assert norm["company_board"] == "paytm"
    assert norm["title"] == "Software Engineer - Backend"
    assert norm["company"] == "Paytm"
    assert norm["location"] == "Bengaluru, Karnataka"
    assert norm["country"] == "India"
    assert norm["is_india_opportunity"] is True
    assert norm["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm["is_direct_apply"] is True
    assert norm["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    assert norm["verification_method"] == "lever_api_direct"
    assert "Python" in norm["skills_required"] or "FastAPI" in norm["skills_required"]
    assert "Build high scale microservices" in norm["description"]


# --- 2. URL CLASSIFICATION ---

def test_02_direct_requisition_urls_accepted():
    """2. Direct Lever hosted and apply URLs are accepted as DIRECT_REQUISITION."""
    url1 = "https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9"
    t1, _ = classify_application_url(url1, company="Paytm")
    assert t1 == ApplicationUrlType.DIRECT_REQUISITION

    url2 = "https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9/apply"
    t2, _ = classify_application_url(url2, company="Paytm")
    assert t2 == ApplicationUrlType.DIRECT_REQUISITION


def test_03_generic_and_invalid_urls_rejected():
    """3. Top-level portals, searches, and invalid URLs are rejected."""
    t_portal, _ = classify_application_url("https://jobs.lever.co/paytm", company="Paytm")
    assert t_portal == ApplicationUrlType.CORPORATE_PORTAL

    t_search, _ = classify_application_url("https://jobs.lever.co/paytm?search=engineer", company="Paytm")
    assert t_search == ApplicationUrlType.SEARCH_RESULTS

    t_google, _ = classify_application_url("https://google.com/search?q=paytm+jobs", company="Paytm")
    assert t_google == ApplicationUrlType.SEARCH_RESULTS

    t_empty, _ = classify_application_url("", company="Paytm")
    assert t_empty == ApplicationUrlType.INVALID


# --- TASK 1 REGRESSION TESTS ---

def test_task1_valid_apply_url():
    """Task 1.1: Valid applyUrl becomes is_direct_apply=True and VERIFIED_ACTIVE."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(
        applyUrl="https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9/apply",
        hostedUrl="https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9",
    )
    norm = provider.normalize_lever_job(raw, "paytm")
    assert norm["is_direct_apply"] is True
    assert norm["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value


def test_task1_valid_hosted_url_when_apply_missing():
    """Task 1.2: Valid hostedUrl accepted as DIRECT_REQUISITION when applyUrl is missing."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(
        applyUrl="",
        hostedUrl="https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9",
    )
    norm = provider.normalize_lever_job(raw, "paytm")
    assert norm["apply_url"] == "https://jobs.lever.co/paytm/c6085ba8-0df2-42fe-b586-773dfabfbba9"
    assert norm["is_direct_apply"] is True
    assert norm["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value


def test_task1_corporate_hosted_url_rejected_when_apply_missing():
    """Task 1.3: Corporate/job-board hostedUrl rejected and excluded from public feed."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(
        applyUrl="",
        hostedUrl="https://jobs.lever.co/paytm",  # Top-level portal without requisition slug
    )
    norm = provider.normalize_lever_job(raw, "paytm")
    assert norm["is_direct_apply"] is False
    assert norm["url_type"] == ApplicationUrlType.CORPORATE_PORTAL.value
    assert norm["verification_status"] == OpportunityLifecycleStatus.PENDING_VERIFICATION.value


def test_task1_missing_apply_url_and_missing_hosted_url():
    """Task 1.4: Missing both applyUrl and hostedUrl marked INVALID."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(applyUrl=None, hostedUrl=None)
    norm = provider.normalize_lever_job(raw, "paytm")
    assert norm["is_direct_apply"] is False
    assert norm["url_type"] == ApplicationUrlType.INVALID.value
    assert norm["verification_status"] == OpportunityLifecycleStatus.INVALID.value


def test_task1_invalid_malformed_url():
    """Task 1.5: Malformed URL marked INVALID."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(applyUrl="javascript:void(0)", hostedUrl="")
    norm = provider.normalize_lever_job(raw, "paytm")
    assert norm["is_direct_apply"] is False
    assert norm["url_type"] == ApplicationUrlType.INVALID.value
    assert norm["verification_status"] == OpportunityLifecycleStatus.INVALID.value


def test_task1_search_results_url_rejected():
    """Task 1.6: Search results URL marked PENDING_VERIFICATION and is_direct_apply=False."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(applyUrl="https://jobs.lever.co/paytm?query=software", hostedUrl="")
    norm = provider.normalize_lever_job(raw, "paytm")
    assert norm["is_direct_apply"] is False
    assert norm["url_type"] == ApplicationUrlType.SEARCH_RESULTS.value
    assert norm["verification_status"] == OpportunityLifecycleStatus.PENDING_VERIFICATION.value


# --- 3. ZERO DATE FABRICATION ---

def test_04_zero_date_fabrication():
    """4. posted_at is parsed from createdAt ms epoch; updated_at is None (no fabrication)."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(createdAt=1783043640931)
    norm = provider.normalize_lever_job(raw, "paytm")

    assert norm["posted_at"] is not None
    assert norm["posted_at"].startswith("2026-")
    assert norm["updated_at"] is None  # Never fabricated


def test_05_missing_created_at_handled_safely():
    """5. Missing createdAt leaves posted_at as None without raising errors."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(createdAt=None)
    norm = provider.normalize_lever_job(raw, "paytm")

    assert norm["posted_at"] is None
    assert norm["posted_days_ago"] == 0


# --- 4. COUNTRY & INDIA RELEVANCE ---

def test_06_country_and_india_relevance():
    """6. Country and India relevance follow actual geography, not company description."""
    provider = LeverJobProvider()

    # Case A: Bengaluru, India
    raw_in = make_raw_lever_job(
        categories={"location": "Bengaluru, Karnataka"},
        descriptionPlain="Global operations center.",
    )
    norm_in = provider.normalize_lever_job(raw_in, "paytm")
    assert norm_in["country"] == "India"
    assert norm_in["is_india_opportunity"] is True

    # Case B: New York, NY
    raw_us = make_raw_lever_job(
        categories={"location": "New York, NY"},
        descriptionPlain="Paytm collaborates with engineering teams in Bangalore, India.",
    )
    norm_us = provider.normalize_lever_job(raw_us, "paytm")
    assert norm_us["country"] == "United States"
    assert norm_us["is_india_opportunity"] is False

    # Case C: Dubai, UAE
    raw_ae = make_raw_lever_job(
        categories={"location": "Dubai"},
        descriptionPlain="Headquartered in India.",
    )
    norm_ae = provider.normalize_lever_job(raw_ae, "paytm")
    assert norm_ae["country"] == "United Arab Emirates"
    assert norm_ae["is_india_opportunity"] is False

    # Case D: Remote alone
    raw_rem = make_raw_lever_job(
        categories={"location": "Remote"},
        workplaceType="remote",
        descriptionPlain="Fully remote role.",
    )
    norm_rem = provider.normalize_lever_job(raw_rem, "paytm")
    assert norm_rem["country"] is None
    assert norm_rem["is_india_opportunity"] is False


# --- 5. SENIORITY & FRESHER CLASSIFICATION ---

def test_07_seniority_signals_not_fresher():
    """7. Seniority signals (SDE II, III, IV, Senior, Lead, Manager) are non-fresher."""
    provider = LeverJobProvider()

    senior_titles = [
        "SDE II",
        "SDE III",
        "SDE IV - Data Engineer",
        "Senior Software Engineer",
        "Staff Software Engineer",
        "Lead Engineer - Cloud",
        "Engineering Manager",
        "Director of Engineering",
    ]

    for title in senior_titles:
        raw = make_raw_lever_job(text=title)
        norm = provider.normalize_lever_job(raw, "paytm")
        assert norm["fresher_friendly"] is False, f"Expected {title} to NOT be fresher friendly"
        assert norm["suitability_signal"] in ("EXPERIENCED", "EARLY_CAREER")


def test_08_genuine_fresher_and_trainee():
    """8. Graduate Trainee, Campus Hire, and explicit 0-1 yr roles are fresher friendly."""
    provider = LeverJobProvider()

    fresher_titles = [
        "Graduate Engineer Trainee",
        "Management Trainee",
        "Campus Hire - Software Engineer",
        "Associate Software Engineer",
    ]

    for title in fresher_titles:
        raw = make_raw_lever_job(
            text=title,
            descriptionPlain="Entry-level campus recruitment program for 2026 graduates. 0-1 years of experience.",
        )
        norm = provider.normalize_lever_job(raw, "paytm")
        assert norm["fresher_friendly"] is True, f"Expected {title} to be fresher friendly"


# --- 6. INTERNSHIP CLASSIFICATION ---

def test_09_genuine_internship_classification():
    """9. Genuine internships preserve internship metadata and structured eligibility."""
    provider = LeverJobProvider()

    # Case A: via structured commitment
    raw_comm = make_raw_lever_job(
        text="Software Development Engineer",
        categories={"commitment": "Intern", "location": "Bangalore"},
    )
    norm_comm = provider.normalize_lever_job(raw_comm, "paytm")
    assert norm_comm["job_type"] == "internship"
    assert norm_comm["experience_min"] == 0
    assert norm_comm["experience_max"] == 2
    assert norm_comm["internship_duration_months"] == 3
    assert norm_comm["student_friendly"] is True
    assert norm_comm["fresher_friendly"] is True

    # Case B: via title
    raw_title = make_raw_lever_job(
        text="Data Science Intern",
        categories={"commitment": "Full Time", "location": "Bangalore"},
    )
    norm_title = provider.normalize_lever_job(raw_title, "paytm")
    assert norm_title["job_type"] == "internship"
    assert norm_title["student_friendly"] is True


def test_10_full_time_experience_integrity():
    """10. Full-time listings without explicit experience do NOT receive fabricated experience_min=0."""
    provider = LeverJobProvider()
    raw = make_raw_lever_job(
        text="Backend Software Engineer",
        categories={"commitment": "Full Time", "location": "Bangalore"},
        descriptionPlain="Design scalable APIs using FastAPI.",
    )
    norm = provider.normalize_lever_job(raw, "paytm")
    assert norm["job_type"] == "full_time"
    assert norm["experience_min"] is None  # NO fabricated 0
    assert norm["experience_max"] is None


# --- 7. FAILURE MODES & NETWORK HANDLING ---

@pytest.mark.asyncio
async def test_11_fetch_company_openings_404_returns_empty():
    """11. 404 response on unknown board returns empty list gracefully."""
    provider = LeverJobProvider()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        jobs = await provider.fetch_company_openings("nonexistent_company_token_xyz")
        assert jobs == []


@pytest.mark.asyncio
async def test_12_fetch_timeout_raises_lever_network_error():
    """12. Timeout when fetching Lever board raises LeverNetworkError."""
    import httpx
    provider = LeverJobProvider()
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Connection timed out")):
        with pytest.raises(LeverNetworkError) as exc_info:
            await provider.fetch_company_openings("paytm")
        assert "Timeout connecting to Lever board" in str(exc_info.value)


@pytest.mark.asyncio
async def test_13_fetch_http_error_raises_lever_network_error():
    """13. HTTP 500/502 error raises LeverNetworkError."""
    import httpx
    provider = LeverJobProvider()
    req = httpx.Request("GET", "https://api.lever.co/v0/postings/paytm?mode=json")
    resp = httpx.Response(status_code=500, request=req)
    with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPStatusError("500 Server Error", request=req, response=resp)):
        with pytest.raises(LeverNetworkError) as exc_info:
            await provider.fetch_company_openings("paytm")
        assert "HTTP failure" in str(exc_info.value)


# --- 8. INVENTORY RECONCILIATION & SYNC ---

@pytest.mark.asyncio
async def test_14_authoritative_closure_of_disappeared_jobs():
    """14. Disappeared jobs on successful sync transition authoritatively to CLOSED."""
    import mongomock_motor
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_roleradar_lever_reconciliation"]

    # Prepopulate with 2 active Paytm jobs
    await db[Collections.JOBS].insert_many([
        {
            "id": "lever_paytm_job_001",
            "source": "lever",
            "source_job_id": "job_001",
            "company_board": "paytm",
            "title": "Backend Engineer",
            "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
            "is_direct_apply": True,
        },
        {
            "id": "lever_paytm_job_002",
            "source": "lever",
            "source_job_id": "job_002",
            "company_board": "paytm",
            "title": "Frontend Engineer",
            "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
            "is_direct_apply": True,
        },
    ])

    provider = LeverJobProvider()

    # Simulate Lever now returning ONLY job_001 (job_002 disappeared/closed)
    fresh_feed = [
        make_raw_lever_job(
            id="job_001",
            text="Backend Engineer",
            hostedUrl="https://jobs.lever.co/paytm/job_001",
            applyUrl="https://jobs.lever.co/paytm/job_001/apply",
        )
    ]

    with patch.object(provider, "fetch_company_openings", return_value=fresh_feed):
        stats = await provider.sync_company_openings(db, "paytm")

    assert stats["fetched"] == 1
    assert stats["verified_active"] == 1
    assert stats["closed"] == 1

    # Verify job_001 remains active
    doc1 = await db[Collections.JOBS].find_one({"id": "lever_paytm_job_001"})
    assert doc1["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value

    # Verify job_002 transitioned to CLOSED
    doc2 = await db[Collections.JOBS].find_one({"id": "lever_paytm_job_002"})
    assert doc2["verification_status"] == OpportunityLifecycleStatus.CLOSED.value
    assert doc2["is_direct_apply"] is False


@pytest.mark.asyncio
async def test_15_network_failure_does_not_close_jobs():
    """15. Temporary network/API failure must NOT close existing jobs (non-destructive)."""
    import mongomock_motor
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_roleradar_lever_network_failure"]

    await db[Collections.JOBS].insert_one({
        "id": "lever_paytm_job_persists",
        "source": "lever",
        "source_job_id": "job_persists",
        "company_board": "paytm",
        "title": "Backend Engineer",
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "is_direct_apply": True,
    })

    provider = LeverJobProvider()

    # Simulate network error during fetch
    with patch.object(provider, "fetch_company_openings", side_effect=LeverNetworkError("Connection refused")):
        stats = await provider.sync_company_openings(db, "paytm")

    assert len(stats["errors"]) > 0
    assert stats["closed"] == 0

    # Verify existing job is untouched
    doc = await db[Collections.JOBS].find_one({"id": "lever_paytm_job_persists"})
    assert doc["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value


# --- 9. DEDUPLICATION & MULTI-PROVIDER COEXISTENCE ---

@pytest.mark.asyncio
async def test_16_deduplication_repeated_sync():
    """16. Repeated syncs of the same Lever listing result in one canonical opportunity."""
    import mongomock_motor
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_roleradar_lever_dedup"]

    provider = LeverJobProvider()
    feed = [make_raw_lever_job(id="dedup_job_1", text="Data Scientist")]

    with patch.object(provider, "fetch_company_openings", return_value=feed):
        # Sync 1
        await provider.sync_company_openings(db, "paytm")
        # Sync 2
        await provider.sync_company_openings(db, "paytm")

    count = await db[Collections.JOBS].count_documents({"source": "lever", "source_job_id": "dedup_job_1"})
    assert count == 1


@pytest.mark.asyncio
async def test_17_multi_provider_coexistence():
    """17. Greenhouse and Lever opportunities coexist in the same canonical collection."""
    import mongomock_motor
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_roleradar_multi_provider"]

    now_iso = datetime.now(timezone.utc).isoformat()

    # Insert a Greenhouse job
    await db[Collections.JOBS].insert_one({
        "id": "gh_postman_12345",
        "source": "greenhouse",
        "source_job_id": "12345",
        "company_board": "postman",
        "title": "Full Stack Engineer",
        "company": "Postman",
        "country": "India",
        "location": "Bengaluru, India",
        "is_india_opportunity": True,
        "is_direct_apply": True,
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "last_verified_at": now_iso,
        "apply_url": "https://boards.greenhouse.io/postman/jobs/12345",
    })

    # Insert a Lever job
    await db[Collections.JOBS].insert_one({
        "id": "lever_meesho_67890",
        "source": "lever",
        "source_job_id": "67890",
        "company_board": "meesho",
        "title": "Android Engineer",
        "company": "Meesho",
        "country": "India",
        "location": "Bangalore, India",
        "is_india_opportunity": True,
        "is_direct_apply": True,
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "last_verified_at": now_iso,
        "apply_url": "https://jobs.lever.co/meesho/67890/apply",
    })

    curated = CuratedJobProvider(db)
    results = await curated.search({})

    # Both live ATS opportunities appear in canonical discovery feed
    sources = {r["source"] for r in results}
    assert "greenhouse" in sources
    assert "lever" in sources
    assert len(results) == 2


@pytest.mark.asyncio
async def test_18_user_isolation_preserved():
    """18. Adding Lever opportunities does not weaken custom job ownership and isolation."""
    import mongomock_motor
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_roleradar_user_isolation"]

    # Custom job owned by user_A
    await db[Collections.JOBS].insert_one({
        "id": "custom_job_user_a",
        "user_id": "user_a_123",
        "source": "custom",
        "title": "Private Application",
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "is_direct_apply": True,
    })

    # Lever job (global, user_id=None)
    await db[Collections.JOBS].insert_one({
        "id": "lever_cred_001",
        "source": "lever",
        "source_job_id": "001",
        "company_board": "cred",
        "title": "Backend Engineer",
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "is_direct_apply": True,
        "country": "India",
    })

    curated = CuratedJobProvider(db)

    # Searching as user_b cannot see user_a's private custom job
    user_b_feed = await curated.search({"user_id": "user_b_456"})
    job_ids = [j["id"] for j in user_b_feed]
    assert "lever_cred_001" in job_ids
    assert "custom_job_user_a" not in job_ids
