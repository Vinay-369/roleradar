import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.modules.learning.routes import _compute_gaps, _provenance_to_roadmap_fields
from app.modules.learning.schemas import RoadmapOut


def _mock_embedder():
    m = MagicMock()
    m.similarity.return_value = 0.0
    return m


@pytest.mark.asyncio
async def test_no_resume_returns_market_roadmap_with_none_status():
    """State 1: No resume -> MARKET + personalization_status=NONE + is_personalized=False"""
    db = AsyncMock()
    settings = Settings()

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.resume_repo.list_achievements", AsyncMock(return_value=[])), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value={"target_roles": ["Frontend Developer"]})), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "user_123", role="Frontend Developer", include_provenance=True)
        fields = _provenance_to_roadmap_fields(provenance)

        assert provenance.resume_found is False
        assert provenance.sufficient_evidence is False
        assert fields["roadmap_type"] == "MARKET"
        assert fields["personalization_status"] == "NONE"
        assert fields["is_personalized"] is False
        assert "Frontend Developer" in fields["role_context"]
        assert "Market Benchmark" in fields["role_context"]

        # Verify RoadmapOut schema accepts fields
        roadmap = RoadmapOut(
            immediate=["React"],
            week_1=["TypeScript"],
            week_2=["HTML5"],
            month_1=["CSS3"],
            **fields,
        )
        assert roadmap.is_personalized is False
        assert roadmap.roadmap_type == "MARKET"
        assert roadmap.personalization_status == "NONE"


@pytest.mark.asyncio
async def test_resume_insufficient_evidence_returns_limited_evidence_status():
    """State 2: Resume present but < 3 skills -> MARKET + personalization_status=LIMITED_EVIDENCE + is_personalized=False"""
    db = AsyncMock()
    settings = Settings()

    scant_resume = {
        "user_id": "user_123",
        "parsed": {
            "skills": ["Git"],  # only 1 skill (< 3 threshold)
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=scant_resume)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value={"target_roles": ["Backend Developer"]})), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "user_123", role="Backend Developer", include_provenance=True)
        fields = _provenance_to_roadmap_fields(provenance)

        assert provenance.resume_found is True
        assert provenance.sufficient_evidence is False
        assert fields["roadmap_type"] == "MARKET"
        assert fields["personalization_status"] == "LIMITED_EVIDENCE"
        assert fields["is_personalized"] is False
        assert "Backend Developer" in fields["role_context"]


@pytest.mark.asyncio
async def test_meaningful_resume_plus_target_role_returns_candidate_personalized():
    """State 3: Meaningful resume (>= 3 skills) + target role -> CANDIDATE + personalization_status=PERSONALIZED + is_personalized=True"""
    db = AsyncMock()
    settings = Settings()

    rich_resume = {
        "user_id": "user_123",
        "parsed": {
            "skills": ["Python", "FastAPI", "SQL", "PostgreSQL"],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=rich_resume)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value={"target_roles": ["Backend Developer"]})), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "user_123", role="Backend Developer", include_provenance=True)
        fields = _provenance_to_roadmap_fields(provenance)

        assert provenance.resume_found is True
        assert provenance.sufficient_evidence is True
        assert provenance.job_is_specific is False
        assert fields["roadmap_type"] == "CANDIDATE"
        assert fields["personalization_status"] == "PERSONALIZED"
        assert fields["is_personalized"] is True
        assert "Backend Developer" in fields["role_context"]


@pytest.mark.asyncio
async def test_meaningful_resume_plus_specific_job_returns_job_personalized():
    """State 4: Meaningful resume + specific job ID -> JOB + personalization_status=PERSONALIZED + is_personalized=True"""
    db = AsyncMock()
    settings = Settings()

    rich_resume = {
        "user_id": "user_123",
        "parsed": {
            "skills": ["Python", "Docker", "Kubernetes", "AWS"],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    specific_job = {
        "_id": "job_abc",
        "id": "job_abc",
        "title": "Senior DevOps Engineer",
        "company": "CloudCorp",
        "must_have_skills": ["Terraform", "CI/CD", "Docker", "AWS"],
        "preferred_skills": ["Golang"],
        "skills_required": ["Terraform", "CI/CD", "Docker", "AWS"],
        "skills_nice_to_have": ["Golang"],
        "source": "live",
    }

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=rich_resume)), \
         patch("app.modules.learning.routes.jobs_repo.get_job_by_id", AsyncMock(return_value=specific_job)):

        gaps, job, provenance = await _compute_gaps(db, settings, "user_123", job_id="job_abc", include_provenance=True)
        fields = _provenance_to_roadmap_fields(provenance)

        assert provenance.resume_found is True
        assert provenance.sufficient_evidence is True
        assert provenance.job_is_specific is True
        assert fields["roadmap_type"] == "JOB"
        assert fields["personalization_status"] == "PERSONALIZED"
        assert fields["is_personalized"] is True
        assert "Senior DevOps Engineer at CloudCorp" == fields["role_context"]
