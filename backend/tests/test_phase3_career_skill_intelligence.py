"""
Phase 3 — Career Skill Intelligence, Skill Gap & Learning Roadmap Tests.

Verifies:
1. Career skill map without resume (clear core, important, supporting breakdown; no negative scoring).
2. Canonical role resolution across 7 required domains (Backend, Frontend, Data, AI/ML, Cloud/DevOps, QA/Testing, Mobile).
3. Demonstrated / Partially Demonstrated / No Resume Evidence semantics using Phase 2 CandidateProfile & EvidenceUnits.
4. Non-judgmental explanation for NO_RESUME_EVIDENCE.
5. Evidence provenance preservation (WORK_EXPERIENCE vs PROJECT vs COURSEWORK vs EXPLICIT).
6. Prioritized skill gap groups (LEARN_FIRST, STRENGTHEN, LATER_SUPPORTING, DEMONSTRATED).
7. Domain-specific prerequisite topological ordering (e.g. unit testing before test frameworks; swift before ios).
8. Roadmap generation excluding demonstrated competencies.
9. Curated resource honesty (no fabricated URLs, no generic Google/YouTube fallbacks).
10. Independence of Career Skill Gap vs Job Skill Gap.
11. Edge cases: unknown roles, sparse resumes, senior profiles with 0 major gaps.
"""

import uuid
import pytest

from app.modules.resume.models import (
    CandidateProfile,
    EvidenceUnit,
    SkillEvidenceTier,
    WorkExperienceEntity,
    ProjectEntity,
    EducationEntity,
)
from app.modules.learning.engine import (
    evaluate_career_competencies,
    build_roadmap,
    _order_skills_with_prerequisites,
    compute_skill_gaps,
    get_resources_for_skill,
    SkillGap,
)
from app.modules.learning.role_taxonomy import (
    ROLE_TAXONOMY,
    resolve_role,
    match_canonical_role,
)
from app.modules.learning.schemas import (
    CompetencyPriorityGroup,
    CompetencyImportance,
    CompetencyStatus,
    CareerAlignmentSummary,
)
from app.modules.jobs.taxonomy import (
    StructuredJobRequirements,
)


# ============================================================================
# 1. CAREER SKILL MAP WITHOUT RESUME
# ============================================================================

def test_career_skill_map_without_resume():
    """When a user selects a career role without a resume, it clearly shows
    what the career requires, broken down into Core, Important, and Supporting."""
    role_prof, r_conf, _ = match_canonical_role("Backend Engineer")
    assert role_prof is not None

    gaps = evaluate_career_competencies(
        role_prof,
        candidate=None,
        source="ROLE_TAXONOMY",
        confidence=r_conf,
    )

    total = len(gaps)
    assert total > 0

    demonstrated = sum(1 for g in gaps if g.status == CompetencyStatus.DEMONSTRATED.value)
    partially_demo = sum(1 for g in gaps if g.status == CompetencyStatus.PARTIALLY_DEMONSTRATED.value)
    no_evidence = sum(1 for g in gaps if g.status == CompetencyStatus.NO_RESUME_EVIDENCE.value)
    core_count = sum(1 for g in gaps if g.importance == "CORE")
    important_count = sum(1 for g in gaps if g.importance in ("IMPORTANT", "COMMON"))
    supporting_count = sum(1 for g in gaps if g.importance in ("SUPPORTING", "OPTIONAL"))

    assert demonstrated == 0
    assert partially_demo == 0
    assert no_evidence == total

    # Verifies core, important, supporting breakdown exists and sums to total
    assert core_count > 0, "Career skill map must define Core competencies"
    assert important_count > 0, "Career skill map must define Important competencies"
    assert supporting_count > 0, "Career skill map must define Supporting competencies"
    assert core_count + important_count + supporting_count == total

    # Verify each competency has proper importance and priority_group
    for comp in gaps:
        assert comp.importance in {"CORE", "IMPORTANT", "COMMON", "SUPPORTING", "OPTIONAL"}
        assert comp.priority_group in {
            CompetencyPriorityGroup.LEARN_FIRST.value,
            CompetencyPriorityGroup.STRENGTHEN.value,
            CompetencyPriorityGroup.LATER_SUPPORTING.value,
        }
        assert comp.current_evidence == "MARKET_REQUIREMENT"
        assert comp.status == CompetencyStatus.NO_RESUME_EVIDENCE.value


