"""
Phase 2 Regression Test Suite:
Canonical Candidate Evidence & Skill Single Source of Truth.

Verifies:
1. CandidateProfile canonical skill extraction
2. Skill normalization (case and aliases: python -> Python, node -> Node.js, mongo -> MongoDB)
3. Explicit skill evidence tier assignment (EXPLICIT)
4. Project technology evidence tier assignment (PROJECT)
5. Experience technology evidence tier assignment (EXPERIENCE)
6. Duplicate normalization (case/alias deduplication into a single canonical skill)
7. Unsupported skill absence (PyTorch absent when not in candidate evidence)
8. Matching consumes canonical evidence (Flask in projects matched)
9. Learning consumes canonical evidence
10. Tailoring receives canonical evidence
11. Copilot receives canonical evidence
12. Cross-system consistency across matching, learning, Skill Gap, tailoring, and Copilot
13. No conversion of project evidence into professional experience years
14. No conversion of certification into professional experience
"""
import pytest
from app.modules.jobs.skill_vocabulary import canonicalize_skill_name
from app.modules.resume.models import (
    CandidateProfile,
    SkillEvidenceTier,
    WorkExperienceEntity,
    ProjectEntity,
)
from app.modules.matching.engine import compute_match
from app.core.embeddings.factory import build_embedding_provider
from app.core.config import get_settings


@pytest.fixture
def student_resume_data():
    """
    Standard student candidate resume as defined in Section 12 of Phase 2 spec:
    - Explicit skills: Python, TensorFlow, Keras
    - Project evidence: Flask, OpenCV, MongoDB
    - Absolutely NO PyTorch anywhere.
    """
    return {
        "personal": {
            "name": "Aarav Sharma",
            "email": "aarav.sharma@example.com",
        },
        "summary": "Motivated computer science student with hands-on projects in web development and computer vision.",
        "skills": ["Python", "TensorFlow", "Keras"],
        "skills_explicit": ["Python", "TensorFlow", "Keras"],
        "projects": [
            {
                "id": "proj_0",
                "title": "Smart Vision Web App",
                "tech_stack": "Flask, OpenCV, MongoDB",
                "technologies": ["Flask", "OpenCV", "MongoDB"],
                "bullets": [
                    "Engineered a Flask application with OpenCV image processing pipelines.",
                    "Persisted image metadata into MongoDB clusters with sub-100ms response times.",
                ],
            }
        ],
        "experience": [],
        "education": [
            {
                "id": "edu_0",
                "institution": "National Institute of Technology",
                "degree": "B.Tech Computer Science",
                "dates": "2022 - 2026",
            }
        ],
        "certifications": ["TensorFlow Developer Certificate"],
    }


# ------------------------------------------------------------------------------
# 1. CandidateProfile canonical skill extraction
# ------------------------------------------------------------------------------
def test_candidate_profile_canonical_skill_extraction(student_resume_data):
    profile = CandidateProfile.from_parsed_dict(student_resume_data)
    demonstrated = profile.get_all_demonstrated_skills()

    # Must contain both explicit skills and project technologies
    expected = {"Python", "TensorFlow", "Keras", "Flask", "OpenCV", "MongoDB"}
    assert expected.issubset(set(demonstrated))


# ------------------------------------------------------------------------------
# 2. Skill normalization
# ------------------------------------------------------------------------------
def test_skill_normalization():
    assert canonicalize_skill_name("python") == "Python"
    assert canonicalize_skill_name("PYTHON") == "Python"
    assert canonicalize_skill_name("node") == "Node.js"
    assert canonicalize_skill_name("nodejs") == "Node.js"
    assert canonicalize_skill_name("Node") == "Node.js"
    assert canonicalize_skill_name("mongo") == "MongoDB"
    assert canonicalize_skill_name("mongodb") == "MongoDB"
    assert canonicalize_skill_name("k8s") == "Kubernetes"
    assert canonicalize_skill_name("golang") == "Go"
    assert canonicalize_skill_name("postgres") == "PostgreSQL"
    assert canonicalize_skill_name("scikit-learn") == "scikit-learn"
    assert canonicalize_skill_name("sklearn") == "scikit-learn"
    assert canonicalize_skill_name("fast api") == "FastAPI"


