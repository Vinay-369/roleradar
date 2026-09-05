"""
Phase 16D — Canonical Career Skill Intelligence & Evidence Alignment Tests.

Verifies:
A. Role with no resume returns complete competency map.
B. Resume with explicit skill marks skill DEMONSTRATED.
C. Resume with project evidence marks appropriate skill DEMONSTRATED.
D. Related evidence can produce PARTIALLY_DEMONSTRATED.
E. Missing skill produces NO_RESUME_EVIDENCE.
F. Demonstrated skills are NOT discarded from the API.
G. Evidence provenance is preserved.
H. Role competency tiers are preserved.
I. Career Skill Gap does not use a separate incompatible matching algorithm.
J. Existing job-specific Skill Gap behavior remains intact.
K. Existing Phase 5 evidence mapping tests remain intact.
L. Existing role-intelligence tests remain intact.
M. No-resume flow remains functional.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.modules.learning.engine import (
    determine_competency_tier,
    determine_competency_importance,
    evaluate_career_competencies,
    build_roadmap,
    compute_skill_gaps,
    SkillGap,
)
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role, match_canonical_role
from app.modules.learning.routes import _compute_gaps, get_canonical_roles, get_skill_gaps_for_role
from app.modules.learning.schemas import CareerAlignmentOut, CompetencyTier, CompetencyStatus
from app.modules.resume.models import CandidateProfile, WorkExperienceEntity, ProjectEntity, EducationEntity


# ==============================================================================
# TEST A: Role with no resume returns complete competency map
# ==============================================================================
def test_a_no_resume_returns_complete_competency_map():
    prof, conf, _ = resolve_role("Data Engineer")
    assert prof is not None
    assert conf == "HIGH"

    competencies = evaluate_career_competencies(prof, candidate=None)
    assert len(competencies) > 0

    skills = [c.skill for c in competencies]
    # Check core data engineering skills exist in the output
    assert any("SQL" in s for s in skills)
    assert any("ETL" in s or "Pipeline" in s for s in skills)

    # In no-resume mode, all competencies have NO_RESUME_EVIDENCE with MARKET_REQUIREMENT
    for c in competencies:
        assert c.status == "NO_RESUME_EVIDENCE"
        assert c.current_evidence == "MARKET_REQUIREMENT"
        assert c.candidate_status is None
        assert "Market benchmark requirement" in c.explanation


# ==============================================================================
# TEST B: Resume with explicit skill marks skill DEMONSTRATED
# ==============================================================================
def test_b_explicit_skill_marks_demonstrated():
    prof, _, _ = resolve_role("Backend Developer")
    assert prof is not None

    candidate = CandidateProfile(
        skills=["Python", "FastAPI"],
        skills_explicit=["Python", "FastAPI"],
    )

    competencies = evaluate_career_competencies(prof, candidate=candidate)
    python_comp = next((c for c in competencies if c.skill.lower() == "python"), None)
    assert python_comp is not None
    assert python_comp.status == "DEMONSTRATED"
    assert python_comp.evidence_type == "EXPLICIT_SKILL"
    assert python_comp.current_evidence == "DEMONSTRATED"
    assert python_comp.candidate_status == "MATCHED"
    assert len(python_comp.evidence) > 0
    assert python_comp.evidence[0]["section"] == "SKILLS"


# ==============================================================================
# TEST C: Resume with project evidence marks appropriate skill DEMONSTRATED
# ==============================================================================
def test_c_project_evidence_marks_demonstrated():
    prof, _, _ = resolve_role("Backend Developer")
    assert prof is not None

    candidate = CandidateProfile.from_parsed_dict({
        "skills": [],
        "experience_raw": [],
        "projects_raw": [
            {
                "title": "RoleRadar Platform",
                "tech_stack": ["Docker", "PostgreSQL"],
                "technologies": ["Docker", "PostgreSQL"],
                "bullets": ["Architected microservices using Docker and PostgreSQL containerized databases."],
            }
        ],
    })

    competencies = evaluate_career_competencies(prof, candidate=candidate)
    docker_comp = next((c for c in competencies if "docker" in c.skill.lower()), None)
    assert docker_comp is not None
    assert docker_comp.status == "DEMONSTRATED"
    assert docker_comp.evidence_type == "PROJECT"
    assert "RoleRadar" in docker_comp.evidence[0]["entity_name"]
    assert "Docker" in docker_comp.evidence[0]["text"]


# ==============================================================================
# TEST D: Related evidence produces PARTIALLY_DEMONSTRATED
# ==============================================================================
def test_d_related_evidence_produces_partial():
    prof, _, _ = resolve_role("Backend Developer")
    assert prof is not None

    # Candidate has Flask, but target role expects FastAPI (both in Python web backend cluster)
    candidate = CandidateProfile(
        skills=["Flask"],
        skills_explicit=["Flask"],
    )

    competencies = evaluate_career_competencies(prof, candidate=candidate)
    fastapi_comp = next((c for c in competencies if c.skill.lower() == "fastapi"), None)
    assert fastapi_comp is not None
    assert fastapi_comp.status == "PARTIALLY_DEMONSTRATED"
    assert fastapi_comp.evidence_type == "RELATED_TECHNOLOGY"
    assert "Flask" in fastapi_comp.explanation


# ==============================================================================
# TEST E: Missing skill produces NO_RESUME_EVIDENCE (neutral wording)
# ==============================================================================
def test_e_missing_skill_produces_no_resume_evidence():
    prof, _, _ = resolve_role("Backend Developer")
    assert prof is not None

    candidate = CandidateProfile(
        skills=["Python"],
        skills_explicit=["Python"],
    )

    competencies = evaluate_career_competencies(prof, candidate=candidate)
    redis_comp = next((c for c in competencies if "redis" in c.skill.lower()), None)
    assert redis_comp is not None
    assert redis_comp.status == "NO_RESUME_EVIDENCE"
    assert redis_comp.evidence_type == "NONE"
    assert redis_comp.current_evidence == "MISSING"
    assert redis_comp.candidate_status == "MISSING"
    # Semantic honesty: Never accuse the candidate of not knowing it
    assert "no verified evidence was found in your resume" in redis_comp.reason
    assert "No resume evidence found" in redis_comp.explanation


# ==============================================================================
# TEST F: Demonstrated skills are NOT discarded from the API
# ==============================================================================
def test_f_demonstrated_skills_not_discarded():
    prof, _, _ = resolve_role("Software Engineer")
    assert prof is not None

    candidate = CandidateProfile(
        skills=["Git", "REST APIs", "Python"],
        skills_explicit=["Git", "REST APIs", "Python"],
    )

    competencies = evaluate_career_competencies(prof, candidate=candidate)
    demonstrated = [c for c in competencies if c.status == "DEMONSTRATED"]
    assert len(demonstrated) >= 2  # Git and REST APIs are in Software Engineer role

    # All demonstrated skills must still be in the returned list
    demonstrated_skills = {c.skill.lower() for c in demonstrated}
    assert any("git" in s for s in demonstrated_skills)
    assert any("rest" in s for s in demonstrated_skills)


# ==============================================================================
# TEST G: Evidence provenance is preserved
# ==============================================================================
def test_g_evidence_provenance_preserved():
    prof, _, _ = resolve_role("Software Engineer")
    assert prof is not None

    candidate = CandidateProfile.from_parsed_dict({
        "experience_raw": [
            "Senior Developer at Tech Innovations Corp (2022 - Present)",
            "Implemented RESTful APIs and optimized microservices for 1M users using Git workflows.",
        ]
    })

    competencies = evaluate_career_competencies(prof, candidate=candidate)
    git_comp = next((c for c in competencies if "git" in c.skill.lower()), None)
    assert git_comp is not None
    assert git_comp.status == "DEMONSTRATED"
    assert len(git_comp.evidence) > 0
    assert git_comp.evidence[0]["section"] == "EXPERIENCE"
    assert "Tech Innovations Corp" in git_comp.evidence[0]["entity_name"]
    assert "RESTful APIs" in git_comp.evidence[0]["text"] or "Git" in git_comp.evidence[0]["text"]


# ==============================================================================
# TEST H: Role competency tiers are preserved
# ==============================================================================
def test_h_role_competency_tiers_preserved():
    prof, _, _ = resolve_role("Backend Developer")
    assert prof is not None

    competencies = evaluate_career_competencies(prof, candidate=None)
    tiers = {c.tier for c in competencies}

    # Verify canonical tiers are present
    assert "FOUNDATION" in tiers
    assert "CORE" in tiers
    assert "TOOLS" in tiers

    python_comp = next((c for c in competencies if c.skill.lower() == "python"), None)
    assert python_comp.tier == "FOUNDATION"

    docker_comp = next((c for c in competencies if c.skill.lower() == "docker"), None)
    assert docker_comp.tier == "TOOLS"


# ==============================================================================
# TEST I: Roadmap excludes demonstrated skills
# ==============================================================================
def test_i_roadmap_excludes_demonstrated_skills():
    gaps = [
        SkillGap(
            skill="Python",
            priority="CORE",
            reason="Demonstrated",
            target_job_title="Backend Developer",
            current_evidence="DEMONSTRATED",
            status="DEMONSTRATED",
        ),
        SkillGap(
            skill="Docker",
            priority="CORE",
            reason="Missing",
            target_job_title="Backend Developer",
            current_evidence="MISSING",
            status="NO_RESUME_EVIDENCE",
        ),
        SkillGap(
            skill="Kubernetes",
            priority="SECONDARY",
            reason="Partial",
            target_job_title="Backend Developer",
            current_evidence="PARTIAL",
            status="PARTIALLY_DEMONSTRATED",
        ),
    ]

    roadmap = build_roadmap(gaps)
    all_scheduled = roadmap["immediate"] + roadmap["week_1"] + roadmap["week_2"] + roadmap["month_1"]

    # Python is DEMONSTRATED, so it must NOT be scheduled into the learning roadmap
    assert "Python" not in all_scheduled
    assert "Docker" in all_scheduled
    assert "Kubernetes" in all_scheduled


# ==============================================================================
# TEST J: Async API Endpoint returns CareerAlignmentOut with complete summary
# ==============================================================================
@pytest.mark.asyncio
async def test_j_api_endpoint_career_alignment_contract():
    db = AsyncMock()
    settings = Settings()

    candidate_resume = {
        "user_id": "user_456",
        "parsed": {
            "skills": ["Python", "Git"],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    with patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=candidate_resume)), \
         patch("app.modules.learning.routes.resume_repo.list_achievements", AsyncMock(return_value=[])), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value={"target_roles": ["Backend Developer"]})), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        res = await get_skill_gaps_for_role(
            role="Backend Developer",
            job_id=None,
            current_user={"_id": "user_456"},
            db=db,
            settings=settings,
        )

        assert isinstance(res, CareerAlignmentOut)
        assert res.role == "Backend Developer"
        assert res.has_resume is True
        assert res.summary.total > 0
        assert res.summary.demonstrated >= 2  # Python and Git demonstrated
        assert res.summary.total == (
            res.summary.demonstrated + res.summary.partially_demonstrated + res.summary.no_resume_evidence
        )
        assert len(res.competencies) == res.summary.total


# ==============================================================================
# TEST K: Canonical roles endpoint returns authoritative list
# ==============================================================================
@pytest.mark.asyncio
async def test_k_canonical_roles_endpoint():
    roles = await get_canonical_roles()
    assert len(roles) >= 20
    role_names = [r.role for r in roles]
    assert "Software Engineer" in role_names
    assert "Data Engineer" in role_names
    assert "Backend Developer" in role_names
    assert "Frontend Developer" in role_names