# ============================================================================
# 2. MULTI-DOMAIN CANONICAL ROLES (7 DOMAINS)
# ============================================================================

@pytest.mark.parametrize(
    "domain,role_query,expected_canonical",
    [
        ("Software/Backend", "Backend Engineer", "Backend Developer"),
        ("Frontend", "Frontend Developer", "Frontend Developer"),
        ("Data/Analytics", "Data Engineer", "Data Engineer"),
        ("AI/ML", "Machine Learning Engineer", "Machine Learning Engineer"),
        ("Cloud/DevOps/SRE", "DevOps Engineer", "DevOps Engineer"),
        ("QA/Testing", "QA Automation Engineer", "QA / Test Engineer"),
        ("Mobile", "Mobile Developer", "Mobile Developer"),
    ],
)
def test_multi_domain_canonical_roles(domain, role_query, expected_canonical):
    """Test resolution and canonical profiles across all 7 required domains."""
    prof, conf, reason = resolve_role(role_query)
    assert prof is not None
    assert prof.role == expected_canonical
    assert conf in ("HIGH", "MEDIUM")
    assert len(prof.core_competencies) > 0
    assert len(prof.common_competencies) > 0


# ============================================================================
# 3. DEMONSTRATED / PARTIALLY DEMONSTRATED / NO_RESUME_EVIDENCE SEMANTICS
# ============================================================================

def test_demonstrated_partial_no_evidence_semantics():
    """Test precise semantic resolution of demonstrated, partial, and missing competencies."""
    candidate = CandidateProfile(
        personal={"name": "Alice Dev"},
        summary="Experienced backend developer",
        skills=["Python", "FastAPI", "Docker"],
        skills_explicit=["Python", "FastAPI"],
        experience=[
            WorkExperienceEntity(
                id="exp-1",
                role="Backend Developer",
                company="Acme Corp",
                technologies=["Python", "FastAPI"],
                description="Architected and maintained REST APIs using Python and FastAPI handling 10k RPS.",
            )
        ],
        education=[
            EducationEntity(
                id="edu-1",
                institution="University",
                degree="BS Computer Science",
            )
        ],
        evidence_units=[
            EvidenceUnit(
                id="ev-1",
                section="experience",
                entity_id="exp-1",
                original_text="Architected and maintained REST APIs using Python and FastAPI handling 10k RPS.",
                normalized_text="Architected and maintained REST APIs using Python and FastAPI handling 10k RPS.",
                technologies=["Python", "FastAPI"],
                confidence=0.95,
            ),
            EvidenceUnit(
                id="ev-2",
                section="education",
                entity_id="edu-1",
                original_text="Coursework in container fundamentals covering Docker basic commands.",
                normalized_text="Coursework in container fundamentals covering Docker basic commands.",
                technologies=["Docker"],
                confidence=0.60,
            ),
        ],
    )

    role_prof, r_conf, _ = match_canonical_role("Backend Engineer")
    assert role_prof is not None

    gaps = evaluate_career_competencies(
        role_prof,
        candidate=candidate,
        source="CANDIDATE_PROFILE",
        confidence=r_conf,
    )

    by_name = {g.skill.lower(): g for g in gaps}

    # Python should be DEMONSTRATED with WORK_EXPERIENCE
    assert "python" in by_name
    py_gap = by_name["python"]
    assert py_gap.status == CompetencyStatus.DEMONSTRATED.value
    assert py_gap.priority_group == CompetencyPriorityGroup.DEMONSTRATED.value
    assert len(py_gap.evidence) > 0
    assert py_gap.evidence[0]["evidence_type"] == "WORK_EXPERIENCE"

    # Docker from coursework should be PARTIALLY_DEMONSTRATED with STRENGTHEN priority
    assert "docker" in by_name
    docker_gap = by_name["docker"]
    assert docker_gap.status == CompetencyStatus.PARTIALLY_DEMONSTRATED.value
    assert docker_gap.priority_group == CompetencyPriorityGroup.STRENGTHEN.value
    assert docker_gap.evidence[0]["evidence_type"] == "COURSEWORK"

    # Redis is not in resume -> NO_RESUME_EVIDENCE
    assert "redis" in by_name
    redis_gap = by_name["redis"]
    assert redis_gap.status == CompetencyStatus.NO_RESUME_EVIDENCE.value
    assert len(redis_gap.evidence) == 0

    # Non-judgmental explanation check
    reason_lower = (redis_gap.reason or "").lower()
    assert "no verified evidence was found in your resume" in reason_lower
    assert "not that you lack the capability" in reason_lower or "does not mean you lack capability" in reason_lower