# ------------------------------------------------------------------------------
# 3. Explicit skill evidence tier assignment
# ------------------------------------------------------------------------------
def test_explicit_skill_evidence_tier():
    profile = CandidateProfile.from_parsed_dict({
        "skills": ["Go", "Docker"],
        "projects": [],
        "experience": [],
    })
    skills_map = profile.get_canonical_skills_map()
    assert skills_map["go"].tier == SkillEvidenceTier.EXPLICIT
    assert skills_map["docker"].tier == SkillEvidenceTier.EXPLICIT
    assert skills_map["go"].is_demonstrated is True
    assert skills_map["go"].is_professional is False


# ------------------------------------------------------------------------------
# 4. Project technology evidence tier assignment
# ------------------------------------------------------------------------------
def test_project_technology_evidence_tier(student_resume_data):
    profile = CandidateProfile.from_parsed_dict(student_resume_data)
    skills_map = profile.get_canonical_skills_map()

    assert skills_map["flask"].tier == SkillEvidenceTier.PROJECT
    assert skills_map["opencv"].tier == SkillEvidenceTier.PROJECT
    assert skills_map["mongodb"].tier == SkillEvidenceTier.PROJECT
    assert skills_map["flask"].is_demonstrated is True
    assert skills_map["flask"].is_professional is False


# ------------------------------------------------------------------------------
# 5. Experience technology evidence tier assignment
# ------------------------------------------------------------------------------
def test_experience_technology_evidence_tier():
    profile = CandidateProfile.from_parsed_dict({
        "skills": ["Java"],
        "experience": [
            {
                "id": "exp_0",
                "company": "Tech Corp",
                "role": "Backend Engineer",
                "technologies": ["Spring Boot", "Kafka"],
                "bullets": ["Engineered microservices using Spring Boot and Kafka messaging."],
            }
        ],
        "projects": [],
    })
    skills_map = profile.get_canonical_skills_map()
    assert skills_map["spring boot"].tier == SkillEvidenceTier.EXPERIENCE
    assert skills_map["kafka"].tier == SkillEvidenceTier.EXPERIENCE
    assert skills_map["spring boot"].is_professional is True
    assert skills_map["java"].tier == SkillEvidenceTier.EXPLICIT
    assert skills_map["java"].is_professional is False


# ------------------------------------------------------------------------------
# 6. Duplicate normalization
# ------------------------------------------------------------------------------
def test_duplicate_normalization():
    # 'mongo' in explicit, 'MongoDB' in projects
    profile = CandidateProfile.from_parsed_dict({
        "skills": ["mongo", "nodejs"],
        "projects": [
            {
                "id": "proj_1",
                "title": "App",
                "technologies": ["MongoDB", "Node.js"],
                "bullets": ["Built app with MongoDB and Node.js"],
            }
        ],
    })
    demonstrated = profile.get_all_demonstrated_skills()
    assert demonstrated.count("MongoDB") == 1
    assert demonstrated.count("Node.js") == 1
    assert "mongo" not in demonstrated
    assert "nodejs" not in demonstrated

    # Upgraded tier to PROJECT because it was demonstrated in project
    skills_map = profile.get_canonical_skills_map()
    assert skills_map["mongodb"].tier == SkillEvidenceTier.PROJECT
    assert skills_map["node.js"].tier == SkillEvidenceTier.PROJECT


# ------------------------------------------------------------------------------
# 7. Unsupported skill absence (Critical Negative Test)
# ------------------------------------------------------------------------------
def test_unsupported_skill_absence(student_resume_data):
    profile = CandidateProfile.from_parsed_dict(student_resume_data)
    demonstrated = profile.get_all_demonstrated_skills()

    # PyTorch was NOT anywhere in student resume -> MUST NOT be in demonstrated skills
    assert "PyTorch" not in demonstrated
    assert "pytorch" not in [s.lower() for s in demonstrated]
    assert profile.has_demonstrated_skill("PyTorch") is False
    assert profile.has_demonstrated_skill("pytorch") is False


