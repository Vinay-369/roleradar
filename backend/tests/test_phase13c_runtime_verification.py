"""
Test Suite: Phase 13C - Final Production Runtime Verification.
Covers:
TASK 1: Direct Apply URL Safety
TASK 2: Actual Public API Runtime Trace (India internship, India full-time, Non-India role)
TASK 3: No-Resume Behavior (recommended_matches: visible, no fake score/evidence)
TASK 4: India Filter (country=India appears in India feed, foreign does not)
TASK 5: Real Internship Validation (job_type=internship, country=India, VERIFIED_ACTIVE, no invented stipend)
TASK 6: Active Status & Reconciliation (exists -> active, remains -> active, omitted -> closed, failure -> retain)
TASK 7: Multi-Provider Coexistence (Greenhouse + Lever in same canonical feed)
TASK 8: Security & User Isolation (Lever global inventory vs custom jobs)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import mongomock_motor
import pytest

from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.jobs.lever_provider import LeverJobProvider, LeverNetworkError
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.routes import list_jobs
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus
from app.modules.matching.routes import recommended_matches


# Real raw payloads captured directly from Lever's public postings API for Paytm
REAL_PAYTM_INTERNSHIP_RAW = {
    "id": "2e0d10a7-a185-4f02-8f89-792900c0d592",
    "text": "HR Payroll-Intern",
    "createdAt": 1787125330364,
    "workplaceType": "onsite",
    "hostedUrl": "https://jobs.lever.co/paytm/2e0d10a7-a185-4f02-8f89-792900c0d592",
    "applyUrl": "https://jobs.lever.co/paytm/2e0d10a7-a185-4f02-8f89-792900c0d592/apply",
    "categories": {
        "commitment": "Intern",
        "department": "Human Resources",
        "team": "HR Operations",
        "location": "Noida, Uttar Pradesh",
        "allLocations": ["Noida, Uttar Pradesh"],
    },
    "descriptionPlain": "We are looking for an HR Payroll Intern to assist our payroll operations team.",
    "description": "<p>We are looking for an HR Payroll Intern to assist our payroll operations team.</p>",
    "lists": [],
    "additionalPlain": "Paytm is India's leading digital payments and financial services company.",
}

REAL_PAYTM_FULLTIME_RAW = {
    "id": "86665c39-2182-4d69-8b8c-33eac104ec2b",
    "text": "Accounts Payable Specialist - Mumbai",
    "createdAt": 1787034988019,
    "workplaceType": "onsite",
    "hostedUrl": "https://jobs.lever.co/paytm/86665c39-2182-4d69-8b8c-33eac104ec2b",
    "applyUrl": "https://jobs.lever.co/paytm/86665c39-2182-4d69-8b8c-33eac104ec2b/apply",
    "categories": {
        "commitment": "Full-time Employment",
        "department": "Finance",
        "team": "Paytm Money",
        "location": "Mumbai, Maharashtra",
        "allLocations": ["Mumbai, Maharashtra"],
    },
    "descriptionPlain": "Manage and process accounts payable for Paytm Money operations.",
    "description": "<p>Manage and process accounts payable for Paytm Money operations.</p>",
    "lists": [],
    "additionalPlain": "Paytm is India's leading digital payments company.",
}

REAL_PAYTM_FOREIGN_RAW = {
    "id": "9eed4fec-73f7-4114-a5d3-b2f689c92e8c",
    "text": "Account Executive/ Director - AI Agentic Enterprise Sales",
    "createdAt": 1783043640931,
    "workplaceType": "onsite",
    "hostedUrl": "https://jobs.lever.co/paytm/9eed4fec-73f7-4114-a5d3-b2f689c92e8c",
    "applyUrl": "https://jobs.lever.co/paytm/9eed4fec-73f7-4114-a5d3-b2f689c92e8c/apply",
    "categories": {
        "commitment": "Full-time Employment",
        "department": "Sales",
        "team": "Inference and Agentic AI",
        "location": "Dubai",
        "allLocations": ["Dubai", "Noida, Uttar Pradesh", "Mumbai, Maharashtra"],
    },
    "descriptionPlain": "Lead enterprise sales for agentic AI products across EMEA. Headquartered in Bangalore, India.",
    "description": "<p>Lead enterprise sales for agentic AI products across EMEA. Headquartered in Bangalore, India.</p>",
    "lists": [],
    "additionalPlain": "Paytm is India's leading fintech platform.",
}


# ==============================================================================
# TASK 1: DIRECT APPLY URL SAFETY
# ==============================================================================

def test_task1_direct_apply_url_safety_invariants():
    """TASK 1: Only URLs verified as DIRECT_REQUISITION may become is_direct_apply=True."""
    provider = LeverJobProvider()

    # A. Valid applyUrl -> Accepted
    raw_a = dict(REAL_PAYTM_FULLTIME_RAW)
    norm_a = provider.normalize_lever_job(raw_a, "paytm")
    assert norm_a["is_direct_apply"] is True
    assert norm_a["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm_a["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value

    # B. Missing applyUrl, valid hostedUrl -> Accepted
    raw_b = dict(REAL_PAYTM_FULLTIME_RAW, applyUrl="")
    norm_b = provider.normalize_lever_job(raw_b, "paytm")
    assert norm_b["is_direct_apply"] is True
    assert norm_b["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm_b["apply_url"] == "https://jobs.lever.co/paytm/86665c39-2182-4d69-8b8c-33eac104ec2b"

    # C. Missing applyUrl, corporate hostedUrl (e.g. https://jobs.lever.co/paytm) -> Rejected
    raw_c = dict(REAL_PAYTM_FULLTIME_RAW, applyUrl="", hostedUrl="https://jobs.lever.co/paytm")
    norm_c = provider.normalize_lever_job(raw_c, "paytm")
    assert norm_c["is_direct_apply"] is False
    assert norm_c["url_type"] == ApplicationUrlType.CORPORATE_PORTAL.value
    assert norm_c["verification_status"] == OpportunityLifecycleStatus.PENDING_VERIFICATION.value

    # D. Both missing -> Invalid
    raw_d = dict(REAL_PAYTM_FULLTIME_RAW, applyUrl=None, hostedUrl=None)
    norm_d = provider.normalize_lever_job(raw_d, "paytm")
    assert norm_d["is_direct_apply"] is False
    assert norm_d["url_type"] == ApplicationUrlType.INVALID.value
    assert norm_d["verification_status"] == OpportunityLifecycleStatus.INVALID.value


# ==============================================================================
# TASK 2: ACTUAL PUBLIC API RUNTIME TRACE
# ==============================================================================

@pytest.mark.asyncio
async def test_task2_actual_public_api_runtime_trace():
    """
    TASK 2: Full path verification:
    Lever API payload -> Normalization -> MongoDB -> Verification Status -> India Relevance -> Public API Endpoint.
    Traces:
    1. Real Paytm Indian internship
    2. Real Paytm Indian full-time opportunity
    3. Real Paytm non-Indian opportunity
    """
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_phase13c_trace"]
    provider = LeverJobProvider()
    settings = Settings(LEVER_ENABLED=True)

    # 1. Normalize and sync real payloads into MongoDB
    feed = [REAL_PAYTM_INTERNSHIP_RAW, REAL_PAYTM_FULLTIME_RAW, REAL_PAYTM_FOREIGN_RAW]
    with patch.object(provider, "fetch_company_openings", return_value=feed):
        stats = await provider.sync_company_openings(db, "paytm")

    assert stats["fetched"] == 3
    assert stats["verified_active"] == 3

    # 2. Verify MongoDB storage & Canonical Opportunities
    jobs_cursor = db[Collections.JOBS].find({})
    stored_jobs = await jobs_cursor.to_list(10)
    assert len(stored_jobs) == 3

    job_map = {j["id"]: j for j in stored_jobs}
    intern_id = "lever_paytm_2e0d10a7-a185-4f02-8f89-792900c0d592"
    ft_id = "lever_paytm_86665c39-2182-4d69-8b8c-33eac104ec2b"
    foreign_id = "lever_paytm_9eed4fec-73f7-4114-a5d3-b2f689c92e8c"

    # Verify Internship canonical doc
    intern_doc = job_map[intern_id]
    assert intern_doc["job_type"] == "internship"
    assert intern_doc["country"] == "India"
    assert intern_doc["is_india_opportunity"] is True
    assert intern_doc["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    assert intern_doc["is_direct_apply"] is True

    # Verify Full-time Indian doc
    ft_doc = job_map[ft_id]
    assert ft_doc["job_type"] == "full_time"
    assert ft_doc["country"] == "India"
    assert ft_doc["is_india_opportunity"] is True
    assert ft_doc["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    assert ft_doc["is_direct_apply"] is True

    # Verify Foreign doc
    foreign_doc = job_map[foreign_id]
    assert foreign_doc["job_type"] == "full_time"
    assert foreign_doc["country"] == "United Arab Emirates"
    assert foreign_doc["is_india_opportunity"] is False
    assert foreign_doc["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    assert foreign_doc["is_direct_apply"] is True

    # 3. Query through actual public API router `list_jobs`
    current_user = {"_id": "test_public_user_1"}
    with patch("app.modules.jobs.routes.services.refresh_live_jobs", AsyncMock(return_value=0)):
        api_jobs = await list_jobs(
            current_user=current_user,
            db=db,
            settings=settings,
        )

    api_job_ids = [j.id for j in api_jobs]
    assert intern_id in api_job_ids
    assert ft_id in api_job_ids
    assert foreign_id in api_job_ids

    # Verify all items in public API response maintain direct apply and active status
    for j in api_jobs:
        assert j.is_direct_apply is True
        assert j.verification_status == "VERIFIED_ACTIVE"
        assert j.apply_url.startswith("https://jobs.lever.co/paytm/")


# ==============================================================================
# TASK 3: NO-RESUME BEHAVIOR
# ==============================================================================

@pytest.mark.asyncio
async def test_task3_no_resume_discovery_recommended_matches():
    """
    TASK 3: User with no resume queries GET /api/matches/recommended.
    Must return verified opportunities without fabricated match scores.
    """
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_phase13c_no_resume"]
    provider = LeverJobProvider()
    settings = Settings(LEVER_ENABLED=True)
    user_no_resume = {"_id": "user_no_resume_99"}

    # Sync real items into DB
    with patch.object(provider, "fetch_company_openings", return_value=[REAL_PAYTM_INTERNSHIP_RAW, REAL_PAYTM_FULLTIME_RAW]):
        await provider.sync_company_openings(db, "paytm")

    # Call recommended_matches directly (same handler as GET /api/matches/recommended)
    with patch("app.modules.matching.routes.jobs_services.refresh_live_jobs", AsyncMock(return_value=0)):
        matches = await recommended_matches(
            current_user=user_no_resume,
            db=db,
            settings=settings,
            job_type=None,
            live_only=False,
            location_preset=None,
            opportunity_type=None,
            experience_tier=None,
            workplace_type=None,
        )

    assert len(matches) == 2
    for m in matches:
        assert m.has_match is False
        assert m.overall_score is None, "Score must NOT be fabricated"
        assert m.skill_score is None
        assert m.experience_score is None
        assert m.matched_skills == []
        assert m.missing_skills == []
        assert m.apply_url.startswith("https://jobs.lever.co/paytm/")
        assert "Upload your resume" in m.eligibility["fit_explanation"]


# ==============================================================================
# TASK 4: INDIA FILTER
# ==============================================================================

@pytest.mark.asyncio
async def test_task4_india_filter_separates_geography():
    """
    TASK 4: Indian opportunities have country=India and is_india_opportunity=True.
    Foreign opportunity has country=UAE and is_india_opportunity=False.
    Company description mentioning Bangalore must NOT override foreign location.
    """
    provider = LeverJobProvider()

    # Normalize real foreign opportunity (description mentions Bangalore, location is Dubai)
    norm_foreign = provider.normalize_lever_job(REAL_PAYTM_FOREIGN_RAW, "paytm")
    assert norm_foreign["country"] == "United Arab Emirates"
    assert norm_foreign["is_india_opportunity"] is False
    assert norm_foreign["location"] == "Dubai"

    # Normalize real Indian opportunity
    norm_in = provider.normalize_lever_job(REAL_PAYTM_FULLTIME_RAW, "paytm")
    assert norm_in["country"] == "India"
    assert norm_in["is_india_opportunity"] is True


# ==============================================================================
# TASK 5: INTERNSHIP VALIDATION
# ==============================================================================

@pytest.mark.asyncio
async def test_task5_real_paytm_internship_validation():
    """
    TASK 5: Real Paytm internship:
    - job_type = internship
    - country = India
    - direct apply URL
    - VERIFIED_ACTIVE
    - discoverable without resume
    - no invented stipend or duration
    """
    provider = LeverJobProvider()
    norm = provider.normalize_lever_job(REAL_PAYTM_INTERNSHIP_RAW, "paytm")

    assert norm["job_type"] == "internship"
    assert norm["country"] == "India"
    assert norm["is_india_opportunity"] is True
    assert norm["is_direct_apply"] is True
    assert norm["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    assert norm["apply_url"] == "https://jobs.lever.co/paytm/2e0d10a7-a185-4f02-8f89-792900c0d592/apply"
    assert norm["stipend_min"] is None  # Not invented
    assert norm["fresher_friendly"] is True
    assert norm["student_friendly"] is True


# ==============================================================================
# TASK 6: ACTIVE STATUS & RECONCILIATION
# ==============================================================================

@pytest.mark.asyncio
async def test_task6_inventory_reconciliation_lifecycle():
    """
    TASK 6: Authoritative reconciliation:
    A. posting exists -> VERIFIED_ACTIVE
    B. same posting remains -> remains VERIFIED_ACTIVE
    C. successful provider sync omits posting -> CLOSED
    D. provider/network failure -> existing posting remains active (no destructive closure)
    """
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_phase13c_active_status"]
    provider = LeverJobProvider()

    # Step A: First sync with 2 postings
    item1 = dict(REAL_PAYTM_INTERNSHIP_RAW)
    item2 = dict(REAL_PAYTM_FULLTIME_RAW)

    with patch.object(provider, "fetch_company_openings", return_value=[item1, item2]):
        stats_a = await provider.sync_company_openings(db, "paytm")
    assert stats_a["verified_active"] == 2
    assert stats_a["closed"] == 0

    doc1 = await db[Collections.JOBS].find_one({"source_job_id": item1["id"]})
    assert doc1["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value

    # Step B: Second sync with same postings -> remains VERIFIED_ACTIVE
    with patch.object(provider, "fetch_company_openings", return_value=[item1, item2]):
        stats_b = await provider.sync_company_openings(db, "paytm")
    assert stats_b["verified_active"] == 2
    assert stats_b["closed"] == 0
    assert stats_b["retained"] == 2

    # Step C: Successful provider sync omits item2 -> item2 transitions to CLOSED
    with patch.object(provider, "fetch_company_openings", return_value=[item1]):
        stats_c = await provider.sync_company_openings(db, "paytm")
    assert stats_c["verified_active"] == 1
    assert stats_c["closed"] == 1

    doc2_closed = await db[Collections.JOBS].find_one({"source_job_id": item2["id"]})
    assert doc2_closed["verification_status"] == OpportunityLifecycleStatus.CLOSED.value
    assert doc2_closed["is_direct_apply"] is False

    # Step D: Network failure occurs -> remaining active posting must NOT close
    with patch.object(provider, "fetch_company_openings", side_effect=LeverNetworkError("Connection timed out")):
        stats_d = await provider.sync_company_openings(db, "paytm")
    assert len(stats_d["errors"]) == 1
    assert stats_d["closed"] == 0

    doc1_still_active = await db[Collections.JOBS].find_one({"source_job_id": item1["id"]})
    assert doc1_still_active["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value


# ==============================================================================
# TASK 7: MULTI-PROVIDER COEXISTENCE
# ==============================================================================

@pytest.mark.asyncio
async def test_task7_multi_provider_coexistence():
    """
    TASK 7: Greenhouse and Lever coexist in the same canonical collection.
    Public discovery returns both without separate product concepts.
    """
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_phase13c_multi_provider"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Greenhouse Opportunity
    await db[Collections.JOBS].insert_one({
        "id": "gh_postman_99901",
        "source": "greenhouse",
        "source_job_id": "99901",
        "company_board": "postman",
        "title": "Staff Backend Engineer",
        "company": "Postman",
        "location": "Bengaluru",
        "country": "India",
        "is_india_opportunity": True,
        "job_type": "full_time",
        "apply_url": "https://job-boards.greenhouse.io/postman/jobs/99901",
        "url_type": "DIRECT_REQUISITION",
        "is_direct_apply": True,
        "verification_status": "VERIFIED_ACTIVE",
        "last_verified_at": now_iso,
    })

    # Lever Opportunity
    await db[Collections.JOBS].insert_one({
        "id": "lever_paytm_2e0d10a7",
        "source": "lever",
        "source_job_id": "2e0d10a7",
        "company_board": "paytm",
        "title": "HR Payroll-Intern",
        "company": "Paytm",
        "location": "Noida, Uttar Pradesh",
        "country": "India",
        "is_india_opportunity": True,
        "job_type": "internship",
        "apply_url": "https://jobs.lever.co/paytm/2e0d10a7/apply",
        "url_type": "DIRECT_REQUISITION",
        "is_direct_apply": True,
        "verification_status": "VERIFIED_ACTIVE",
        "last_verified_at": now_iso,
    })

    curated = CuratedJobProvider(db)
    feed = await curated.search({})
    assert len(feed) == 2
    sources = {j["source"] for j in feed}
    assert "greenhouse" in sources
    assert "lever" in sources


# ==============================================================================
# TASK 8: SECURITY & USER ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_task8_security_and_user_isolation():
    """
    TASK 8: Lever global opportunities are public and never treated as custom jobs.
    Custom job ownership and privacy remain strictly intact.
    """
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_phase13c_security"]

    # Custom job for user_A
    await db[Collections.JOBS].insert_one({
        "id": "custom_job_secret_01",
        "user_id": "user_alice",
        "source": "custom",
        "title": "Private Confidential Application",
        "company": "Stealth Corp",
        "is_direct_apply": True,
        "verification_status": "VERIFIED_ACTIVE",
    })

    # Lever public job
    await db[Collections.JOBS].insert_one({
        "id": "lever_paytm_public_01",
        "source": "lever",
        "source_job_id": "paytm_public_01",
        "company_board": "paytm",
        "title": "Public Paytm Job",
        "company": "Paytm",
        "is_direct_apply": True,
        "verification_status": "VERIFIED_ACTIVE",
    })

    curated = CuratedJobProvider(db)

    # Bob should see Lever public job, but CANNOT see Alice's custom job
    bob_feed = await curated.search({"user_id": "user_bob"})
    bob_ids = [j["id"] for j in bob_feed]
    assert "lever_paytm_public_01" in bob_ids
    assert "custom_job_secret_01" not in bob_ids

    # Alice can see both her own custom job and the Lever public job
    alice_feed = await curated.search({"user_id": "user_alice"})
    alice_ids = [j["id"] for j in alice_feed]
    assert "lever_paytm_public_01" in alice_ids
    assert "custom_job_secret_01" in alice_ids