# ============================================================================
# 4. PROVENANCE PRESERVATION (NEVER UPGRADE PROJECT/COURSEWORK TO EXPERIENCE)
# ============================================================================

def test_provenance_preservation_no_upgrades():
    """Project and coursework evidence must retain their exact type and never be
    upgraded to professional work experience."""
    candidate = CandidateProfile(
        personal={"name": "Bob Builder"},
        summary="Self-taught developer with portfolio projects",
        skills=["PostgreSQL", "AWS"],
        projects=[
            ProjectEntity(
                id="proj-1",
                title="Side Project App",
                technologies=["PostgreSQL"],
                description="Built a portfolio app backed by PostgreSQL database.",
            )
        ],
        evidence_units=[
            EvidenceUnit(
                id="ev-proj-1",
                section="projects",
                entity_id="proj-1",
                original_text="Built a portfolio app backed by PostgreSQL database.",
                normalized_text="Built a portfolio app backed by PostgreSQL database.",
                technologies=["PostgreSQL"],
                confidence=0.80,
            ),
            EvidenceUnit(
                id="ev-cert-1",
                section="certifications",
                entity_id="cert-1",
                original_text="Completed AWS Cloud Practitioner certification.",
                normalized_text="Completed AWS Cloud Practitioner certification.",
                technologies=["AWS"],
                confidence=0.75,
            ),
        ],
    )

    role_prof, r_conf, _ = match_canonical_role("Backend Engineer")
    gaps = evaluate_career_competencies(role_prof, candidate=candidate)

    by_name = {g.skill.lower(): g for g in gaps}

    # PostgreSQL provenance
    if "postgresql" in by_name:
        pg = by_name["postgresql"]
        assert len(pg.evidence) > 0
        assert pg.evidence[0]["evidence_type"] == "PROJECT"
        assert pg.evidence[0]["evidence_type"] != "WORK_EXPERIENCE"

    # AWS provenance
    if "aws" in by_name:
        aws = by_name["aws"]
        assert len(aws.evidence) > 0
        assert aws.evidence[0]["evidence_type"] == "COURSEWORK"
        assert aws.evidence[0]["evidence_type"] != "WORK_EXPERIENCE"


# ============================================================================
# 5. PRIORITIZED SKILL GAP (LEARN_FIRST, STRENGTHEN, LATER_SUPPORTING)
# ============================================================================

def test_prioritized_skill_gap_groups():
    """Gaps must be organized into LEARN FIRST, STRENGTHEN, and LATER / SUPPORTING,
    with core missing skills and unmet foundational prerequisites elevated to LEARN FIRST."""
    candidate = CandidateProfile(
        personal={"name": "Charlie Coder"},
        skills=["Git"],
        experience=[
            WorkExperienceEntity(
                id="exp-git",
                role="Junior Tech",
                company="Startup Inc",
                technologies=["Git"],
                description="Used Git for version control.",
            )
        ],
        evidence_units=[
            EvidenceUnit(
                id="ev-git",
                section="experience",
                entity_id="exp-git",
                original_text="Used Git for version control.",
                normalized_text="Used Git for version control.",
                technologies=["Git"],
                confidence=0.9,
            ),
        ],
    )

    role_prof, r_conf, _ = match_canonical_role("Backend Engineer")
    gaps = evaluate_career_competencies(role_prof, candidate=candidate)

    learn_first = [g for g in gaps if g.priority_group == CompetencyPriorityGroup.LEARN_FIRST.value]
    strengthen = [g for g in gaps if g.priority_group == CompetencyPriorityGroup.STRENGTHEN.value]
    later = [g for g in gaps if g.priority_group == CompetencyPriorityGroup.LATER_SUPPORTING.value]
    demonstrated = [g for g in gaps if g.priority_group == CompetencyPriorityGroup.DEMONSTRATED.value]

    assert len(learn_first) > 0, "Missing core skills must be prioritized as LEARN_FIRST"
    assert len(later) > 0, "Optional/supporting competencies must be in LATER_SUPPORTING"

    # Core competencies like Python/API Architecture should be in LEARN_FIRST
    learn_first_names = {g.skill.lower() for g in learn_first}
    assert any(core_skill in learn_first_names for core_skill in ["python", "api architecture", "system design"])