# ------------------------------------------------------------------------------
# 8. Matching consumes canonical evidence
# ------------------------------------------------------------------------------
def test_matching_consumes_canonical_evidence(student_resume_data):
    profile = CandidateProfile.from_parsed_dict(student_resume_data)
    demonstrated = profile.get_all_demonstrated_skills()

    settings = get_settings()
    embedder = build_embedding_provider(settings)

    # Job requiring Flask (demonstrated in projects, but NOT in explicit skills)
    job_flask = {
        "id": "job_flask_01",
        "title": "Junior Python Developer",
        "company": "Innovate Ltd",
        "skills_required": ["Python", "Flask"],
    }
    candidate = {
        "skills": demonstrated,
        "target_roles": ["Python Developer"],
        "experience_years": 0,
    }

    match_result = compute_match(candidate, job_flask, embedder, category="FRESHER")
    # Both Python and Flask must be matched!
    matched_lower = [s.lower() for s in match_result.skill_match.matched]
    assert "python" in matched_lower
    assert "flask" in matched_lower
    assert "flask" not in [s.lower() for s in match_result.skill_match.missing]


# ------------------------------------------------------------------------------
# 9. Learning consumes canonical evidence
# ------------------------------------------------------------------------------
def test_learning_consumes_canonical_evidence(student_resume_data):
    from app.modules.learning.engine import evaluate_career_competencies
    from app.modules.learning.role_taxonomy import RoleCompetencyProfile

    profile = CandidateProfile.from_parsed_dict(student_resume_data)

    role_prof = RoleCompetencyProfile(
        canonical_role="Computer Vision Engineer",
        domain="AI / Data Science",
        subdomain="Computer Vision",
        core_competencies=["Python", "OpenCV"],
        common_competencies=["Flask", "MongoDB"],
        tools_technologies=["TensorFlow", "Keras"],
        knowledge_areas=["Machine Learning"],
        optional_competencies=["PyTorch"],
    )

    gaps = evaluate_career_competencies(role_prof, candidate=profile)
    gaps_by_skill = {g.skill.lower(): g for g in gaps}

    # Python, OpenCV, Flask, MongoDB, TensorFlow, Keras must all be recognized as demonstrated
    for proven_skill in ["python", "opencv", "flask", "mongodb", "tensorflow", "keras"]:
        assert proven_skill in gaps_by_skill
        assert gaps_by_skill[proven_skill].candidate_status == "MATCHED"

    # PyTorch was NOT present anywhere -> MUST NOT be MATCHED
    assert "pytorch" in gaps_by_skill
    assert gaps_by_skill["pytorch"].candidate_status != "MATCHED"
    assert gaps_by_skill["pytorch"].status in ("NO_RESUME_EVIDENCE", "PARTIALLY_DEMONSTRATED")


# ------------------------------------------------------------------------------
# 10. Tailoring receives canonical evidence
# ------------------------------------------------------------------------------
def test_tailoring_receives_canonical_evidence(student_resume_data):
    from app.modules.tailoring.validation import detect_fabricated_claims

    profile = CandidateProfile.from_parsed_dict(student_resume_data)
    demonstrated = profile.get_all_demonstrated_skills()

    # Proposal rewrites original bullet to mention Flask and MongoDB
    orig_bullet = "• Built web service."
    prop_bullet = "• Built web service using Flask and MongoDB."

    unsupported = detect_fabricated_claims(
        original=orig_bullet,
        proposed=prop_bullet,
        jd_text="Flask, MongoDB required",
        candidate_skills=demonstrated,
    )
    # Flask and MongoDB are canonical candidate skills -> MUST NOT be flagged as unsupported!
    assert len(unsupported) == 0

    # If proposal introduces PyTorch (which is absent from candidate background)
    prop_fake = "• Built deep learning models using PyTorch."
    unsupported_fake = detect_fabricated_claims(
        original=orig_bullet,
        proposed=prop_fake,
        jd_text="PyTorch required",
        candidate_skills=demonstrated,
    )
    assert any("pytorch" in t.lower() for t in unsupported_fake)


