"""
Tests for Pre-Resume Opportunity Discovery (Jobs & Internships).
Proves:
1. New authenticated user with no resume can load Jobs.
2. Jobs response contains real available opportunities when provider data exists.
3. New authenticated user with no resume can load Internships.
4. Internships response contains real available opportunities when provider data exists.
5. No resume does NOT trigger a resume-required redirect/block for discovery.
6. Existing user with resume still gets personalized matching.
7. Match score is NOT fabricated when resume evidence is unavailable (overall_score is None, has_match=False).
8. Custom opportunity ownership isolation remains intact.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest

from app.core.config import Settings
from app.modules.matching.routes import recommended_matches
from app.modules.matching.schemas import JobMatchOut


CANONICAL_TEST_JOBS = [
    {
        "id": "job_ft_001",
        "title": "Backend Developer",
        "company": "Accenture",
        "industry": "Consulting",
        "description": "Building backend microservices in Python & FastAPI.",
        "skills_required": ["Python", "FastAPI", "MongoDB"],
        "skills_nice_to_have": ["Docker"],
        "experience_min": 1,
        "experience_max": 4,
        "job_type": "full_time",
        "location": "Bangalore",
        "is_remote": False,
        "salary_min": 8,
        "salary_max": 12,
        "salary_disclosed": True,
        "stipend_min": None,
        "stipend_max": None,
        "posted_days_ago": 2,
        "source": "curated",
        "apply_url": "https://accenture.com/careers/job1",
    },
    {
        "id": "job_ft_002",
        "title": "Frontend Developer",
        "company": "Flipkart",
        "industry": "E-commerce",
        "description": "Building modern web UI in React.",
        "skills_required": ["React", "TypeScript", "Tailwind CSS"],
        "skills_nice_to_have": ["REST APIs"],
        "experience_min": 1,
        "experience_max": 3,
        "job_type": "full_time",
        "location": "Bangalore",
        "is_remote": True,
        "salary_min": 10,
        "salary_max": 15,
        "salary_disclosed": True,
        "stipend_min": None,
        "stipend_max": None,
        "posted_days_ago": 1,
        "source": "live",
        "apply_url": "https://flipkart.careers/job2",
    },
    {
        "id": "intern_001",
        "title": "Data Science Intern",
        "company": "Microsoft",
        "industry": "Technology",
        "description": "Internship researching machine learning algorithms.",
        "skills_required": ["Python", "Machine Learning", "SQL"],
        "skills_nice_to_have": ["PyTorch"],
        "experience_min": 0,
        "experience_max": 1,
        "job_type": "internship",
        "location": "Hyderabad",
        "is_remote": True,
        "salary_min": None,
        "salary_max": None,
        "salary_disclosed": False,
        "stipend_min": 50000,
        "stipend_max": 75000,
        "posted_days_ago": 0,
        "source": "curated",
        "apply_url": "https://careers.microsoft.com/intern1",
    },
    {
        "id": "custom_job_user_b",
        "title": "Stealth Founder Role",
        "company": "Confidential Corp",
        "skills_required": ["Leadership"],
        "job_type": "full_time",
        "source": "custom",
        "user_id": "user_b",
        "apply_url": "https://stealth.com",
    },
]


@pytest.mark.asyncio
async def test_new_user_no_resume_can_load_jobs():
    """Requirement 1 & 2: User with no resume discovers real full-time jobs without fabrication."""
    db = AsyncMock()
    settings = Settings()
    current_user = {"_id": "fresh_user_123"}

    # Provider search returns the public canonical jobs for fresh_user_123
    public_ft_jobs = [j for j in CANONICAL_TEST_JOBS if j["job_type"] == "full_time" and j.get("source") != "custom"]

    with patch("app.modules.matching.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.jobs_services.refresh_live_jobs", AsyncMock(return_value=0)), \
         patch("app.modules.matching.routes.jobs_services.search_jobs", AsyncMock(return_value=public_ft_jobs)):

        matches = await recommended_matches(
            job_type="full_time",
            live_only=False,
            current_user=current_user,
            db=db,
            settings=settings,
        )

        assert len(matches) == 2, f"Expected 2 jobs discovered, got {len(matches)}"
        for m in matches:
            assert isinstance(m, JobMatchOut)
            assert m.has_match is False
            assert m.overall_score is None, f"Expected no fabricated score, got {m.overall_score}"
            assert m.skill_score is None
            assert m.apply_readiness is None
            assert m.matched_skills == []
            assert m.missing_skills == []
            assert len(m.skills_required) > 0, "Expected real job skills_required to be present"
            assert m.apply_url.startswith("https://")


@pytest.mark.asyncio
async def test_new_user_no_resume_can_load_internships():
    """Requirement 3 & 4: User with no resume discovers real internships without fabrication."""
    db = AsyncMock()
    settings = Settings()
    current_user = {"_id": "intern_seeker_456"}

    public_internships = [j for j in CANONICAL_TEST_JOBS if j["job_type"] == "internship" and j.get("source") != "custom"]

    with patch("app.modules.matching.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.matching.routes.jobs_services.refresh_live_jobs", AsyncMock(return_value=0)), \
         patch("app.modules.matching.routes.jobs_services.search_jobs", AsyncMock(return_value=public_internships)):

        matches = await recommended_matches(
            job_type="internship",
            live_only=False,
            current_user=current_user,
            db=db,
            settings=settings,
        )

        assert len(matches) == 1
        intern = matches[0]
        assert intern.job_title == "Data Science Intern"
        assert intern.company == "Microsoft"
        assert intern.stipend_min == 50000
        assert intern.has_match is False
        assert intern.overall_score is None
        assert intern.skills_required == ["Python", "Machine Learning", "SQL"]


@pytest.mark.asyncio
async def test_existing_user_with_resume_gets_personalized_matching():
    """Requirement 6: User with active resume receives personalized deterministic match scores."""
    db = AsyncMock()
    settings = Settings()
    current_user = {"_id": "experienced_user_789"}

    user_resume = {
        "user_id": "experienced_user_789",
        "version": 1,
        "parsed": {"skills": ["Python", "FastAPI", "MongoDB"]},
    }
    user_profile = {
        "target_roles": ["Backend Developer"],
        "experience_years": 2,
        "preferred_locations": ["Bangalore"],
        "remote_preference": "any",
        "category": "EXPERIENCED",
    }
    public_ft_jobs = [CANONICAL_TEST_JOBS[0]]  # Backend Developer job

    mock_match_data = {
        "job_id": "job_ft_001",
        "job_title": "Backend Developer",
        "company": "Accenture",
        "overall_score": 92,
        "skill_score": 95,
        "role_score": 90,
        "experience_score": 90,
        "location_score": 100,
        "salary_score": 85,
        "industry_score": 80,
        "matched_skills": ["Python", "FastAPI", "MongoDB"],
        "partial_skills": [],
        "missing_skills": [],
        "skills_required": ["Python", "FastAPI", "MongoDB"],
        "apply_readiness": "ready",
        "job_type": "full_time",
        "source": "curated",
        "apply_url": "https://accenture.com/careers/job1",
        "posted_days_ago": 2,
        "has_match": True,
    }

    with patch("app.modules.matching.routes.profile_repo.get_profile", AsyncMock(return_value=user_profile)), \
         patch("app.modules.matching.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=user_resume)), \
         patch("app.modules.matching.routes.jobs_services.refresh_live_jobs", AsyncMock(return_value=0)), \
         patch("app.modules.matching.routes.jobs_services.search_jobs", AsyncMock(return_value=public_ft_jobs)), \
         patch("app.modules.matching.routes.matching_services.get_or_compute_matches", AsyncMock(return_value=[mock_match_data])):

        matches = await recommended_matches(
            job_type="full_time",
            live_only=False,
            current_user=current_user,
            db=db,
            settings=settings,
        )

        assert len(matches) == 1
        m = matches[0]
        assert m.has_match is True
        assert m.overall_score == 92
        assert m.apply_readiness == "ready"
        assert m.matched_skills == ["Python", "FastAPI", "MongoDB"]


@pytest.mark.asyncio
async def test_custom_opportunity_ownership_isolation_preserved():
    """Requirement 8: User A cannot discover user B's private custom opportunity."""
    from app.modules.jobs.providers import CuratedJobProvider

    db = AsyncMock()
    provider = CuratedJobProvider(db)

    with patch("app.modules.jobs.repositories.find_jobs", AsyncMock(return_value=[])) as mock_find:
        await provider.search({"user_id": "user_a", "job_type": "full_time"})

        # Verify query generated isolates custom jobs
        called_filter = mock_find.call_args[0][1]
        user_clause = None
        if "$or" in called_filter:
            user_clause = called_filter["$or"]
        elif "$and" in called_filter:
            for sub in called_filter["$and"]:
                if "$or" in sub and any("user_id" in cond for cond in sub["$or"]):
                    user_clause = sub["$or"]
                    break

        assert user_clause is not None, f"User isolation clause not found in {called_filter}"
        assert {"source": {"$ne": "custom"}} in user_clause
        assert {"user_id": "user_a"} in user_clause
        assert {"user_id": "user_b"} not in user_clause