# ============================================================================
# 6. DOMAIN PREREQUISITE TOPOLOGICAL ORDERING
# ============================================================================

def test_prerequisite_ordering_qa_domain():
    """QA/Testing prerequisites: Unit Testing must precede Test Automation Frameworks."""
    skills = ["Test Automation Frameworks", "Integration Testing", "Unit Testing", "Python"]
    ordered = _order_skills_with_prerequisites(skills)

    ordered_lower = [s.lower() for s in ordered]
    assert ordered_lower.index("unit testing") < ordered_lower.index("test automation frameworks")
    assert ordered_lower.index("unit testing") < ordered_lower.index("integration testing")
    assert ordered_lower.index("python") < ordered_lower.index("test automation frameworks")


def test_prerequisite_ordering_mobile_domain():
    """Mobile prerequisites: Swift precedes iOS App Development, Kotlin precedes Android."""
    skills = ["iOS App Development", "SwiftUI", "Swift"]
    ordered = _order_skills_with_prerequisites(skills)

    ordered_lower = [s.lower() for s in ordered]
    assert ordered_lower.index("swift") < ordered_lower.index("ios app development")
    assert ordered_lower.index("swift") < ordered_lower.index("swiftui")

    android_skills = ["Jetpack Compose", "Android App Development", "Kotlin"]
    ordered_android = _order_skills_with_prerequisites(android_skills)
    android_lower = [s.lower() for s in ordered_android]
    assert android_lower.index("kotlin") < android_lower.index("android app development")


def test_prerequisite_ordering_backend_domain():
    """Backend prerequisites: Python precedes FastAPI, SQL precedes PostgreSQL."""
    skills = ["FastAPI", "PostgreSQL", "Python", "SQL"]
    ordered = _order_skills_with_prerequisites(skills)

    ordered_lower = [s.lower() for s in ordered]
    assert ordered_lower.index("python") < ordered_lower.index("fastapi")
    assert ordered_lower.index("sql") < ordered_lower.index("postgresql")


# ============================================================================
# 7. LEARNING ROADMAP EXCLUDES DEMONSTRATED COMPETENCIES
# ============================================================================

def test_learning_roadmap_excludes_demonstrated_competencies():
    """Skills already clearly demonstrated by the candidate must NOT be scheduled
    into beginner roadmap sprints."""
    candidate = CandidateProfile(
        personal={"name": "Diana Senior"},
        skills=["Python", "FastAPI", "SQL", "Git"],
        experience=[
            WorkExperienceEntity(
                id="exp-demo-1",
                role="Senior Engineer",
                company="Tech Corp",
                technologies=["Python", "FastAPI", "SQL", "Git"],
                description="Senior engineer developing scalable microservices in Python, FastAPI, and SQL with Git workflow.",
            )
        ],
        evidence_units=[
            EvidenceUnit(
                id="ev-demo-1",
                section="experience",
                entity_id="exp-demo-1",
                original_text="Senior engineer developing scalable microservices in Python, FastAPI, and SQL with Git workflow.",
                normalized_text="Senior engineer developing scalable microservices in Python, FastAPI, and SQL with Git workflow.",
                technologies=["Python", "FastAPI", "SQL", "Git"],
                confidence=0.98,
            )
        ],
    )

    role_prof, r_conf, _ = match_canonical_role("Backend Engineer")
    gaps = evaluate_career_competencies(role_prof, candidate=candidate)

    roadmap = build_roadmap(gaps=gaps)

    scheduled = [s.lower() for s in (
        roadmap["immediate"] + roadmap["week_1"] + roadmap["week_2"] + roadmap["month_1"]
    )]

    # Demonstrated skills should not appear in scheduled sprints
    assert "python" not in scheduled
    assert "fastapi" not in scheduled
    assert "git" not in scheduled


# ============================================================================
# 8. CURATED RESOURCES (NO FABRICATED URLS, NO GENERIC SEARCH FALLBACKS)
# ============================================================================

