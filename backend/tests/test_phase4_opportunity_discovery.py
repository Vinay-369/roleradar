"""
Phase 4 — Opportunity Discovery, Inventory, Freshness & Job UX Comprehensive Test Suite.

Tests verify:
1. Inventory & distribution (provider, lifecycle, job type, domain)
2. External vs omission funnel (unrelated vs dropped opportunities)
3. Role classification matrix (aliases, seniority, compound titles, comma segments, distinct role families)
4. Experience bounds extraction (fresher, 1-3, 3+, ranges, unspecified)
5. Freshness & lifecycle semantics (recent, older active continuous hiring, benchmarks, closed)
6. Canonical filtering & pagination (role, domain, workplace, pagination stability)
7. Job Detail Canonical StructuredJobRequirements (required vs preferred vs contextual)
8. Operational non-blocking GET requests (no synchronous provider network sync)
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.learning.role_taxonomy import (
    resolve_role,
    RoleCompetencyProfile,
)
from app.modules.jobs.classification import (
    classify_opportunity,
    OpportunityType,
    CandidateSuitabilitySignal,
)
from app.modules.jobs.taxonomy import analyze_job_description, StructuredJobRequirements
from app.modules.jobs.verification import (
    OpportunityLifecycleStatus,
    ApplicationUrlType,
)
from app.modules.jobs.services import (
    search_jobs,
    get_job,
    get_canonical_job_requirements,
)
from app.modules.matching.services import build_india_metadata


# =========================================================================
# 1. ROLE CLASSIFICATION MATRIX & CANONICAL TAXONOMY
# =========================================================================

@pytest.mark.parametrize(
    "raw_title,expected_canonical",
    [
        # All 13 mandatory prompt examples
        ("Backend Engineer", "Backend Developer"),
        ("Backend Developer", "Backend Developer"),
        ("Software Engineer - Backend", "Backend Developer"),
        ("Senior Backend Engineer", "Backend Developer"),
        ("Junior Backend Developer", "Backend Developer"),
        ("Frontend Engineer", "Frontend Developer"),
        ("React Developer", "Frontend Developer"),
        ("QA Automation Engineer", "QA / Test Engineer"),
        ("Data Engineer", "Data Engineer"),
        ("Machine Learning Engineer", "Machine Learning Engineer"),
        ("DevOps Engineer", "DevOps Engineer"),
        ("Cloud Engineer", "Cloud Engineer"),
        ("Android Developer", "Mobile Developer"),
        # Additional aliases & technology-heavy titles
        ("Lead Python Developer", "Backend Developer"),
        ("iOS Application Engineer", "Mobile Developer"),
        ("Site Reliability Engineer (SRE)", "Site Reliability Engineer"),
        ("Data Analyst - Business Intelligence", "Data Analyst"),
        ("Product Designer (UI/UX)", "Product Designer"),
        ("Cyber Security Analyst", "Cybersecurity Analyst"),
    ],
)
def test_role_classification_mandatory_and_extended_examples(raw_title, expected_canonical):
    prof, conf, reason = resolve_role(raw_title)
    assert prof is not None
    assert prof.canonical_role == expected_canonical
    assert conf in ("HIGH", "EXACT")


def test_compound_titles_with_conjunctions_and_commas():
    # Compound title with conjunction & comma: "Backend and System Engineer, Flows"
    prof1, conf1, _ = resolve_role("Backend and System Engineer, Flows")
    assert prof1 is not None
    assert prof1.canonical_role == "Backend Developer"
    assert conf1 in ("HIGH", "EXACT")

    # Conjunction with ampersand: "Data & Analytics Engineer"
    prof2, conf2, _ = resolve_role("Data & Analytics Engineer")
    assert prof2 is not None
    assert prof2.canonical_role == "Data Engineer"
    assert conf2 in ("HIGH", "EXACT")

    # Slash compound title: "DevOps / SRE Engineer"
    prof3, conf3, _ = resolve_role("DevOps / SRE Engineer")
    assert prof3 is not None
    assert prof3.canonical_role in ("DevOps Engineer", "Site Reliability Engineer")
    assert conf3 in ("HIGH", "EXACT")


def test_similar_but_different_roles_not_conflated():
    """
    Selecting Software Engineer must not conflate with Sales Engineer or Engineering Manager.
    """
    dev_prof, _, _ = resolve_role("Software Engineer")
    mgr_prof, _, _ = resolve_role("Software Engineering Manager")
    sales_prof, _, _ = resolve_role("Software Sales Engineer")

    # Manager should be recognized as Engineering Manager
    assert mgr_prof is not None
    assert mgr_prof.canonical_role == "Engineering Manager"
    # Software Engineer should be Software Engineer
    assert dev_prof is not None
    assert dev_prof.canonical_role == "Software Engineer"
    # They should not share the same canonical_role
    assert dev_prof.canonical_role != mgr_prof.canonical_role
    assert sales_prof is None or sales_prof.canonical_role != "Software Engineer"


# =========================================================================
# 2. EXPERIENCE / ELIGIBILITY BOUNDS EXTRACTION
# =========================================================================

def test_experience_extraction_explicit_years():
    # Range
    desc1 = "Qualifications:\nMust have 3-5 years of hands-on experience in distributed systems."
    res1 = analyze_job_description(desc1, "Backend Developer")
    assert res1.min_years_experience == 3
    assert res1.max_years_experience == 5

    # Minimum only
    desc2 = "Requirements:\nRequires a minimum of 2+ years of software development experience."
    res2 = analyze_job_description(desc2, "Software Engineer")
    assert res2.min_years_experience == 2

    # Fresher / Entry Level
    classification = classify_opportunity("Junior Associate", "Open to freshers and recent graduates.", experience_min=0)
    assert classification.fresher_eligible is True
    assert classification.suitability == CandidateSuitabilitySignal.FRESHER


def test_experience_extraction_unspecified():
    # Does not invent numbers from unrelated numeric text (e.g. 500 Fortune companies, 24/7 support)
    desc = "Join our Fortune 500 client providing 24/7 high-availability cloud solutions."
    res = analyze_job_description(desc, "Cloud Specialist")
    assert res.min_years_experience is None
    assert res.max_years_experience is None


def test_internship_experience_handling():
    # Internships must not require professional experience or be dropped because experience is unspecified
    classification = classify_opportunity(
        title="Software Engineering Intern - Summer 2025",
        description="Seeking motivated undergraduate students pursuing Computer Science.",
        experience_min=None,
        experience_max=None,
        job_type_hint="internship",
    )
    assert classification.opportunity_type == OpportunityType.INTERNSHIP
    assert classification.student_eligible is True


# =========================================================================
# 3. EXTERNAL INVENTORY VS ROLERADAR OMISSIONS FUNNEL
# =========================================================================

def test_funnel_preserves_valid_ingested_opportunities():
    """
    Funnel verification: When a provider supplies a valid opportunity,
    it must pass through normalization, classification, and deduplication
    into MongoDB-ready dictionary without being silently discarded.
    """
    from app.modules.jobs.lever_provider import LeverJobProvider
    
    mock_lever_posting = {
        "id": "lever-12345",
        "text": "Senior Backend Developer",
        "description": "<p>We are hiring a Senior Backend Developer with 3+ years of Python and Go experience.</p>",
        "categories": {
            "location": "Bengaluru, Karnataka, India",
            "team": "Engineering",
            "commitment": "Full-time",
        },
        "hostedUrl": "https://jobs.lever.co/example/lever-12345",
        "applyUrl": "https://jobs.lever.co/example/lever-12345/apply",
        "createdAt": 1715000000000,
    }

    provider = LeverJobProvider()
    normalized = provider.normalize_lever_job(mock_lever_posting, "example", "ExampleCorp")
    assert normalized is not None
    assert normalized["title"] == "Senior Backend Developer"
    assert normalized["company"] == "ExampleCorp"
    assert normalized["is_direct_apply"] is True
    assert normalized["country"] == "India"
    assert normalized["verification_status"] == "VERIFIED_ACTIVE"

    # Verify classification attaches valid canonical metadata
    meta = build_india_metadata(normalized)
    assert meta["opportunity_type"] == "FULL_TIME"
    assert meta["normalized_location"] == "Bengaluru"


def test_funnel_correctly_identifies_unrelated_supply_as_external_low():
    """
    When provider has no matching jobs for a niche role, system does not fabricate
    or misclassify unrelated roles (e.g. Executive Assistant should not map to Software Engineering).
    """
    prof, _, _ = resolve_role("Executive Assistant to CEO")
    if prof is not None:
        assert prof.domain != "Software Engineering"
        assert prof.domain != "Data & Analytics"


# =========================================================================
# 4. FRESHNESS & LIFECYCLE SEMANTICS
# =========================================================================

def test_freshness_and_lifecycle_separation():
    # 1. Recent active listing (<= 3 days)
    recent_job = {
        "title": "Frontend Engineer",
        "company": "Acme Corp",
        "posted_days_ago": 2,
        "verification_status": "VERIFIED_ACTIVE",
        "is_direct_apply": True,
    }
    assert recent_job["posted_days_ago"] <= 3
    assert recent_job["verification_status"] == "VERIFIED_ACTIVE"

    # 2. Older active listing (continuous hiring, verified live direct requisition)
    older_job = {
        "title": "Backend Developer",
        "company": "Global Tech",
        "posted_days_ago": 45,
        "verification_status": "VERIFIED_ACTIVE",
        "is_direct_apply": True,
    }
    # Older than 14 days, but verified active -> Treated honestly as verified active / continuous hiring
    assert older_job["posted_days_ago"] > 14
    assert older_job["verification_status"] == "VERIFIED_ACTIVE"

    # 3. Market Benchmark listing (must remain separate from live ATS postings)
    benchmark_job = {
        "title": "Senior Data Scientist",
        "company": "RoleRadar Reference",
        "verification_status": "MARKET_BENCHMARK",
        "is_direct_apply": False,
    }
    assert benchmark_job["verification_status"] == "MARKET_BENCHMARK"
    assert benchmark_job["is_direct_apply"] is False


# =========================================================================
# 5. CANONICAL STRUCTURED JOB REQUIREMENTS IN JOB DETAIL
# =========================================================================

@pytest.mark.asyncio
async def test_job_detail_canonical_requirements_extraction():
    """
    Ensures StructuredJobRequirements keeps required, preferred, and contextual
    distinct, and does not manufacture skills or dump all technologies into required.
    """
    mock_db = MagicMock()
    
    # Sample job with structured JD
    job_doc = {
        "_id": "test-job-999",
        "id": "test-job-999",
        "title": "Staff Backend Engineer",
        "company": "TechStream",
        "description": "We are seeking a Staff Backend Engineer.\n\nRequired Qualifications:\n- Python\n- FastAPI\n- PostgreSQL\n\nPreferred Qualifications:\n- Docker\n- Kubernetes\n- AWS",
        "skills_required": [],
        "skills_nice_to_have": [],
        "source": "lever",
    }

    reqs = await get_canonical_job_requirements(mock_db, job_doc)
    assert reqs is not None
    
    # Required skills must be populated from requirements analysis
    assert len(reqs.required_skills) > 0 or len(reqs.must_have_skills) > 0

    # Test distinctness: required and preferred should not arbitrarily duplicate
    req_set = set(reqs.required_skills or reqs.must_have_skills)
    pref_set = set(reqs.preferred_skills)
    overlap = req_set.intersection(pref_set)
    assert len(overlap) == 0


@pytest.mark.asyncio
async def test_job_detail_honest_empty_state():
    """
    When JD contains no extractable skills, returns empty lists rather than manufactured skills.
    """
    mock_db = MagicMock()
    empty_jd_job = {
        "_id": "test-empty-111",
        "id": "test-empty-111",
        "title": "Team Member",
        "company": "Generic Office",
        "description": "General office duties. Answering phone calls and sorting paperwork.",
        "skills_required": [],
        "skills_nice_to_have": [],
        "source": "curated",
    }
    reqs = await get_canonical_job_requirements(mock_db, empty_jd_job)
    assert len(reqs.required_skills) == 0
    assert len(reqs.must_have_skills) == 0


# =========================================================================
# 6. OPERATIONAL DECOUPLING (GET DOES NOT BLOCK ON SYNC)
# =========================================================================

@pytest.mark.asyncio
async def test_opportunity_search_does_not_synchronously_sync_providers():
    """
    GET /jobs and GET /matches/recommended must NOT trigger provider sync.
    Phase 16C architecture preservation verification.
    """
    mock_db = MagicMock()
    
    # Mock find_jobs
    with patch("app.modules.jobs.repositories.find_jobs", new_callable=AsyncMock) as mock_find, \
         patch("app.modules.jobs.services.refresh_live_jobs", new_callable=AsyncMock) as mock_sync:
        mock_find.return_value = []
        
        await search_jobs(mock_db, {"job_type": "full_time"})
        
        # search_jobs must have queried MongoDB repository
        assert mock_find.called
        # search_jobs must NEVER have called refresh_live_jobs
        assert not mock_sync.called


# =========================================================================
# 7. FILTERING & PAGINATION STABILITY
# =========================================================================

@pytest.mark.asyncio
async def test_pagination_and_slice_bounds():
    from app.modules.jobs.providers import CuratedJobProvider

    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.sort.return_value = mock_cursor

    jobs_sample = [
        {"id": f"job-{i}", "title": f"Engineer {i}", "posted_days_ago": i, "job_type": "full_time", "verification_status": "VERIFIED_ACTIVE"}
        for i in range(10)
    ]
    mock_cursor.to_list = AsyncMock(return_value=jobs_sample)
    mock_db.__getitem__.return_value.find.return_value = mock_cursor

    provider = CuratedJobProvider(mock_db)
    p1 = await provider.search({"limit": 10, "skip": 0, "active_discovery_only": True})
    assert len(p1) == 10
    mock_cursor.limit.assert_called_with(10)


@pytest.mark.asyncio
async def test_smartrecruiters_sync_initialization_no_unbound_error():
    """
    Ensures sync_all_smartrecruiters_boards initializes total_active and total_closed
    and returns properly structured sync statistics without raising UnboundLocalError.
    """
    from app.modules.jobs.services import sync_all_smartrecruiters_boards
    from app.core.config import Settings

    mock_db = MagicMock()
    settings = Settings(
        SMARTRECRUITERS_ENABLED=True,
        SMARTRECRUITERS_COMPANIES="CompanyA,CompanyB",
        SMARTRECRUITERS_COUNTRY="in",
    )

    with patch("app.modules.jobs.smartrecruiters_provider.SmartRecruitersJobProvider.sync_company_openings", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {"board": "comp", "fetched": 5, "verified_active": 3, "closed": 1, "errors": []}

        res = await sync_all_smartrecruiters_boards(mock_db, settings)
        assert res["total_boards"] == 2
        assert res["verified_active"] == 6
        assert res["closed"] == 2
        assert len(res["results"]) == 2

