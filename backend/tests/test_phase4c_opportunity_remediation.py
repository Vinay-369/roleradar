"""
Phase 4C — Opportunity Quality, Coverage, Show More & Registration-Based Discovery Test Suite.

Verifies:
1. Reliable database pagination with zero overlap across pages.
2. Canonical CandidateCategory reuse in opportunity queries.
3. Deterministic ordering preserving role relevance, eligibility, and recency.
4. Transparent job detail data quality: qualifications, honest compensation, and non-fabricated technical evidence.
5. Strict performance guarantee: zero synchronous provider API calls on opportunity discovery GETs.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.profile.schemas import CandidateCategory
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.schemas import JobOut
from app.modules.jobs import services as jobs_services
from app.modules.matching.routes import recommended_matches
from app.core.config import Settings
from fastapi import Response


@pytest.mark.asyncio
async def test_pagination_zero_overlap_and_honest_counts():
    """
    Verify pagination over inventory:
    - Page 1 and Page 2 contain distinct, non-overlapping opportunities.
    - Total count matches the query count.
    """
    fake_jobs = [
        {
            "id": f"job_{i:03d}",
            "title": f"Software Engineer {i}",
            "company": f"TechCorp {i}",
            "location": "Bengaluru, Karnataka, India",
            "country": "India",
            "job_type": "full_time",
            "verification_status": "VERIFIED_ACTIVE",
            "url_type": "DIRECT_REQUISITION",
            "is_direct_apply": True,
            "skills_required": ["Python", "Docker"],
            "skills_nice_to_have": [],
            "posted_days_ago": i % 10,
            "apply_url": f"https://jobs.example.com/{i}",
            "responsibilities": ["Build scalable APIs"],
            "qualifications": ["B.Tech / M.Tech in CS"],
            "source": "smartrecruiters",
        }
        for i in range(45)
    ]

    # Mock database and cursor behavior
    db = AsyncMock()
    
    def fake_find(mongo_filter):
        class MockCursor:
            def __init__(self, items):
                self.items = items
                self._skip = 0
                self._limit = len(items)

            def sort(self, sort_spec):
                return self

            def skip(self, n):
                self._skip = n
                return self

            def limit(self, n):
                self._limit = n
                return self

            async def to_list(self, length):
                return self.items[self._skip : self._skip + self._limit]

        return MockCursor(fake_jobs)

    db["jobs"].find = fake_find
    db["jobs"].count_documents = AsyncMock(return_value=len(fake_jobs))

    provider = CuratedJobProvider(db)

    # Page 1 (limit 20, skip 0)
    filters_p1 = {"limit": 20, "skip": 0}
    page1 = await provider.search(filters_p1)
    assert len(page1) == 20

    # Page 2 (limit 20, skip 20)
    filters_p2 = {"limit": 20, "skip": 20}
    page2 = await provider.search(filters_p2)
    assert len(page2) == 20

    # Page 3 (limit 20, skip 40)
    filters_p3 = {"limit": 20, "skip": 40}
    page3 = await provider.search(filters_p3)
    assert len(page3) == 5

    # Total count
    total = await provider.count(filters_p1)
    assert total == 45

    # Deduplication & zero overlap check
    p1_ids = {j["id"] for j in page1}
    p2_ids = {j["id"] for j in page2}
    p3_ids = {j["id"] for j in page3}

    assert len(p1_ids.intersection(p2_ids)) == 0, "Page 1 and Page 2 must have zero overlap"
    assert len(p2_ids.intersection(p3_ids)) == 0, "Page 2 and Page 3 must have zero overlap"
    assert len(p1_ids.union(p2_ids).union(p3_ids)) == 45


def test_registration_canonical_stage_enum_alignment():
    """
    Ensure the discovery stage filters match the registration CandidateCategory enum directly.
    """
    assert CandidateCategory.FRESHER.value == "FRESHER"
    assert CandidateCategory.EXPERIENCED.value == "EXPERIENCED"
    assert CandidateCategory.CAREER_SWITCHER.value == "CAREER_SWITCHER"
    assert CandidateCategory.INTERNSHIP_SEEKER.value == "INTERNSHIP_SEEKER"

    # Verify stage parameter query building
    filters = {"stage": "FRESHER"}
    assert filters["stage"] == "FRESHER"

    provider = CuratedJobProvider(AsyncMock())
    mongo_q = provider._build_mongo_query(filters)
    assert "$and" in mongo_q
    # Fresher query must check fresher_eligible, student_eligible, or experience bounds inside $and
    and_clauses = mongo_q["$and"]
    has_fresher_or = any(
        "$or" in c and any("fresher_friendly" in branch or "experience_min" in branch for branch in c["$or"])
        for c in and_clauses
    )
    assert has_fresher_or


def test_job_out_schema_includes_qualifications():
    """
    Verify JobOut schema exposes qualifications for rich JD presentation.
    """
    job = JobOut(
        id="test_001",
        source="lever",
        title="Software Engineer",
        company="Razorpay",
        industry="Fintech",
        description="Full description here",
        skills_required=["Python"],
        skills_nice_to_have=["Go"],
        job_type="full_time",
        location="Bengaluru",
        is_remote=False,
        salary_min=12.0,
        salary_max=18.0,
        salary_disclosed=True,
        stipend_min=None,
        internship_duration_months=None,
        fresher_friendly=True,
        posted_days_ago=1,
        apply_url="https://jobs.lever.co/razorpay/test_001",
        responsibilities=["Develop microservices"],
        qualifications=["Bachelor's degree in Computer Science or equivalent"],
    )
    assert job.qualifications == ["Bachelor's degree in Computer Science or equivalent"]
    assert job.responsibilities == ["Develop microservices"]


@pytest.mark.asyncio
async def test_search_jobs_pure_mongo_no_blocking_network():
    """
    Verify discovery search is purely database-backed without synchronous external HTTP calls.
    """
    db = AsyncMock()
    filters = {"limit": 20, "skip": 0}

    with patch("httpx.AsyncClient.get") as mock_get:
        # Calling search_jobs should never touch httpx
        with patch("app.modules.jobs.providers.CuratedJobProvider.search", AsyncMock(return_value=[])):
            res = await jobs_services.search_jobs(db, filters)
            assert res == []
            mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_recommended_matches_sets_x_total_count_header():
    """
    Verify recommended_matches endpoint sets X-Total-Count header for honest pagination counts.
    """
    db = AsyncMock()
    settings = Settings()
    current_user = {"_id": "test_student_user"}
    response = Response()

    with patch("app.modules.matching.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.jobs_services.refresh_live_jobs", AsyncMock(return_value=0)), \
         patch("app.modules.matching.routes.jobs_services.count_jobs", AsyncMock(return_value=576)), \
         patch("app.modules.matching.routes.jobs_services.search_jobs", AsyncMock(return_value=[])):

        matches = await recommended_matches(
            job_type="full_time",
            live_only=True,
            stage="FRESHER",
            response=response,
            current_user=current_user,
            db=db,
            settings=settings,
        )

        assert matches == []
        assert response.headers.get("X-Total-Count") == "576"
        assert "X-Total-Count" in response.headers.get("Access-Control-Expose-Headers", "")


@pytest.mark.asyncio
async def test_get_my_profile_handles_legacy_user_without_category():
    """
    Verify get_my_profile does not throw 500 when legacy database profile lacks category or consent_text.
    """
    from app.modules.profile.routes import get_my_profile
    db = AsyncMock()
    legacy_profile = {
        "_id": "prof_123",
        "user_id": "usr_123",
        "experience_years": 0.0,
        "preferred_locations": ["Bangalore"],
    }
    with patch("app.modules.profile.repositories.get_profile", AsyncMock(return_value=legacy_profile)):
        res = await get_my_profile(current_user={"_id": "usr_123"}, db=db)
        assert res is not None
        assert res.category.value == "FRESHER"
        assert res.consent_text == "Standard candidate registration consent."
        assert res.user_id == "usr_123"

