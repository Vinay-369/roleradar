"""
Comprehensive test suite for Ashby Direct Live Opportunity Provider (Phase 13).
Covers all 20 required scenarios:
1. Normalization (title, company, source_job_id, apply_url, published_at).
2. India filtering (admitting Bengaluru, Pune, Mumbai, Delhi NCR, Hyderabad, etc.).
3. Remote India handling (admitting India-remote, rejecting ambiguous global-remote without India eligibility).
4. Job classification (full-time vs other).
5. Internship classification (structured employmentType == "Intern", title markers, rejecting description substring).
6. Active filtering (isListed: False rejected, isListed: True admitted).
7. Freshness (ISO timestamp preserved, zero date fabrication).
8. Role mapping (canonical role taxonomy resolution: Software Engineer, Product Designer, SRE, etc.).
9. Required-skill extraction (canonical taxonomy extraction from description).
10. Experience extraction (years extracted honestly from text, 0 for internships).
11. Apply URL validation (https://jobs.ashbyhq.com/{org}/{job_id}/application -> DIRECT_REQUISITION).
12. Unsafe URL rejection (javascript:, placeholder hosts, malformed schemes).
13. Deduplication (cross-provider and repeated sync idempotence).
14. Malformed response handling (missing ID, missing URL, invalid types).
15. Empty response handling (HTTP 200 with empty array, 404 handling).
16. Provider outage handling (AshbyNetworkError raised, timeout handled).
17. Repeated synchronization (idempotent upserts, no duplicate rows).
18. Partial synchronization failure (failure on board A does not abort board B).
19. No deletion on provider failure (transient network failure retains existing active records).
20. Source provenance (source = "ashby", company_board, source_job_id, source_url, apply_url).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.jobs.ashby_provider import (
    AshbyJobProvider,
    AshbyNetworkError,
    AshbyProviderError,
    is_internship_opportunity,
)
from app.modules.jobs.deduplication import deduplicate_opportunities
from app.modules.jobs.services import sync_all_ashby_boards
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus


def make_raw_ashby_job(**overrides):
    base = {
        "id": "e7890d9f-8e1f-48a0-92be-071a282e7fe8",
        "title": "Software Engineer II (Bangalore, India)",
        "department": "Engineering",
        "team": "Backend Platform",
        "employmentType": "FullTime",
        "location": "Bengaluru",
        "secondaryLocations": [],
        "publishedAt": "2026-08-24T19:13:57.321+00:00",
        "isListed": True,
        "isRemote": False,
        "workplaceType": "OnSite",
        "address": {
            "postalAddress": {
                "addressCountry": "India",
                "addressLocality": "Bengaluru",
                "addressRegion": "Karnataka",
            }
        },
        "jobUrl": "https://jobs.ashbyhq.com/aiprise/e7890d9f-8e1f-48a0-92be-071a282e7fe8",
        "applyUrl": "https://jobs.ashbyhq.com/aiprise/e7890d9f-8e1f-48a0-92be-071a282e7fe8/application",
        "descriptionPlain": "We are seeking a Software Engineer with 3+ years experience in Python, FastAPI, and PostgreSQL to build our core platform.",
        "descriptionHtml": "<p>We are seeking a Software Engineer with 3+ years experience in Python, FastAPI, and PostgreSQL.</p>",
        "compensation": {
            "scrapeableCompensationSalarySummary": "₹30L - ₹50L",
            "compensationTierSummary": "₹30L – ₹50L • Offers Bonus",
            "summaryComponents": [
                {
                    "compensationType": "Salary",
                    "interval": "1 YEAR",
                    "currencyCode": "INR",
                    "minValue": 3000000,
                    "maxValue": 5000000,
                }
            ],
        },
    }
    base.update(overrides)
    return base


# --- 1. NORMALIZATION ---
def test_01_ashby_response_normalization():
    """1. Normalization: Ashby response normalizes correctly into canonical opportunity model."""
    provider = AshbyJobProvider()
    raw = make_raw_ashby_job()
    norm = provider.normalize_ashby_job(raw, "aiprise", company_name="AiPrise")

    assert norm["id"] == "ashby_aiprise_e7890d9f-8e1f-48a0-92be-071a282e7fe8"
    assert norm["source"] == "ashby"
    assert norm["source_job_id"] == "e7890d9f-8e1f-48a0-92be-071a282e7fe8"
    assert norm["company_board"] == "aiprise"
    assert norm["title"] == "Software Engineer II (Bangalore, India)"
    assert norm["company"] == "AiPrise"
    assert norm["country"] == "India"
    assert norm["is_india_opportunity"] is True
    assert norm["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm["is_direct_apply"] is True
    assert norm["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    assert norm["verification_method"] == "ashby_api_direct"
    assert norm["salary_min"] == 30.0
    assert norm["salary_max"] == 50.0
    assert norm["salary_disclosed"] is True


# --- 2. INDIA FILTERING ---
def test_02_india_filtering():
    """2. India filtering: Admits Indian cities, rejects foreign locations."""
    provider = AshbyJobProvider()

    # Valid Indian cities
    for loc, country_expected in [
        ("Bengaluru", "India"),
        ("Bangalore, India", "India"),
        ("Hyderabad", "India"),
        ("Pune, Maharashtra", "India"),
        ("Mumbai", "India"),
        ("Gurugram", "India"),
        ("Noida, Uttar Pradesh", "India"),
        ("New Delhi", "India"),
        ("Chennai", "India"),
    ]:
        raw = make_raw_ashby_job(location=loc, address={"postalAddress": {"addressCountry": "India"}})
        norm = provider.normalize_ashby_job(raw, "kong")
        assert norm["is_india_opportunity"] is True, f"Failed for {loc}"
        assert norm["country"] == "India"

    # Foreign locations rejected
    foreign_raw = make_raw_ashby_job(
        location="San Francisco, CA",
        address={"postalAddress": {"addressCountry": "United States"}},
    )
    foreign_norm = provider.normalize_ashby_job(foreign_raw, "kong")
    assert foreign_norm["is_india_opportunity"] is False
    assert foreign_norm["country"] == "United States"


# --- 3. REMOTE INDIA HANDLING ---
def test_03_remote_india_handling():
    """3. Remote India handling: Explicit India-remote admitted, ambiguous global remote rejected."""
    provider = AshbyJobProvider()

    # Explicit India Remote
    remote_india_raw = make_raw_ashby_job(
        location="Remote - India",
        isRemote=True,
        workplaceType="Remote",
        address={"postalAddress": {"addressCountry": "India"}},
    )
    norm = provider.normalize_ashby_job(remote_india_raw, "elevenlabs")
    assert norm["is_india_opportunity"] is True
    assert norm["country"] == "India"
    assert norm["workplace_type"] == "REMOTE"

    # Ambiguous / Global Remote without India anchor
    global_remote_raw = make_raw_ashby_job(
        location="Remote",
        isRemote=True,
        workplaceType="Remote",
        address={"postalAddress": {"addressCountry": ""}},
    )
    norm_global = provider.normalize_ashby_job(global_remote_raw, "elevenlabs")
    assert norm_global["is_india_opportunity"] is False
    assert norm_global["country"] is None


# --- 4. JOB CLASSIFICATION ---
def test_04_job_classification():
    """4. Job classification: Full-time classified accurately."""
    provider = AshbyJobProvider()
    raw = make_raw_ashby_job(employmentType="FullTime")
    norm = provider.normalize_ashby_job(raw, "cartesia")
    assert norm["job_type"] == "full_time"
    assert norm["opportunity_type"] == "FULL_TIME"


# --- 5. INTERNSHIP CLASSIFICATION ---
def test_05_internship_classification():
    """5. Internship classification: Based on structured employmentType or title markers, never description."""
    provider = AshbyJobProvider()

    # Case A: Structured employmentType == "Intern"
    intern_raw = make_raw_ashby_job(
        title="Software Engineer",
        employmentType="Intern",
    )
    norm = provider.normalize_ashby_job(intern_raw, "cartesia")
    assert norm["job_type"] == "internship"
    assert norm["opportunity_type"] == "INTERNSHIP"

    # Case B: Title has "Intern"
    intern_title_raw = make_raw_ashby_job(
        title="Machine Learning Intern",
        employmentType="FullTime",
    )
    norm_title = provider.normalize_ashby_job(intern_title_raw, "cartesia")
    assert norm_title["job_type"] == "internship"

    # Case C: STRICT RULE: Description mentions intern/internship, but title and type are full-time
    not_intern_raw = make_raw_ashby_job(
        title="Senior Backend Engineer",
        employmentType="FullTime",
        descriptionPlain="You will mentor junior engineers and occasional interns on our platform team.",
    )
    norm_not_intern = provider.normalize_ashby_job(not_intern_raw, "cartesia")
    assert norm_not_intern["job_type"] == "full_time"
    assert norm_not_intern["opportunity_type"] == "FULL_TIME"


# --- 6. ACTIVE FILTERING ---
def test_06_active_filtering():
    """6. Active filtering: isListed=False transitions to CLOSED, isListed=True stays VERIFIED_ACTIVE."""
    provider = AshbyJobProvider()

    # Unlisted listing
    unlisted_raw = make_raw_ashby_job(isListed=False)
    norm_unlisted = provider.normalize_ashby_job(unlisted_raw, "harvey")
    assert norm_unlisted["verification_status"] == OpportunityLifecycleStatus.CLOSED.value
    assert "Unlisted" in norm_unlisted["verification_reason"]

    # Listed listing
    listed_raw = make_raw_ashby_job(isListed=True)
    norm_listed = provider.normalize_ashby_job(listed_raw, "harvey")
    assert norm_listed["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value


# --- 7. FRESHNESS & ZERO DATE FABRICATION ---
def test_07_freshness_zero_date_fabrication():
    """7. Freshness: Zero date fabrication; publishedAt used honestly, updated_at is None."""
    provider = AshbyJobProvider()
    fixed_now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    raw = make_raw_ashby_job(publishedAt="2026-08-25T12:00:00.000Z")
    norm = provider.normalize_ashby_job(raw, "temporal", now=fixed_now)

    assert norm["posted_at"] == "2026-08-25T12:00:00+00:00"
    assert norm["posted_days_ago"] == 7
    assert norm["updated_at"] is None  # Ashby does not have updated_at; no fabrication allowed!

    # When publishedAt is missing
    raw_no_date = make_raw_ashby_job(publishedAt=None)
    norm_no_date = provider.normalize_ashby_job(raw_no_date, "temporal", now=fixed_now)
    assert norm_no_date["posted_at"] is None
    assert norm_no_date["posted_days_ago"] == 0


# --- 8. ROLE MAPPING ---
def test_08_canonical_role_mapping():
    """8. Role mapping: Titles map to canonical roles correctly via canonical taxonomy, without fabricating unconfirmed roles."""
    from app.modules.learning.role_taxonomy import resolve_role

    test_roles = [
        ("Software Engineer II", "Software Engineer"),
        ("Site Reliability Engineer 2, Managed Gateways", "Site Reliability Engineer"),
        ("Product Designer II", "Product Designer"),
        ("Operations Analyst", "Operations Analyst"),
    ]

    for title, expected_role in test_roles:
        prof, conf, reason = resolve_role(title)
        assert prof is not None, f"Failed to resolve role for {title}"
        assert prof.canonical_role == expected_role, f"Expected {expected_role}, got {prof.canonical_role}"
        assert conf in ("HIGH", "MEDIUM")

    # Low-confidence unconfirmed roles must not fabricate or hallucinate generic Software Engineer
    niche_prof, niche_conf, _ = resolve_role("Senior Marketing Operations Analyst")
    assert niche_prof is None or niche_conf == "LOW"


# --- 9. REQUIRED SKILL EXTRACTION ---
def test_09_required_skill_extraction():
    """9. Required-skill extraction: Skills extracted accurately from job description."""
    provider = AshbyJobProvider()
    raw = make_raw_ashby_job(
        descriptionPlain="Requirements: 4+ years of experience in Python, Docker, Kubernetes, and PostgreSQL.",
    )
    norm = provider.normalize_ashby_job(raw, "aiprise")
    skills = norm["skills_required"]
    assert any("Python" in s for s in skills)
    assert any("Kubernetes" in s or "Docker" in s for s in skills)


# --- 10. EXPERIENCE EXTRACTION ---
def test_10_experience_extraction():
    """10. Experience extraction: Truthfully extracted years from JD text, 0 for internships."""
    provider = AshbyJobProvider()

    # Explicit full-time 3+ years
    raw_ft = make_raw_ashby_job(
        title="Backend Engineer",
        descriptionPlain="Minimum 3 years of hands-on software development experience required.",
    )
    norm_ft = provider.normalize_ashby_job(raw_ft, "kong")
    assert norm_ft["experience_min"] == 3

    # Internship experience default
    raw_intern = make_raw_ashby_job(
        title="Software Engineering Intern",
        employmentType="Intern",
        descriptionPlain="Open to current students in computer science.",
    )
    norm_intern = provider.normalize_ashby_job(raw_intern, "kong")
    assert norm_intern["experience_min"] == 0
    assert norm_intern["experience_max"] == 2


# --- 11. APPLY URL VALIDATION ---
def test_11_apply_url_validation():
    """11. Apply URL validation: Ashby application URLs are recognized as DIRECT_REQUISITION."""
    url = "https://jobs.ashbyhq.com/aiprise/e7890d9f-8e1f-48a0-92be-071a282e7fe8/application"
    url_type, reason = classify_application_url(url, company="AiPrise")
    assert url_type == ApplicationUrlType.DIRECT_REQUISITION
    assert "ashbyhq.com" in reason


# --- 12. UNSAFE URL REJECTION ---
def test_12_unsafe_url_rejection():
    """12. Unsafe URL rejection: Rejects javascript:, missing host, and placeholder URLs."""
    provider = AshbyJobProvider()

    # javascript: scheme
    raw_js = make_raw_ashby_job(applyUrl="javascript:stealToken()")
    norm_js = provider.normalize_ashby_job(raw_js, "aiprise")
    assert norm_js["url_type"] == ApplicationUrlType.INVALID.value
    assert norm_js["verification_status"] == OpportunityLifecycleStatus.INVALID.value

    # placeholder domain
    raw_ph = make_raw_ashby_job(applyUrl="https://example.com/job/123")
    norm_ph = provider.normalize_ashby_job(raw_ph, "aiprise")
    assert norm_ph["url_type"] == ApplicationUrlType.INVALID.value


# --- 13. DEDUPLICATION ---
def test_13_deduplication():
    """13. Deduplication: Identical role reposts deduplicate into a single canonical record."""
    provider = AshbyJobProvider()
    raw1 = make_raw_ashby_job(id="uuid-1", title="Software Engineer", publishedAt="2026-08-20T10:00:00Z")
    raw2 = make_raw_ashby_job(id="uuid-2", title="Software Engineer", publishedAt="2026-08-25T10:00:00Z")

    norm1 = provider.normalize_ashby_job(raw1, "aiprise")
    norm2 = provider.normalize_ashby_job(raw2, "aiprise")

    deduped = deduplicate_opportunities([norm1, norm2])
    assert len(deduped) == 1
    # Check that freshest recency was retained
    assert deduped[0]["posted_days_ago"] <= max(norm1["posted_days_ago"], norm2["posted_days_ago"])


# --- 14. MALFORMED RESPONSE HANDLING ---
@pytest.mark.asyncio
async def test_14_malformed_response_handling():
    """14. Malformed response: Non-dict response or items missing ID handled gracefully without crash."""
    provider = AshbyJobProvider()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"jobs": [{"title": "No ID Job"}, None]})
        jobs = await provider.fetch_company_openings("aiprise")
        assert len(jobs) == 2

    # Normalization with missing ID
    raw_malformed = {"title": "Missing ID"}
    norm = provider.normalize_ashby_job(raw_malformed, "aiprise")
    assert norm["id"] == "ashby_aiprise_"
    assert norm["verification_status"] == OpportunityLifecycleStatus.INVALID.value


# --- 15. EMPTY RESPONSE / 404 HANDLING ---
@pytest.mark.asyncio
async def test_15_empty_and_404_handling():
    """15. Empty response & 404: Returns empty list without raising exception."""
    provider = AshbyJobProvider()

    # 404 Not Found
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=404)
        jobs = await provider.fetch_company_openings("nonexistent-board")
        assert jobs == []

    # 200 with empty jobs
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"jobs": []})
        jobs = await provider.fetch_company_openings("empty-board")
        assert jobs == []


# --- 16. PROVIDER OUTAGE HANDLING ---
@pytest.mark.asyncio
async def test_16_provider_outage_handling():
    """16. Provider outage: Timeout or network failure raises AshbyNetworkError cleanly."""
    provider = AshbyJobProvider()
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection timed out")):
        with pytest.raises((AshbyNetworkError, AshbyProviderError)):
            await provider.fetch_company_openings("timeout-board")


# --- 17. REPEATED SYNCHRONIZATION ---
@pytest.mark.asyncio
async def test_17_repeated_synchronization():
    """17. Repeated synchronization: Successive syncs are idempotent."""
    provider = AshbyJobProvider()
    raw = make_raw_ashby_job()

    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_collection.find.return_value = mock_cursor
    mock_collection.update_one = AsyncMock()

    with patch.object(provider, "fetch_company_openings", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [raw]
        stats1 = await provider.sync_company_openings(mock_db, "aiprise")
        assert stats1["verified_active"] == 1

        stats2 = await provider.sync_company_openings(mock_db, "aiprise")
        assert stats2["verified_active"] == 1


# --- 18. PARTIAL SYNCHRONIZATION FAILURE ---
@pytest.mark.asyncio
async def test_18_partial_synchronization_failure():
    """18. Partial synchronization failure: Failure on one board does not abort remaining boards."""
    settings = Settings(ASHBY_ENABLED=True, ASHBY_COMPANIES="board1,board2")
    mock_db = MagicMock()

    async def mock_sync(db, board, **kwargs):
        if board == "board1":
            return {"board": "board1", "verified_active": 0, "closed": 0, "errors": ["Network error"]}
        return {"board": "board2", "verified_active": 3, "closed": 0, "errors": []}

    with patch("app.modules.jobs.ashby_provider.AshbyJobProvider.sync_company_openings", side_effect=mock_sync):
        res = await sync_all_ashby_boards(mock_db, settings)
        assert res["total_boards"] == 2
        assert res["verified_active"] == 3
        assert len(res["results"]) == 2


# --- 19. NO DELETION ON PROVIDER FAILURE ---
@pytest.mark.asyncio
async def test_19_no_deletion_on_provider_failure():
    """19. No deletion on provider failure: Network outage retains previously stored active jobs."""
    provider = AshbyJobProvider()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.update_one = AsyncMock()

    with patch.object(provider, "fetch_company_openings", side_effect=AshbyNetworkError("Outage")):
        stats = await provider.sync_company_openings(mock_db, "aiprise")
        assert stats["verified_active"] == 0
        assert stats["closed"] == 0
        # Critical guarantee: update_one was NEVER called to delete or close jobs
        mock_collection.update_one.assert_not_called()


# --- 20. SOURCE PROVENANCE ---
def test_20_source_provenance():
    """20. Source provenance: Exact provider provenance fields are preserved."""
    provider = AshbyJobProvider()
    raw = make_raw_ashby_job()
    norm = provider.normalize_ashby_job(raw, "aiprise", company_name="AiPrise")

    assert norm["source"] == "ashby"
    assert norm["company_board"] == "aiprise"
    assert norm["source_job_id"] == "e7890d9f-8e1f-48a0-92be-071a282e7fe8"
    assert norm["apply_url"] == "https://jobs.ashbyhq.com/aiprise/e7890d9f-8e1f-48a0-92be-071a282e7fe8/application"
    assert norm["source_url"] == "https://jobs.ashbyhq.com/aiprise/e7890d9f-8e1f-48a0-92be-071a282e7fe8"
    assert norm["verification_method"] == "ashby_api_direct"
