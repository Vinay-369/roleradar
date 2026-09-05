"""
Comprehensive Role Intelligence & Skill Gap Test Suite.
Tests:
- Role resolution across all major career domains
- Negative cross-contamination prevention
- Unknown / low-confidence role handling
- Resume personalization modes (No resume vs resume present)
- The 15 required real-world roles matrix
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.modules.learning.role_taxonomy import (
    ROLE_TAXONOMY,
    resolve_role,
)
from app.modules.learning.routes import (
    _aggregate_role_requirements,
    _compute_gaps,
    _provenance_to_roadmap_fields,
)
from app.modules.learning.schemas import RoadmapOut, SkillGapOut


def _mock_embedder():
    m = MagicMock()
    # Default zero similarity unless specified
    m.similarity.return_value = 0.0
    return m


# ==============================================================================
# PART 15: ROLE RESOLUTION TESTS
# ==============================================================================

@pytest.mark.parametrize("input_role,expected_canonical,expected_domain", [
    ("Software Engineer", "Software Engineer", "Software Engineering"),
    ("Backend Developer", "Backend Developer", "Software Engineering"),
    ("Data Scientist", "Data Scientist", "Data & Analytics"),
    ("Data Analyst", "Data Analyst", "Data & Analytics"),
    ("Data Engineer", "Data Engineer", "Data & Analytics"),
    ("DevOps Engineer", "DevOps Engineer", "Cloud / DevOps / Infrastructure"),
    ("Cybersecurity Analyst", "Cybersecurity Analyst", "Cybersecurity"),
    ("Graphic Designer", "Graphic Designer", "Design"),
    ("Product Manager", "Product Manager", "Product"),
    ("Financial Analyst", "Financial Analyst", "Finance / Accounting"),
    ("HR Specialist", "HR Generalist", "HR / People"),
    ("Digital Marketing Specialist", "Digital Marketing Specialist", "Marketing"),
    ("Mechanical Engineer", "Mechanical Engineer", "Engineering"),
    ("Civil Engineer", "Civil Engineer", "Engineering"),
    ("Teacher", "Teacher", "Education"),
    ("Healthcare Analyst", "Healthcare Analyst", "Healthcare"),
    ("Supply Chain Analyst", "Supply Chain Analyst", "Operations / Supply Chain"),
    ("Research Scientist", "Research Scientist", "Research / Academia"),
    ("Video Editor", "Video Editor", "Media / Creative"),
    ("Architect", "Architect", "Architecture / Construction"),
])
def test_canonical_role_resolution(input_role, expected_canonical, expected_domain):
    profile, conf, reason = resolve_role(input_role)
    assert profile is not None, f"Role '{input_role}' failed to resolve"
    assert profile.canonical_role == expected_canonical
    assert profile.domain == expected_domain
    assert conf in ("HIGH", "MEDIUM")


# ==============================================================================
# PART 15: NEGATIVE CROSS-CONTAMINATION TESTS
# ==============================================================================

def test_negative_cybersecurity_analyst_does_not_become_data_analyst():
    profile, conf, _ = resolve_role("Cybersecurity Analyst")
    assert profile is not None
    assert profile.canonical_role == "Cybersecurity Analyst"
    assert profile.canonical_role != "Data Analyst"
    assert profile.domain == "Cybersecurity"
    assert "Threat Monitoring & Detection" in profile.core_competencies
    assert "Pandas" not in profile.core_competencies


def test_negative_graphic_designer_does_not_become_devops_engineer():
    profile, conf, _ = resolve_role("Graphic Designer")
    assert profile is not None
    assert profile.canonical_role == "Graphic Designer"
    assert profile.domain == "Design"
    assert "Visual Composition & Layout" in profile.core_competencies
    assert "Docker" not in profile.core_competencies
    assert "Kubernetes" not in profile.core_competencies


def test_negative_product_manager_does_not_become_software_engineer():
    profile, conf, _ = resolve_role("Product Manager")
    assert profile is not None
    assert profile.canonical_role == "Product Manager"
    assert profile.domain == "Product"
    assert "Product Strategy & Vision" in profile.core_competencies
    assert "Data Structures & Algorithms" not in profile.core_competencies


def test_negative_financial_analyst_does_not_become_data_analyst():
    profile, conf, _ = resolve_role("Financial Analyst")
    assert profile is not None
    assert profile.canonical_role == "Financial Analyst"
    assert profile.domain == "Finance / Accounting"
    assert any("Financial Modeling" in c for c in profile.core_competencies)


def test_negative_mechanical_engineer_does_not_become_software_engineer():
    profile, conf, _ = resolve_role("Mechanical Engineer")
    assert profile is not None
    assert profile.canonical_role == "Mechanical Engineer"
    assert profile.domain == "Engineering"
    assert any("CAD" in c for c in profile.core_competencies)
    assert "REST APIs" not in profile.core_competencies


def test_negative_healthcare_analyst_does_not_become_data_analyst():
    profile, conf, _ = resolve_role("Healthcare Analyst")
    assert profile is not None
    assert profile.canonical_role == "Healthcare Analyst"
    assert profile.domain == "Healthcare"
    assert any("Health" in c or "Clinical" in c for c in profile.core_competencies)


def test_negative_marine_robotics_engineer_does_not_become_generic_software_engineer():
    # Marine Robotics Engineer must not inherit generic software engineering requirements
    profile, conf, _ = resolve_role("Marine Robotics Engineer")
    # It must either resolve with LOW confidence or to Robotics Engineer, NEVER Software Engineer
    if profile is not None:
        assert profile.canonical_role != "Software Engineer"
        assert profile.domain != "Software Engineering"
    else:
        assert conf == "LOW"


def test_generic_tokens_alone_cannot_determine_role():
    for token in ["Engineer", "Analyst", "Manager", "Developer", "Specialist", "Consultant", "Coordinator"]:
        profile, conf, _ = resolve_role(token)
        assert profile is None, f"Generic token '{token}' should not resolve to a canonical role"
        assert conf == "LOW"


# ==============================================================================
# PART 15: UNKNOWN / LOW-CONFIDENCE ROLES
# ==============================================================================

@pytest.mark.asyncio
async def test_unknown_custom_role_returns_low_confidence_and_no_generic_skills():
    db = AsyncMock()
    with patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):
        res = await _aggregate_role_requirements(db, "Intergalactic Warp Drive Specialist 999")
        assert res["confidence"] == "LOW"
        assert res["provenance"] == "LOW_CONFIDENCE"
        assert len(res["must_have_skills"]) == 0
        assert len(res["preferred_skills"]) == 0
        assert "Python" not in res["must_have_skills"]
        assert "Docker" not in res["preferred_skills"]
        assert "couldn't confidently determine" in res["message"]


@pytest.mark.asyncio
async def test_marine_robotics_engineer_unknown_state_has_zero_fabricated_skills():
    db = AsyncMock()
    with patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):
        res = await _aggregate_role_requirements(db, "Marine Robotics Engineer")
        assert res["confidence"] == "LOW"
        assert len(res["must_have_skills"]) == 0
        # Absolutely NO arbitrary software fallback
        assert "Python" not in res["must_have_skills"]
        assert "Docker" not in res["must_have_skills"]
        assert "AWS" not in res["preferred_skills"]


# ==============================================================================
# PART 16: RESUME PERSONALIZATION TESTS (A - G)
# ==============================================================================

@pytest.mark.asyncio
async def test_personalization_mode_a_no_resume_returns_market_benchmark():
    """A. No resume -> market benchmark only, candidate_status is None, non-punitive reason"""
    db = AsyncMock()
    settings = Settings()

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "user_no_resume", role="Graphic Designer", include_provenance=True)
        fields = _provenance_to_roadmap_fields(provenance)

        assert provenance.resume_found is False
        assert fields["roadmap_type"] == "MARKET"
        assert fields["personalization_status"] == "NONE"
        assert fields["is_personalized"] is False
        assert "Graphic Designer" in fields["role_context"]
        assert "Market Benchmark" in fields["role_context"]

        # Each gap is labeled as market expectation, NOT candidate missing
        assert len(gaps) > 0
        for g in gaps:
            assert g.current_evidence == "MARKET_REQUIREMENT"
            assert g.candidate_status is None
            assert "commonly expected" in g.reason or "strengthens" in g.reason
            assert "no evidence of it was found in your resume" not in g.reason


@pytest.mark.asyncio
async def test_personalization_mode_b_resume_with_strong_match():
    """B. Resume with strong match -> matched skills are recognized, not marked as missing"""
    db = AsyncMock()
    settings = Settings()

    # Graphic designer candidate who has Photoshop and Typography
    resume_data = {
        "user_id": "designer_user",
        "parsed": {
            "skills": [
                "Adobe Photoshop",
                "Adobe Illustrator",
                "Typography & Font Pairing",
                "Visual Composition & Layout",
            ],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=resume_data)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "designer_user", role="Graphic Designer", include_provenance=True)
        fields = _provenance_to_roadmap_fields(provenance)

        assert provenance.resume_found is True
        assert provenance.sufficient_evidence is True
        assert fields["roadmap_type"] == "CANDIDATE"
        assert fields["personalization_status"] == "PERSONALIZED"
        assert fields["is_personalized"] is True

        # Phase 16D Update: Demonstrated skills are preserved in the canonical API response
        # with DEMONSTRATED status, rather than being discarded.
        # Verified skills must NOT be reported as missing.
        missing_skills = [g.skill for g in gaps if g.status == "NO_RESUME_EVIDENCE" or g.current_evidence == "MISSING"]
        assert "Visual Composition & Layout" not in missing_skills
        assert "Typography & Font Pairing" not in missing_skills
        demonstrated_skills = [g.skill for g in gaps if g.status == "DEMONSTRATED"]
        assert "Visual Composition & Layout" in demonstrated_skills
        assert "Typography & Font Pairing" in demonstrated_skills


@pytest.mark.asyncio
async def test_personalization_mode_c_resume_with_partial_match():
    """C. Resume with partial match -> partial/related skills appear with SECONDARY priority"""
    db = AsyncMock()
    settings = Settings()

    # Candidate has semantically close skill (similarity >= 0.55)
    resume_data = {
        "user_id": "partial_user",
        "parsed": {
            "skills": ["Python", "FastAPI", "SQL", "Postgres"],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    embedder = MagicMock()
    # Mock similarity: "RESTful API Design" vs "fastapi" -> 0.65 (partial)
    def sim_side_effect(a, b):
        if "restful api design" in a and "fastapi" in b:
            return 0.65
        return 0.0
    embedder.similarity.side_effect = sim_side_effect

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=embedder), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=resume_data)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "partial_user", role="Backend Developer", include_provenance=True)

        partial_gaps = [g for g in gaps if g.priority == "SECONDARY"]
        assert len(partial_gaps) >= 1
        assert any("RESTful API Design" in g.skill for g in partial_gaps)
        assert any(g.candidate_status == "PARTIAL" for g in partial_gaps)


@pytest.mark.asyncio
async def test_personalization_mode_d_resume_with_missing_skills():
    """D. Resume with missing skills -> genuine missing skills appear as CORE gaps"""
    db = AsyncMock()
    settings = Settings()

    # Candidate is missing core skills
    resume_data = {
        "user_id": "dev_user",
        "parsed": {
            "skills": ["HTML5", "CSS3", "Git"],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=resume_data)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "dev_user", role="Backend Developer", include_provenance=True)
        missing_core = [g for g in gaps if g.priority == "CORE"]
        assert len(missing_core) > 0
        assert all(g.candidate_status == "MISSING" for g in missing_core)
        assert all(g.current_evidence == "MISSING" for g in missing_core)


@pytest.mark.asyncio
async def test_personalization_mode_e_unrelated_skills_do_not_satisfy_requirements():
    """E. Resume containing unrelated skills must NOT falsely satisfy requirements"""
    db = AsyncMock()
    settings = Settings()

    # Candidate has nursing & hospitality skills, applying to Backend Developer
    unrelated_resume = {
        "user_id": "unrelated_user",
        "parsed": {
            "skills": ["Patient Triage", "Vital Signs Monitoring", "Bedside Care", "Medication Administration"],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=unrelated_resume)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        gaps, job, provenance = await _compute_gaps(db, settings, "unrelated_user", role="Backend Developer", include_provenance=True)
        # All Backend core requirements must remain missing
        core_gaps = [g for g in gaps if g.priority == "CORE"]
        assert len(core_gaps) >= 4
        gap_names = {g.skill for g in core_gaps}
        assert "RESTful API Design" in gap_names
        assert "Database Modeling & Querying" in gap_names


@pytest.mark.asyncio
async def test_personalization_mode_g_specific_jd_overrides_generic_benchmark():
    """G. Specific JD -> JD requirements override generic role benchmark"""
    db = AsyncMock()
    settings = Settings()

    rich_resume = {
        "user_id": "candidate_1",
        "parsed": {
            "skills": ["Python", "Docker", "Git"],
            "experience_raw": [],
            "projects_raw": [],
        },
    }

    custom_job = {
        "_id": "custom_job_99",
        "id": "custom_job_99",
        "title": "Quantum Systems Engineer",
        "company": "Qubit Labs",
        "must_have_skills": ["Qiskit", "Superconducting Circuits", "Cryogenic Control"],
        "preferred_skills": ["Python"],
        "skills_required": ["Qiskit", "Superconducting Circuits", "Cryogenic Control"],
        "skills_nice_to_have": ["Python"],
        "source": "live",
    }

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=rich_resume)), \
         patch("app.modules.learning.routes.jobs_repo.get_job_by_id", AsyncMock(return_value=custom_job)):

        gaps, job, provenance = await _compute_gaps(db, settings, "candidate_1", job_id="custom_job_99", include_provenance=True)
        fields = _provenance_to_roadmap_fields(provenance)

        assert provenance.job_is_specific is True
        assert fields["roadmap_type"] == "JOB"
        assert fields["personalization_status"] == "PERSONALIZED"
        assert "Quantum Systems Engineer at Qubit Labs" == fields["role_context"]

        gap_skills = [g.skill for g in gaps]
        # Specific JD must-haves must be the gaps, not generic software engineer skills
        assert "Qiskit" in gap_skills
        assert "Superconducting Circuits" in gap_skills
        assert "Cryogenic Control" in gap_skills


# ==============================================================================
# PART 17: REQUIRED REAL-WORLD ROLES TEST MATRIX (15 ROLES)
# ==============================================================================

REAL_WORLD_15_ROLES = [
    "Data Scientist",
    "Software Engineer",
    "DevOps Engineer",
    "Cybersecurity Analyst",
    "Graphic Designer",
    "Product Manager",
    "Financial Analyst",
    "HR Specialist",
    "Mechanical Engineer",
    "Marketing Specialist",
    "Healthcare Analyst",
    "Supply Chain Analyst",
    "Teacher",
    "Architect",
    "Marine Robotics Engineer",
]


@pytest.mark.asyncio
async def test_required_real_world_15_roles_matrix():
    """
    Executes the exact 15-role matrix specified in Part 17:
    Captures:
      - resolved canonical role
      - domain
      - confidence
      - number of benchmark skills
      - top benchmark skills
      - provenance
      - whether fallback was used (MUST BE FALSE)
    """
    db = AsyncMock()
    with patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):
        results = []
        for role_name in REAL_WORLD_15_ROLES:
            agg = await _aggregate_role_requirements(db, role_name)
            
            # Check whether generic software fallback was used:
            # Fallback was previously: top_required = ["Python", "JavaScript", "SQL", "REST APIs", "Git"]
            # and top_nice = ["Docker", "AWS", "CI/CD", "Testing"]
            generic_fallback_required = ["Python", "JavaScript", "SQL", "REST APIs", "Git"]
            generic_fallback_nice = ["Docker", "AWS", "CI/CD", "Testing"]
            fallback_used = (
                agg["must_have_skills"] == generic_fallback_required
                and agg["preferred_skills"] == generic_fallback_nice
            )

            result_entry = {
                "input_role": role_name,
                "canonical_role": agg["title"],
                "domain": agg["domain"],
                "confidence": agg["confidence"],
                "num_benchmark_skills": len(agg["must_have_skills"]) + len(agg["preferred_skills"]),
                "top_benchmark_skills": agg["must_have_skills"][:3],
                "provenance": agg["provenance"],
                "fallback_used": fallback_used,
            }
            results.append(result_entry)

            # CRITICAL ASSERTION: Fallback must NEVER be used!
            assert not fallback_used, f"Role '{role_name}' used generic software fallback!"

            # Specific role checks
            if role_name == "Marine Robotics Engineer":
                assert agg["confidence"] == "LOW"
                assert len(agg["must_have_skills"]) == 0
                assert agg["provenance"] == "LOW_CONFIDENCE"
            elif role_name == "Graphic Designer":
                assert agg["domain"] == "Design"
                assert "Visual Composition & Layout" in agg["must_have_skills"]
                assert "Docker" not in agg["must_have_skills"]
            elif role_name == "Cybersecurity Analyst":
                assert agg["domain"] == "Cybersecurity"
                assert "Threat Monitoring & Detection" in agg["must_have_skills"]
            elif role_name == "Teacher":
                assert agg["domain"] == "Education"
                assert "Curriculum & Lesson Planning" in agg["must_have_skills"]
            elif role_name == "Architect":
                assert agg["domain"] == "Architecture / Construction"
                assert any("Architectural" in s or "BIM" in s for s in agg["must_have_skills"])
            elif role_name == "Mechanical Engineer":
                assert agg["domain"] == "Engineering"
                assert any("CAD" in s or "FEA" in s for s in agg["must_have_skills"])

        # Ensure all 15 were tested
        assert len(results) == 15