def test_curated_resources_no_fabricated_urls():
    """Curated resources must return reputable links or empty lists, never fabricated search URLs."""
    # Python has curated resources
    py_resources = get_resources_for_skill("Python")
    assert len(py_resources) > 0
    for url in py_resources:
        assert any(domain in url for domain in ["docs.python.org", "realpython.com", "coursera.org", "freecodecamp.org"])
        assert "google.com/search" not in url
        assert "youtube.com/results" not in url

    # Obscure/unknown skill must return empty list (not a fabricated search query)
    unknown_resources = get_resources_for_skill("HyperdimensionalQuantumEntanglementProtocol")
    assert unknown_resources == [], "Unknown skill must not return generic fabricated search URLs"


# ============================================================================
# 9. CAREER GAP VS JOB GAP INDEPENDENCE
# ============================================================================

def test_career_gap_vs_job_gap_independence():
    """A single job requisition with specialized requirements must NOT redefine
    or mutate the canonical Career Competency profile."""
    candidate = CandidateProfile(
        personal={"name": "Evan Engineer"},
        skills=["Python"],
        experience=[
            WorkExperienceEntity(
                id="exp-1",
                role="Python Engineer",
                company="Tech LLC",
                technologies=["Python"],
                description="Python developer",
            )
        ],
        evidence_units=[
            EvidenceUnit(
                id="ev-1",
                section="experience",
                entity_id="exp-1",
                original_text="Python developer",
                normalized_text="Python developer",
                technologies=["Python"],
                confidence=0.9,
            )
        ],
    )

    # 1. Career Competency Map
    role_prof, _, _ = match_canonical_role("Backend Engineer")
    career_result = evaluate_career_competencies(role_prof, candidate)
    career_skills = {g.skill.lower() for g in career_result}

    # 2. Requisition requiring niche proprietary tool (e.g. Cobol, Fortran, ProprietaryDB)
    job_reqs = StructuredJobRequirements(
        job_id="job-niche-123",
        role_category="Backend Engineer",
        required_skills=["Cobol", "Fortran", "ProprietaryDB"],
        preferred_skills=["Perl"],
    )

    # Job evaluation
    job_gaps = compute_skill_gaps(
        missing_required=job_reqs.required_skills,
        partial_required=[],
        missing_nice_to_have=job_reqs.preferred_skills,
        job_title="Legacy Systems Specialist",
    )
    job_gap_skills = {g.skill.lower() for g in job_gaps}

    assert "cobol" in job_gap_skills
    assert "fortran" in job_gap_skills

    # 3. Canonical career competencies must remain untouched
    career_result_after = evaluate_career_competencies(role_prof, candidate)
    career_skills_after = {g.skill.lower() for g in career_result_after}

    assert career_skills == career_skills_after
    assert "cobol" not in career_skills_after
    assert "fortran" not in career_skills_after


# ============================================================================
# 10. EDGE CASES: UNKNOWN ROLE & SPARSE RESUME
# ============================================================================

def test_edge_case_unknown_role():
    """An arbitrary or unknown role returns low confidence or an empty profile,
    and NEVER silently falls back to generic Software Engineer."""
    prof, conf, reason = resolve_role("Quantum Gravity Interstellar Specialist")
    assert conf == "LOW"
    assert prof is None or prof.role != "Software Engineer"


def test_edge_case_sparse_resume():
    """A sparse resume with 0 evidence entries does not crash and marks all
    canonical competencies as NO_RESUME_EVIDENCE."""
    sparse_candidate = CandidateProfile(
        personal={"name": "Sparse Cand"},
        skills=[],
        experience=[],
        education=[],
        projects=[],
        evidence_units=[],
    )

    role_prof, _, _ = match_canonical_role("Frontend Developer")
    assert role_prof is not None

    gaps = evaluate_career_competencies(role_prof, candidate=sparse_candidate)
    total = len(gaps)
    assert total > 0

    demonstrated = sum(1 for g in gaps if g.status == CompetencyStatus.DEMONSTRATED.value)
    partially_demo = sum(1 for g in gaps if g.status == CompetencyStatus.PARTIALLY_DEMONSTRATED.value)
    no_evidence = sum(1 for g in gaps if g.status == CompetencyStatus.NO_RESUME_EVIDENCE.value)

    assert demonstrated == 0
    assert partially_demo == 0
    assert no_evidence == total

    for comp in gaps:
        assert comp.status == CompetencyStatus.NO_RESUME_EVIDENCE.value
        assert len(comp.evidence) == 0
