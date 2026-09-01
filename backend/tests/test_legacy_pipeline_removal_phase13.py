"""
Phase 13: Legacy Pipeline Removal & Modern Canonical Verification Test Suite.
Verifies the clean migration from legacy structures:
1. experience_raw / projects_raw -> canonical WorkExperienceEntity / ProjectEntity with EvidenceUnits.
2. Flattened tailoring lists -> structured TailoringPlan with explicit actions over EvidenceUnit.id.
3. String-based evidence matching -> EvidenceJDMap with EvidenceMatchStatus.
4. Bullet-index identity -> stable EvidenceUnit.id with section/entity provenance.
5. Downstream raw-text reparsing -> direct semantic CandidateProfile rendering.
6. Public API backward compatibility fields preserved during transition.
"""
import pytest

from app.modules.jobs.taxonomy import analyze_jd_requirements
from app.modules.matching.evidence_mapping import (
    EvidenceJDMap,
    EvidenceMatchStatus,
    MatchSupportLevel,
    map_resume_to_jd_evidence,
)
from app.modules.resume.classification import (
    CareerClassification,
    analyze_candidate_profile,
    classify_candidate_profile,
)
from app.modules.resume.models import (
    CandidateProfile,
    EvidenceUnit,
    TailoringAction,
    TailoringDecision,
    TailoringPlan,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.export import (
    render_candidate_profile_to_text,
    validate_rendered_export_integrity,
)
from app.modules.tailoring.plan import (
    apply_tailoring_plan,
    build_tailoring_prompt_context,
    generate_structured_tailoring_plan,
)
from app.modules.tailoring.strategy import resolve_template_strategy
from app.modules.tailoring.validation import validate_tailored_profile_truth_guard


@pytest.fixture
def sample_resume_text():
    return """
    ELENA ROSTOVA
    elena.rostova@tech.io • (555) 987-6543 • Seattle, WA • linkedin.com/in/erostova

    PROFESSIONAL SUMMARY
    Senior Backend Engineer with 6+ years designing distributed systems in Go, Python, and AWS.

    TECHNICAL SKILLS
    Languages: Go, Python, SQL, Bash
    Cloud & Infra: AWS (EKS, RDS, DynamoDB), Docker, Kubernetes, Terraform

    PROFESSIONAL EXPERIENCE
    Senior Software Engineer at CloudNova (2021 - Present) — Seattle, WA
    • Architected distributed event-driven messaging service in Go processing 250k events/sec.
    • Reduced database p99 query latency by 45% via DynamoDB caching.
    • Mentored 4 junior engineers on distributed consensus protocols.

    Software Engineer at DataMesh (2018 - 2021) — San Francisco, CA
    • Developed RESTful ingestion microservices handling 10TB daily telemetry in Python.
    • Improved automated test coverage from 60% to 92% across 14 microservices.

    PROJECTS
    Raft-KV Distributed Store (Go, gRPC) (2023)
    • Implemented Raft consensus algorithm supporting linearizable reads and snapshotting.
    • Validated fault-tolerance under network partitions using Jepsen tests.

    AsyncFlow Telemetry Engine (Python, Redis) (2022)
    • Built distributed stream processing pipeline processing 50k metrics/sec.

    EDUCATION
    B.S. in Computer Science, University of Washington (2014 - 2018)
    GPA: 3.85 / 4.0

    CERTIFICATIONS
    • AWS Certified Solutions Architect - Professional (2023)
    """


@pytest.fixture
def sample_jd_text():
    return """
    Senior Backend Engineer — High-Throughput Distributed Systems
    Requirements:
    1. 5+ years building distributed backend services in Go or Python.
    2. Deep experience with high-throughput event processing and messaging architectures (> 100k events/sec).
    3. Proven track record reducing database query latency and designing caching strategies.
    4. Hands-on expertise with AWS, Docker, and Kubernetes in production.
    5. Experience mentoring engineers and leading technical architecture.
    """


def test_legacy_removal_01_canonical_profile_entities(sample_resume_text):
    """Verifies that CandidateProfile is populated with rich semantic entities and stable evidence IDs."""
    profile = extract_candidate_profile(sample_resume_text)

    # Canonical entities exist
    assert len(profile.experience) == 2
    assert len(profile.projects) >= 1
    assert len(profile.education) == 1
    assert len(profile.certifications) == 1
    assert len(profile.evidence_units) >= 6

    # Stable evidence unit IDs exist with entity linking
    for ev in profile.evidence_units:
        assert ev.id.startswith(("EXP_", "PROJ_", "SUM_", "SKILL_"))
        assert ev.entity_id is not None
        assert ev.original_text.strip() != ""


def test_legacy_removal_02_no_string_matching_in_tailoring_plan(sample_resume_text, sample_jd_text):
    """Verifies tailoring plan targets stable EvidenceUnit IDs with zero substring matching."""
    profile = extract_candidate_profile(sample_resume_text)
    jd = analyze_jd_requirements(sample_jd_text)
    ev_map = map_resume_to_jd_evidence(profile, jd)

    # Generate plan
    analysis = analyze_candidate_profile(profile)
    plan = generate_structured_tailoring_plan(profile, jd, ev_map, analysis)
    assert len(plan.evidence_decisions) == len(profile.evidence_units)

    # Every decision references a verified EvidenceUnit.id
    profile_ev_ids = {ev.id for ev in profile.evidence_units}
    for dec in plan.evidence_decisions:
        assert dec.evidence_id in profile_ev_ids
        assert dec.action in TailoringAction

    # Deterministic application by ID
    tailored = apply_tailoring_plan(profile, plan)
    assert len(tailored.evidence_units) > 0


def test_legacy_removal_03_no_downstream_reparsing_in_renderer(sample_resume_text):
    """Verifies that the structured renderer directly transforms CandidateProfile into ATS text."""
    profile = extract_candidate_profile(sample_resume_text)
    strategy = resolve_template_strategy(classify_candidate_profile(profile))

    # Render without raw text reparsing
    rendered_text = render_candidate_profile_to_text(profile, strategy)
    assert "ELENA ROSTOVA" in rendered_text
    assert "CloudNova" in rendered_text
    assert "250k events/sec" in rendered_text
    assert "University of Washington" in rendered_text

    is_valid, errors = validate_rendered_export_integrity(profile, rendered_text)
    assert is_valid is True, f"Integrity errors: {errors}"


def test_legacy_removal_04_public_api_compatibility_fields(sample_resume_text):
    """Verifies that CandidateProfile.to_dict() provides backward compatibility fields for legacy consumers."""
    profile = extract_candidate_profile(sample_resume_text)
    d = profile.to_dict()

    # Legacy fields exist for frontend/API compatibility
    assert "experience_raw" in d
    assert "projects_raw" in d
    assert "education_raw" in d
    assert len(d["experience_raw"]) >= 5
    assert len(d["projects_raw"]) >= 1

    # Canonical fields are also present
    assert "experience" in d
    assert "projects" in d
    assert "evidence_units" in d


def test_legacy_removal_05_provenance_and_truth_guard_integrity(sample_resume_text, sample_jd_text):
    """Verifies Truth Guard evaluates tailored profile against evidence ledger with complete provenance."""
    profile = extract_candidate_profile(sample_resume_text)
    jd = analyze_jd_requirements(sample_jd_text)
    ev_map = map_resume_to_jd_evidence(profile, jd)
    analysis = analyze_candidate_profile(profile)
    plan = generate_structured_tailoring_plan(profile, jd, ev_map, analysis)

    tailored = apply_tailoring_plan(profile, plan)
    tailored_final, audit = validate_tailored_profile_truth_guard(profile, tailored, plan)

    assert audit.is_valid is True
    assert audit.source_coverage_summary["accidental_loss"] == 0
    assert len(audit.unsupported_technologies) == 0
    assert len(audit.unsupported_metrics) == 0