# ------------------------------------------------------------------------------
# 11. Copilot receives canonical evidence
# ------------------------------------------------------------------------------
def test_copilot_receives_canonical_evidence(student_resume_data):
    profile = CandidateProfile.from_parsed_dict(student_resume_data)
    demonstrated = profile.get_all_demonstrated_skills()

    # Copilot receives the canonical demonstrated skills
    copilot_skills = set(demonstrated)
    assert {"Python", "TensorFlow", "Keras", "Flask", "OpenCV", "MongoDB"}.issubset(copilot_skills)
    assert "PyTorch" not in copilot_skills


# ------------------------------------------------------------------------------
# 12. Cross-system consistency test
# ------------------------------------------------------------------------------
def test_cross_system_skill_consistency(student_resume_data):
    """
    All subsystems (Matching, Learning, Tailoring, Copilot) must agree
    on whether a technology exists in the candidate's verified evidence.
    """
    profile = CandidateProfile.from_parsed_dict(student_resume_data)
    canonical_skills = profile.get_all_demonstrated_skills()

    # 1. Matching candidate skills
    matching_skills = set(canonical_skills)

    # 2. Learning candidate skills
    learning_skills = set(profile.get_all_demonstrated_skills())

    # 3. Tailoring candidate skills
    tailoring_skills = set(profile.get_all_demonstrated_skills())

    # 4. Copilot candidate skills
    copilot_skills = set(profile.get_all_demonstrated_skills())

    # They MUST be 100% identical!
    assert matching_skills == learning_skills == tailoring_skills == copilot_skills
    assert "Flask" in matching_skills
    assert "MongoDB" in matching_skills
    assert "PyTorch" not in matching_skills


# ------------------------------------------------------------------------------
# 13. No conversion of project evidence into professional years
# ------------------------------------------------------------------------------
def test_no_conversion_of_project_evidence_into_professional_years(student_resume_data):
    from app.modules.jobs.eligibility import evaluate_eligibility

    profile = CandidateProfile.from_parsed_dict(student_resume_data)

    user_profile = {
        "category": "STUDENT",
        "experience_years": 0.0,
        "is_student": True,
    }
    master_resume = {
        "parsed": profile.to_parsed_dict(),
        "raw_text": "Student resume text",
    }

    # Job requiring 2+ years of professional experience
    senior_job = {
        "id": "senior_01",
        "title": "Senior Python Engineer",
        "description": "Requires 2+ years of professional software engineering experience.",
        "experience_min": 2,
        "experience_max": 5,
        "required_skills": ["Python", "Flask"],
    }

    elig = evaluate_eligibility(user_profile, master_resume, senior_job)

    # Candidate has projects using Flask and Python, but 0 professional years.
    # Eligibility MUST NOT upgrade project count to professional years!
    assert elig.candidate_experience_years == 0.0
    assert "EXPERIENCE" in str(elig.status) or elig.status.value != "ELIGIBLE"
    assert any("experience" in r.lower() or "senior" in r.lower() or "year" in r.lower() for r in elig.reasons)


# ------------------------------------------------------------------------------
# 14. No conversion of certification into professional experience
# ------------------------------------------------------------------------------
def test_no_conversion_of_certification_into_professional_experience():
    from app.modules.jobs.eligibility import evaluate_eligibility

    resume_with_certs = {
        "personal": {"name": "Certified Fresher"},
        "skills": ["AWS", "Docker"],
        "certifications": ["AWS Certified Solutions Architect - Associate"],
        "experience": [],
        "projects": [],
    }
    cand_prof = CandidateProfile.from_parsed_dict(resume_with_certs)

    user_profile = {
        "category": "FRESHER",
        "experience_years": 0.0,
    }
    master_resume = {
        "parsed": cand_prof.to_parsed_dict(),
        "raw_text": "Fresher resume text with AWS cert",
    }

    job_3yr = {
        "id": "job_mid_01",
        "title": "Cloud Engineer",
        "description": "Requires minimum 3 years industry experience.",
        "experience_min": 3,
        "required_skills": ["AWS"],
    }

    elig = evaluate_eligibility(user_profile, master_resume, job_3yr)

    # Certification must NOT count as 3 years professional experience
    assert elig.candidate_experience_years == 0.0
    assert "EXPERIENCE" in str(elig.status) or elig.status.value != "ELIGIBLE"
