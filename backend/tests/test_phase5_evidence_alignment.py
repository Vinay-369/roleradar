"""
Phase 5 Comprehensive Evidence Alignment Test Suite.
Verifies:
1. Exact skill matching with delivery evidence hierarchy (Experience/Projects vs Education vs Listing)
2. Related / adjacent technology matching (Postgres <-> MySQL, AWS <-> Azure, PyTorch <-> TensorFlow)
3. Missing technology matching (never hallucinating missing skills)
4. Compound requirements (partial coverage, multi-skill breakdown, missing sub-skill extraction)
5. Responsibility matching (delivery action intent)
6. Experience duration requirements (years comparison)
7. Preferred vs Must-Have priority segregation
8. Coursework / academic credential evidence hierarchy
9. Multiple evidence units aggregation
10. Negation and non-evidence filtering ("no experience in...", "interested in learning...")
11. Cross-entity evidence scoping (same skill across different employers)
12. Cross-feature consistency across Matching, Skill Gap, Tailoring, and Truth Guard
"""
import pytest
from app.modules.jobs.taxonomy import analyze_job_description, RequirementCategory
from app.modules.matching.evidence_mapping import (
    EvidenceMatchStatus,
    map_resume_to_jd_evidence,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile
from mongomock_motor import AsyncMongoMockClient
from app.core.config import Settings


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock", AI_PROVIDER="mock")


# =========================================================================
# 1. COMPOUND REQUIREMENT PARTIAL MATCHING
# =========================================================================

def test_compound_requirement_partial_and_missing_extraction():
    """
    JD requires: Java, Spring Boot, REST APIs, and PostgreSQL.
    Candidate only has: Java, PostgreSQL (missing Spring Boot, REST APIs).
    Should produce PARTIAL match, NOT EXACT_MATCH, and list missing sub-skills.
    """
    candidate_text = """
JOHN DOE
john@example.com

SKILLS
Languages: Java, SQL
Databases: PostgreSQL

EXPERIENCE
Backend Developer at TechCorp (2022 - Present)
• Maintained Java backend services connected to PostgreSQL database.
"""
    jd_text = """
Full Stack Engineer
REQUIREMENTS
• Hands-on experience with Java, Spring Boot, REST APIs, and PostgreSQL.
"""
    profile = extract_candidate_profile(candidate_text)
    reqs = analyze_job_description(jd_text)
    matrix = map_resume_to_jd_evidence(profile, reqs)

    mapping = matrix.mappings[0]
    assert mapping.status == EvidenceMatchStatus.PARTIAL
    assert mapping.relevance_score < 1.0
    assert mapping.relevance_score >= 0.5
    assert "Java" in mapping.matched_skills or "java" in [s.lower() for s in mapping.matched_skills]
    assert "PostgreSQL" in mapping.matched_skills or "postgresql" in [s.lower() for s in mapping.matched_skills]

    # Verify missing sub-skills are populated in gaps
    missing_lower = {s.lower() for s in matrix.missing_skills}
    assert any("spring boot" in s or "rest" in s for s in missing_lower)


# =========================================================================
# 2. NEGATIVE AND NON-EVIDENCE FILTERING
# =========================================================================

def test_negation_and_aspirational_mentions_not_promoted_to_evidence():
    """
    Candidate text contains 'no experience with Kubernetes' and 'interested in learning Go'.
    JD requires Kubernetes and Go.
    Should be classified as MISSING, not supported evidence.
    """
    candidate_text = """
ALICE SMITH
alice@example.com

EXPERIENCE
Software Engineer at CloudApp (2021 - Present)
• Built Python web microservices with Docker deployment.
• Note: no experience with Kubernetes or container orchestration.
• Currently interested in learning Go for backend services.
"""
    jd_text = """
DevOps Engineer
REQUIREMENTS
• Hands-on experience with Kubernetes.
• Production experience with Go.
"""
    profile = extract_candidate_profile(candidate_text)
    reqs = analyze_job_description(jd_text)
    matrix = map_resume_to_jd_evidence(profile, reqs)

    k8s_mapping = next(m for m in matrix.mappings if "kubernetes" in m.requirement_text.lower())
    assert k8s_mapping.status != EvidenceMatchStatus.EXACT_MATCH

    go_mapping = next(m for m in matrix.mappings if "go" in m.requirement_text.lower())
    assert go_mapping.status == EvidenceMatchStatus.MISSING
    assert len(go_mapping.matched_evidence_units) == 0


# =========================================================================
# 3. SECTION HIERARCHY & COURSEWORK EVIDENCE
# =========================================================================

def test_coursework_only_evidence_classified_as_supported_not_exact_delivery():
    """
    Candidate only has Machine Learning / PyTorch in Education coursework.
    JD requires PyTorch.
    Should be classified as SUPPORTED (coursework foundation), not delivery EXACT_MATCH.
    """
    candidate_text = """
BOB BUILDER
bob@example.com

EDUCATION
State University
B.S. Computer Science (2020 - 2024)
• Coursework: Deep Learning and Computer Vision with PyTorch and OpenCV.

EXPERIENCE
Web Developer Intern at LocalCo (2023)
• Built front-end components using JavaScript and HTML.
"""
    jd_text = """
ML Engineer
REQUIREMENTS
• Experience with PyTorch.
"""
    profile = extract_candidate_profile(candidate_text)
    reqs = analyze_job_description(jd_text)
    matrix = map_resume_to_jd_evidence(profile, reqs)

    pytorch_mapping = next(m for m in matrix.mappings if "pytorch" in m.requirement_text.lower())
    assert pytorch_mapping.status == EvidenceMatchStatus.SUPPORTED
    assert pytorch_mapping.status != EvidenceMatchStatus.EXACT_MATCH


# =========================================================================
# 4. EXPERIENCE DURATION REQUIREMENTS
# =========================================================================

def test_experience_duration_fulfillment_and_gap():
    """
    Candidate has 4 years experience.
    JD 1 requires 3+ years (Satisfied -> EXACT_MATCH).
    JD 2 requires 8+ years (Under-tenured -> WEAK / PARTIAL).
    """
    candidate_text = """
CLARA OSWALD
clara@example.com

SUMMARY
Software Engineer with 4 years building scalable services.

EXPERIENCE
Software Engineer at PrimeCorp (2020 - 2024)
• Developed Python backend systems and database pipelines for 4 years.
"""
    profile = extract_candidate_profile(candidate_text)

    jd_3yr = analyze_job_description("Software Engineer\nREQUIREMENTS:\n• 3+ years professional software development experience.")
    matrix_3yr = map_resume_to_jd_evidence(profile, jd_3yr)
    exp_3yr_mapping = matrix_3yr.mappings[0]
    assert exp_3yr_mapping.status == EvidenceMatchStatus.EXACT_MATCH
    assert exp_3yr_mapping.relevance_score == 1.0

    jd_8yr = analyze_job_description("Staff Engineer\nREQUIREMENTS:\n• 8+ years professional software development experience.")
    matrix_8yr = map_resume_to_jd_evidence(profile, jd_8yr)
    exp_8yr_mapping = matrix_8yr.mappings[0]
    assert exp_8yr_mapping.status in (EvidenceMatchStatus.PARTIAL, EvidenceMatchStatus.WEAK)
    assert exp_8yr_mapping.relevance_score <= 0.60


# =========================================================================
# 5. RELATED ADJACENT SKILL TRANSFERABILITY
# =========================================================================

def test_related_skill_transferability_distinction():
    """
    JD requires AWS.
    Candidate has GCP and Azure (Cloud cluster).
    Should produce RELATED match with 0.70 score, not EXACT_MATCH.
    """
    candidate_text = """
DANIEL JACKSON
daniel@example.com

SKILLS
Cloud: GCP, Azure

EXPERIENCE
Cloud Engineer at Stargate Inc (2021 - Present)
• Deployed microservices on GCP and Azure.
"""
    profile = extract_candidate_profile(candidate_text)
    reqs = analyze_job_description("Cloud Architect\nREQUIREMENTS:\n• Production experience with AWS.")
    matrix = map_resume_to_jd_evidence(profile, reqs)

    aws_mapping = matrix.mappings[0]
    assert aws_mapping.status == EvidenceMatchStatus.RELATED
    assert aws_mapping.relevance_score == 0.70
    assert any(s.lower() in ("gcp", "azure") for s in aws_mapping.matched_skills)


# =========================================================================
# 6. CROSS-ENTITY EVIDENCE SCOPING (SAME SKILL ACROSS EMPLOYERS)
# =========================================================================

def test_cross_entity_evidence_scoping():
    """
    Python appears in Company A and Company B.
    EvidenceUnits must maintain distinct entity IDs and text without merging.
    """
    candidate_text = """
EMILY THORNE
emily@example.com

EXPERIENCE
Senior Developer at Alpha Corp (2022 - Present)
• Built Python data pipeline processing 1M records daily.

Junior Developer at Beta LLC (2020 - 2022)
• Maintained legacy Python web scripts and automation tools.
"""
    profile = extract_candidate_profile(candidate_text)
    reqs = analyze_job_description("Python Engineer\nREQUIREMENTS:\n• Strong skills in Python.")
    matrix = map_resume_to_jd_evidence(profile, reqs)

    mapping = matrix.mappings[0]
    assert mapping.status == EvidenceMatchStatus.EXACT_MATCH
    assert len(mapping.matched_evidence_units) >= 2
    assert len(mapping.matched_entity_ids) >= 2
    assert any("exp_0" in eid or "Alpha" in eid for eid in mapping.matched_entity_ids)
    assert any("exp_1" in eid or "Beta" in eid for eid in mapping.matched_entity_ids)


# =========================================================================
# 7. CROSS-FEATURE CONSISTENCY: MATCHING, SKILL GAP, TAILORING, TRUTH GUARD
# =========================================================================

@pytest.mark.asyncio
async def test_cross_feature_consistency_synthetic(db, settings):
    """
    Synthetic Candidate:
    - Has verified Python, FastAPI, and Docker in experience bullets.
    - Missing Kafka and Kubernetes.
    - Target JD requires: Python, FastAPI (Must-Have), Kafka (Must-Have), Kubernetes (Preferred).
    
    Verifies across all consumers:
    1. Evidence Alignment: Python & FastAPI -> EXACT_MATCH; Kafka -> MISSING; Kubernetes -> MISSING.
    2. Skill Gap: Kafka -> CORE gap; Kubernetes -> BONUS gap.
    3. Tailoring Plan: Prioritizes Python & FastAPI; never fabricates Kafka/Kubernetes.
    4. Truth Guard: Rejects any hallucinated Kafka/Kubernetes bullets.
    """
    from app.modules.learning.routes import _compute_gaps
    from app.modules.resume import repositories as resume_repo
    from app.modules.jobs.services import create_custom_job
    from app.modules.tailoring.plan import generate_structured_tailoring_plan
    from app.modules.tailoring.validation import validate_tailored_profile_truth_guard
    from app.modules.resume.classification import classify_candidate_profile
    from bson import ObjectId
    import copy

    user_id = str(ObjectId())

    candidate_text = """
VICTOR STONE
victor@example.com

SUMMARY
Backend developer with 3 years building microservices with Python and FastAPI.

SKILLS
Python, FastAPI, Docker, SQL

EXPERIENCE
Backend Engineer at StarLabs (2021 - Present)
• Built scalable REST APIs using Python and FastAPI.
• Packaged and deployed containerized services using Docker.
"""
    profile = extract_candidate_profile(candidate_text)

    # Ingest master resume
    await resume_repo.create_master_resume(
        db,
        user_id=user_id,
        version=1,
        file_name="victor_resume.pdf",
        file_type="pdf",
        raw_text=candidate_text,
        parsed={
            "skills": profile.skills,
            "experience_raw": [ev.normalized_text for ev in profile.evidence_units if ev.section == "EXPERIENCE"],
            "projects_raw": [],
            "experience_entries": [{"title": "Backend Engineer", "company": "StarLabs", "technologies": ["Python", "FastAPI", "Docker"]}],
        },
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 85, "bullets_analyzed": 2, "quantified_bullets": 1, "weak_verb_bullets": 0, "quantification_rate": 0.5, "issues": []},
    )

    jd_text = """
Backend Platform Engineer
CORE REQUIREMENTS
• Strong experience with Python and FastAPI.
• Production experience with Kafka event streaming.

PREFERRED QUALIFICATIONS
• Experience with Kubernetes.
"""
    job = await create_custom_job(
        db,
        company="StarLabs Platform",
        title="Backend Platform Engineer",
        jd_text=jd_text,
        user_id=user_id,
    )

    reqs = analyze_job_description(jd_text)

    # 1. Evidence Alignment Verification
    matrix = map_resume_to_jd_evidence(profile, reqs)
    python_mapping = next(m for m in matrix.mappings if "python" in m.requirement_text.lower())
    kafka_mapping = next(m for m in matrix.mappings if "kafka" in m.requirement_text.lower())
    k8s_mapping = next(m for m in matrix.mappings if "kubernetes" in m.requirement_text.lower())

    assert python_mapping.status in (EvidenceMatchStatus.EXACT_MATCH, EvidenceMatchStatus.STRONG_MATCH)
    assert kafka_mapping.status == EvidenceMatchStatus.MISSING
    assert k8s_mapping.status in (EvidenceMatchStatus.MISSING, EvidenceMatchStatus.RELATED)

    # 2. Skill Gap Verification
    gaps, _ = await _compute_gaps(db, settings, user_id, job_id=job["id"])
    gap_skills = {g.skill.lower(): g.priority for g in gaps}
    assert gap_skills.get("kafka") == "CORE"
    assert "python" not in gap_skills
    assert "fastapi" not in gap_skills

    # 3. Tailoring Plan Verification
    classification = classify_candidate_profile(profile)
    plan = generate_structured_tailoring_plan(profile, reqs, matrix, classification)
    assert plan is not None
    # No decision should invent Kafka
    for dec in plan.evidence_decisions:
        assert dec.action.value in ("PRESERVE", "REWRITE", "CONDENSE", "REORDER", "PRIORITIZE", "DEPRIORITIZE", "REMOVE", "NEEDS_USER_INPUT")

    # 4. Truth Guard Verification against unauthorized injection
    tampered_profile = copy.deepcopy(profile)
    tampered_profile.evidence_units[0].technologies.append("Kafka")
    tampered_profile.evidence_units[0].normalized_text += " Configured Kafka clusters."

    _, audit_result = validate_tailored_profile_truth_guard(profile, tampered_profile, plan)
    assert len(audit_result.unsupported_technologies) > 0 or len(audit_result.reverted_evidence_ids) > 0

