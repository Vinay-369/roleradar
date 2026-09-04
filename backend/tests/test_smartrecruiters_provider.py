"""
Unit Test Suite: SmartRecruiters Direct Live Opportunity Provider.
Tests:
- successful API response
- pagination
- empty board
- malformed response
- timeout
- HTTP 429
- HTTP 5xx
- direct posting URL
- direct apply URL
- corporate portal rejection
- malformed URL rejection
- India location
- foreign location
- India company boilerplate must not affect geography
- internship classification
- entry-level classification
- undisclosed experience remains undisclosed
- explicit numeric experience preservation
- salary/stipend non-fabrication
- releasedDate preservation
- inventory reconciliation
- disappeared requisition -> CLOSED
- network failure -> preserve active
- canonical source ID
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx
import mongomock_motor
import pytest

from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.jobs.smartrecruiters_provider import (
    SmartRecruitersJobProvider,
    SmartRecruitersNetworkError,
    is_internship_opportunity,
)
from app.modules.jobs.url_classifier import ApplicationUrlType
from app.modules.jobs.verification import OpportunityLifecycleStatus


# --- Realistic Mock Payloads from SmartRecruiters API ---

SAMPLE_SR_INDIA_ENGINEER_RAW = {
    "id": "744000147412989",
    "name": "DevOps CI/CD Engineer",
    "uuid": "df49161a-1af7-4cef-89b6-27594d58c065",
    "refNumber": "REF294331B",
    "company": {
        "identifier": "BoschGroup",
        "name": "Bosch Group"
    },
    "releasedDate": "2026-09-04T04:50:40.198Z",
    "location": {
        "city": "Bengaluru",
        "region": "Karnataka",
        "country": "in",
        "address": "Electronic City, Hosur Road",
        "postalCode": "560100",
        "remote": False,
        "hybrid": True,
        "fullLocation": "Bengaluru, Karnataka, India"
    },
    "industry": {
        "id": "computer_software",
        "label": "Computer Software"
    },
    "function": {
        "id": "information_technology",
        "label": "Information Technology"
    },
    "typeOfEmployment": {
        "id": "permanent",
        "label": "Full-time"
    },
    "experienceLevel": {
        "id": "associate",
        "label": "Associate"
    },
    "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/744000147412989",
    "applyUrl": "https://jobs.smartrecruiters.com/BoschGroup/744000147412989/apply",
    "customField": [
        {"fieldLabel": "Division", "valueLabel": "BGSW"}
    ]
}

SAMPLE_SR_INDIA_INTERNSHIP_RAW = {
    "id": "744000147400001",
    "name": "Software Engineering Intern - Frontend",
    "company": {
        "identifier": "BlueberryLabsPrivateLimited",
        "name": "Blueberry Labs"
    },
    "releasedDate": "2026-09-01T10:00:00.000Z",
    "location": {
        "city": "Hyderabad",
        "country": "in",
        "fullLocation": "Hyderabad, Telangana, India",
        "remote": False,
        "hybrid": False
    },
    "typeOfEmployment": {
        "id": "internship",
        "label": "Internship"
    },
    "experienceLevel": {
        "id": "internship",
        "label": "Internship"
    },
    "postingUrl": "https://jobs.smartrecruiters.com/BlueberryLabsPrivateLimited/744000147400001",
    "applyUrl": "https://jobs.smartrecruiters.com/BlueberryLabsPrivateLimited/744000147400001/apply"
}

SAMPLE_SR_FOREIGN_ROLE_RAW = {
    "id": "744000147409729",
    "name": "Senior Network Programmer",
    "company": {
        "identifier": "Ubisoft2",
        "name": "Ubisoft"
    },
    "releasedDate": "2026-09-04T03:57:29.534Z",
    "location": {
        "city": "Chengdu",
        "region": "Sichuan",
        "country": "cn",
        "fullLocation": "Chengdu, Sichuan, China",
        "remote": False,
        "hybrid": False
    },
    "typeOfEmployment": {
        "id": "permanent",
        "label": "Full-time"
    },
    "experienceLevel": {
        "id": "mid_senior_level",
        "label": "Mid-Senior Level"
    },
    "postingUrl": "https://jobs.smartrecruiters.com/Ubisoft2/744000147409729",
    "applyUrl": "https://jobs.smartrecruiters.com/Ubisoft2/744000147409729/apply"
}


# --- 1. Successful API Response & Normalization ---

def test_successful_smartrecruiters_normalization():
    provider = SmartRecruitersJobProvider()
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    job = provider.normalize_smartrecruiters_job(SAMPLE_SR_INDIA_ENGINEER_RAW, "BoschGroup", now=now)

    assert job["id"] == "smartrecruiters_boschgroup_744000147412989"
    assert job["source"] == "smartrecruiters"
    assert job["source_job_id"] == "744000147412989"
    assert job["title"] == "DevOps CI/CD Engineer"
    assert job["company"] == "Bosch Group"
    assert job["country"] == "India"
    assert job["is_india_opportunity"] is True
    assert job["is_india_relevant"] is True
    assert job["workplace_type"] == "HYBRID"
    assert job["job_type"] == "full_time"
    assert job["opportunity_type"] == "FULL_TIME"
    assert job["experience_min"] is None  # Undisclosed numeric min must not be fabricated
    assert job["experience_level"] == "Associate"
    assert job["verification_status"] == "VERIFIED_ACTIVE"
    assert job["is_direct_apply"] is True
    assert job["url_type"] == "DIRECT_REQUISITION"
    assert job["posted_at"] == "2026-09-04T04:50:40.198000+00:00"
    assert job["updated_at"] is None  # Zero date fabrication


# --- 2. Pagination ---

@pytest.mark.asyncio
async def test_smartrecruiters_pagination():
    provider = SmartRecruitersJobProvider()

    page1 = {
        "totalFound": 3,
        "content": [{"id": "1", "name": "Job 1"}, {"id": "2", "name": "Job 2"}]
    }
    page2 = {
        "totalFound": 3,
        "content": [{"id": "3", "name": "Job 3"}]
    }

    mock_resp1 = httpx.Response(200, json=page1, request=httpx.Request("GET", "http://test"))
    mock_resp2 = httpx.Response(200, json=page2, request=httpx.Request("GET", "http://test"))

    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=[mock_resp1, mock_resp2])):
        jobs = await provider.fetch_company_openings("BoschGroup", limit_per_page=2)
        assert len(jobs) == 3
        assert [j["id"] for j in jobs] == ["1", "2", "3"]


# --- 3. Empty Board Handling ---

@pytest.mark.asyncio
async def test_smartrecruiters_empty_board():
    provider = SmartRecruitersJobProvider()
    mock_resp = httpx.Response(200, json={"totalFound": 0, "content": []}, request=httpx.Request("GET", "http://test"))
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        jobs = await provider.fetch_company_openings("EmptyCompany")
        assert jobs == []


# --- 4. Malformed Response Handling ---

@pytest.mark.asyncio
async def test_smartrecruiters_malformed_response():
    provider = SmartRecruitersJobProvider()
    mock_resp = httpx.Response(200, text="not-json", request=httpx.Request("GET", "http://test"))
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with pytest.raises(Exception):
            await provider.fetch_company_openings("BadCompany")


# --- 5. Timeout Handling ---

@pytest.mark.asyncio
async def test_smartrecruiters_timeout_raises_network_error():
    provider = SmartRecruitersJobProvider()
    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
        with pytest.raises(SmartRecruitersNetworkError):
            await provider.fetch_company_openings("SlowCompany")


# --- 6. HTTP 429 Rate Limiting ---

@pytest.mark.asyncio
async def test_smartrecruiters_429_rate_limit():
    provider = SmartRecruitersJobProvider()
    mock_resp = httpx.Response(429, request=httpx.Request("GET", "http://test"))
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SmartRecruitersNetworkError) as exc_info:
            await provider.fetch_company_openings("RateLimited")
        assert "429" in str(exc_info.value)


# --- 7. HTTP 5xx Server Error ---

@pytest.mark.asyncio
async def test_smartrecruiters_500_server_error():
    provider = SmartRecruitersJobProvider()
    mock_resp = httpx.Response(500, request=httpx.Request("GET", "http://test"))
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SmartRecruitersNetworkError) as exc_info:
            await provider.fetch_company_openings("ServerError")
        assert "500" in str(exc_info.value)


# --- 8. Direct Posting URL & Direct Apply URL Validation ---

def test_smartrecruiters_direct_url_validation():
    provider = SmartRecruitersJobProvider()
    
    # 1. Direct applyUrl
    job1 = provider.normalize_smartrecruiters_job(SAMPLE_SR_INDIA_ENGINEER_RAW, "BoschGroup")
    assert job1["is_direct_apply"] is True
    assert job1["url_type"] == "DIRECT_REQUISITION"
    assert "https://jobs.smartrecruiters.com/BoschGroup/744000147412989" in job1["apply_url"]

    # 2. Direct postingUrl fallback when applyUrl is missing
    raw_no_apply = dict(SAMPLE_SR_INDIA_ENGINEER_RAW)
    raw_no_apply["applyUrl"] = ""
    raw_no_apply["postingUrl"] = "https://jobs.smartrecruiters.com/BoschGroup/744000147412989"
    job2 = provider.normalize_smartrecruiters_job(raw_no_apply, "BoschGroup")
    assert job2["is_direct_apply"] is True
    assert job2["url_type"] == "DIRECT_REQUISITION"


# --- 9. Corporate Portal & Malformed URL Rejection ---

def test_smartrecruiters_corporate_portal_and_malformed_rejection():
    provider = SmartRecruitersJobProvider()

    # Generic portal URL
    raw_portal = dict(SAMPLE_SR_INDIA_ENGINEER_RAW)
    raw_portal["applyUrl"] = "https://jobs.smartrecruiters.com/BoschGroup"
    raw_portal["postingUrl"] = "https://jobs.smartrecruiters.com/BoschGroup"
    job_portal = provider.normalize_smartrecruiters_job(raw_portal, "BoschGroup")
    assert job_portal["is_direct_apply"] is False
    assert job_portal["verification_status"] == OpportunityLifecycleStatus.PENDING_VERIFICATION.value

    # Malformed URL
    raw_malformed = dict(SAMPLE_SR_INDIA_ENGINEER_RAW)
    raw_malformed["applyUrl"] = "not_a_valid_url"
    raw_malformed["postingUrl"] = "not_a_valid_url"
    job_malformed = provider.normalize_smartrecruiters_job(raw_malformed, "BoschGroup")
    assert job_malformed["is_direct_apply"] is False
    assert job_malformed["url_type"] == ApplicationUrlType.INVALID.value


# --- 10. India Location & Foreign Location Classification ---

def test_smartrecruiters_india_and_foreign_geography():
    provider = SmartRecruitersJobProvider()

    # India
    india_job = provider.normalize_smartrecruiters_job(SAMPLE_SR_INDIA_ENGINEER_RAW, "BoschGroup")
    assert india_job["country"] == "India"
    assert india_job["is_india_relevant"] is True

    # Foreign
    foreign_job = provider.normalize_smartrecruiters_job(SAMPLE_SR_FOREIGN_ROLE_RAW, "Ubisoft2")
    assert foreign_job["country"] == "China"
    assert foreign_job["is_india_relevant"] is False


# --- 11. Company Boilerplate Isolation ---

def test_smartrecruiters_company_boilerplate_must_not_affect_geography():
    provider = SmartRecruitersJobProvider()
    foreign_with_india_desc = dict(SAMPLE_SR_FOREIGN_ROLE_RAW)
    foreign_with_india_desc["jobAd"] = {
        "sections": {
            "companyDescription": {
                "text": "Ubisoft operates in Paris, London, Montreal, San Francisco, and Pune, India."
            }
        }
    }
    job = provider.normalize_smartrecruiters_job(foreign_with_india_desc, "Ubisoft2")
    assert job["country"] == "China"
    assert job["is_india_relevant"] is False


# --- 12. Internship & Entry-Level Classification ---

def test_smartrecruiters_internship_and_entry_level_classification():
    provider = SmartRecruitersJobProvider()

    # Internship
    intern_job = provider.normalize_smartrecruiters_job(SAMPLE_SR_INDIA_INTERNSHIP_RAW, "BlueberryLabsPrivateLimited")
    assert intern_job["job_type"] == "internship"
    assert intern_job["opportunity_type"] == "INTERNSHIP"
    assert intern_job["fresher_friendly"] is True
    assert intern_job["experience_min"] == 0
    assert intern_job["experience_max"] == 2
    assert intern_job["student_eligible"] is True

    # Entry level engineering
    raw_entry = dict(SAMPLE_SR_INDIA_ENGINEER_RAW)
    raw_entry["experienceLevel"] = {"id": "entry_level", "label": "Entry Level"}
    entry_job = provider.normalize_smartrecruiters_job(raw_entry, "BoschGroup")
    assert entry_job["fresher_friendly"] is True
    assert entry_job["experience_min"] == 0
    assert entry_job["experience_max"] == 1


# --- 13. Undisclosed Experience Remains Undisclosed ---

def test_smartrecruiters_undisclosed_experience_not_fabricated():
    provider = SmartRecruitersJobProvider()
    raw_undisclosed = dict(SAMPLE_SR_INDIA_ENGINEER_RAW)
    raw_undisclosed["experienceLevel"] = None
    job = provider.normalize_smartrecruiters_job(raw_undisclosed, "BoschGroup")
    assert job["experience_min"] is None
    assert job["experience_max"] is None
    assert job["fresher_friendly"] is False  # Undisclosed must NOT be assumed fresher!


# --- 14. Salary / Stipend Non-Fabrication ---

def test_smartrecruiters_salary_non_fabrication():
    provider = SmartRecruitersJobProvider()
    job = provider.normalize_smartrecruiters_job(SAMPLE_SR_INDIA_ENGINEER_RAW, "BoschGroup")
    assert job["salary_disclosed"] is False
    assert job["salary_min"] is None
    assert job["salary_max"] is None
    assert job["stipend_min"] is None


# --- 15. releasedDate Preservation ---

def test_smartrecruiters_released_date_preservation():
    provider = SmartRecruitersJobProvider()
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    job = provider.normalize_smartrecruiters_job(SAMPLE_SR_INDIA_ENGINEER_RAW, "BoschGroup", now=now)
    assert job["posted_at"] == "2026-09-04T04:50:40.198000+00:00"
    assert job["posted_days_ago"] == 0


# --- 16. Inventory Reconciliation (Disappearance -> CLOSED) ---

@pytest.mark.asyncio
async def test_smartrecruiters_inventory_reconciliation():
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_sr_reconciliation"]
    provider = SmartRecruitersJobProvider()

    # Sync 1: Two jobs present
    with patch.object(provider, "fetch_company_openings", return_value=[SAMPLE_SR_INDIA_ENGINEER_RAW, SAMPLE_SR_INDIA_INTERNSHIP_RAW]):
        stats1 = await provider.sync_company_openings(db, "BoschGroup")
        assert stats1["fetched"] == 2
        assert stats1["verified_active"] == 2
        assert stats1["closed"] == 0

    cursor1 = db[Collections.JOBS].find({"source": "smartrecruiters", "verification_status": "VERIFIED_ACTIVE"})
    active1 = await cursor1.to_list(10)
    assert len(active1) == 2

    # Sync 2: Internship disappears (closed by employer)
    with patch.object(provider, "fetch_company_openings", return_value=[SAMPLE_SR_INDIA_ENGINEER_RAW]):
        stats2 = await provider.sync_company_openings(db, "BoschGroup")
        assert stats2["fetched"] == 1
        assert stats2["verified_active"] == 1
        assert stats2["closed"] == 1

    cursor2_active = db[Collections.JOBS].find({"source": "smartrecruiters", "verification_status": "VERIFIED_ACTIVE"})
    active2 = await cursor2_active.to_list(10)
    assert len(active2) == 1

    cursor2_closed = db[Collections.JOBS].find({"source": "smartrecruiters", "verification_status": "CLOSED"})
    closed2 = await cursor2_closed.to_list(10)
    assert len(closed2) == 1
    assert closed2[0]["id"] == "smartrecruiters_boschgroup_744000147400001"


# --- 17. Network Failure Preserves Active State (Non-Destructive) ---

@pytest.mark.asyncio
async def test_smartrecruiters_network_failure_preserves_active():
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_sr_net_failure"]
    provider = SmartRecruitersJobProvider()

    # Step 1: Initial successful sync
    with patch.object(provider, "fetch_company_openings", return_value=[SAMPLE_SR_INDIA_ENGINEER_RAW]):
        await provider.sync_company_openings(db, "BoschGroup")

    # Step 2: Network failure during sync
    with patch.object(provider, "fetch_company_openings", side_effect=SmartRecruitersNetworkError("Connection reset")):
        stats = await provider.sync_company_openings(db, "BoschGroup")
        assert stats["network_error"] is True

    # Active jobs must be preserved
    cursor = db[Collections.JOBS].find({"source": "smartrecruiters", "verification_status": "VERIFIED_ACTIVE"})
    active_jobs = await cursor.to_list(10)
    assert len(active_jobs) == 1
    assert active_jobs[0]["id"] == "smartrecruiters_boschgroup_744000147412989"


# --- 18. Canonical Source ID ---

def test_smartrecruiters_canonical_source_id():
    provider = SmartRecruitersJobProvider()
    job = provider.normalize_smartrecruiters_job(SAMPLE_SR_INDIA_ENGINEER_RAW, "BoschGroup")
    assert job["id"] == "smartrecruiters_boschgroup_744000147412989"
    assert job["source"] == "smartrecruiters"
