"""
Tests for Phase 5: Authoritative Source Evidence Ledger.
Validates stable evidence IDs, claim classification, metric fidelity,
coverage auditing, position independence, and multi-entity provenance.
"""
import pytest
from app.modules.resume.ledger import (
    get_evidence_by_id,
    get_evidence_for_entity,
    get_claims,
    get_metrics,
    get_technologies,
    get_source_location,
    extract_claims_from_text,
    compare_source_coverage,
)
from app.modules.resume.models import (
    CandidateProfile,
    ClaimType,
    EvidenceUnit,
    SourceCoverageState,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile


def test_duplicate_looking_bullets_across_different_companies():
    resume_text = """
    ALEX RIVERA
    alex@example.com

    EXPERIENCE
    Software Engineer at Alpha Corp (2022 - Present)
    • Engineered scalable backend services in Python and Go with 99.9% uptime.

    Software Engineer at Beta Labs (2020 - 2022)
    • Engineered scalable backend services in Python and Go with 99.9% uptime.
    """

    profile = extract_candidate_profile(resume_text)

    assert len(profile.experience) == 2
    alpha_exp = profile.experience[0]
    beta_exp = profile.experience[1]

    # Verify each entity has unique, stable evidence units
    assert len(alpha_exp.evidence_units) == 1
    assert len(beta_exp.evidence_units) == 1

    ev_alpha = alpha_exp.evidence_units[0]
    ev_beta = beta_exp.evidence_units[0]

    # Different IDs guaranteed despite identical text
    assert ev_alpha.id != ev_beta.id
    assert "ALPHA" in ev_alpha.id
    assert "BETA" in ev_beta.id

    # Lookup via ledger API
    found_alpha = get_evidence_by_id(profile, ev_alpha.id)
    assert found_alpha is not None
    assert found_alpha.entity_id == alpha_exp.id

    found_beta = get_evidence_by_id(profile, ev_beta.id)
    assert found_beta is not None
    assert found_beta.entity_id == beta_exp.id


def test_same_metric_and_actions_in_different_sections():
    resume_text = """
    JORDAN REESE
    jordan@example.com

    EXPERIENCE
    Senior Engineer at DataScale (2021 - Present)
    • Architected distributed streaming pipeline reducing latency by 45%.

    PROJECTS
    HyperStream Cache (Rust, Redis)
    • Architected distributed streaming pipeline reducing latency by 45%.
    """

    profile = extract_candidate_profile(resume_text)

    assert len(profile.experience) == 1
    assert len(profile.projects) == 1

    exp_ev = profile.experience[0].evidence_units[0]
    proj_ev = profile.projects[0].evidence_units[0]

    assert exp_ev.id.startswith("EXP_")
    assert proj_ev.id.startswith("PROJ_")
    assert exp_ev.id != proj_ev.id

    # Exact metrics preserved
    assert "45%" in get_metrics(exp_ev)
    assert "45%" in get_metrics(proj_ev)


def test_claim_type_extraction():
    sample_bullet = "Spearheaded multi-tenant cloud migration on AWS Kubernetes reducing annual infrastructure costs by $350,000 with sub-10ms p99 latency."

    claims = extract_claims_from_text(sample_bullet)
    claim_types = [c[0] for c in claims]

    # Should detect Leadership, Metric, Business Impact, Performance, Scale, and Technology
    assert ClaimType.LEADERSHIP in claim_types
    assert ClaimType.METRIC in claim_types
    assert ClaimType.BUSINESS_IMPACT in claim_types
    assert ClaimType.PERFORMANCE in claim_types
    assert ClaimType.SCALE in claim_types
    assert ClaimType.TECHNOLOGY in claim_types


def test_source_coverage_auditing():
    ev1 = EvidenceUnit(
        id="EXP_CORP_001",
        section="EXPERIENCE",
        entity_id="exp_0",
        original_text="Engineered microservices in Go and Docker processing 50k QPS.",
        normalized_text="Engineered microservices in Go and Docker processing 50k QPS.",
        metrics=["50k QPS"],
        technologies=["Go", "Docker"],
    )
    ev2 = EvidenceUnit(
        id="EXP_CORP_002",
        section="EXPERIENCE",
        entity_id="exp_0",
        original_text="Built CI/CD automated deployment pipeline with GitHub Actions.",
        normalized_text="Built CI/CD automated deployment pipeline with GitHub Actions.",
        metrics=[],
        technologies=["GitHub Actions"],
    )
    ev3 = EvidenceUnit(
        id="EXP_CORP_003",
        section="EXPERIENCE",
        entity_id="exp_0",
        original_text="Maintained legacy PHP system.",
        normalized_text="Maintained legacy PHP system.",
        metrics=[],
        technologies=["PHP"],
    )

    source_units = [ev1, ev2, ev3]

    # Target tailored content has ev1 preserved, ev2 rewritten, ev3 intentionally removed
    target_output = [
        "Engineered microservices in Go and Docker processing 50k QPS with zero downtime.",
        "Constructed automated CI/CD deployment pipelines using GitHub Actions.",
    ]
    decisions = {
        "EXP_CORP_003": "REMOVE",
    }

    audit = compare_source_coverage(source_units, target_output, explicit_decisions=decisions)

    assert audit["total_source_units"] == 3
    assert audit["preserved_units_count"] == 2
    assert audit["coverage_rate"] == 0.6667
    assert audit["states"]["EXP_CORP_001"] in (SourceCoverageState.PRESERVED, SourceCoverageState.REWRITTEN)
    assert audit["states"]["EXP_CORP_002"] == SourceCoverageState.REWRITTEN
    assert audit["states"]["EXP_CORP_003"] == SourceCoverageState.INTENTIONALLY_REMOVED
    assert len(audit["lost_evidence_ids"]) == 0


def test_identity_independence_from_list_position():
    # If experiences or projects are reordered, their semantic evidence IDs must remain constant
    resume_text = """
    TAYLOR REESE
    taylor@example.com

    EXPERIENCE
    Staff Engineer at Zenith Tech (2022 - Present)
    • Scaled search engine to 10M DAU.

    Senior Engineer at Apex Labs (2019 - 2022)
    • Built realtime notification queue.
    """

    profile1 = extract_candidate_profile(resume_text)
    ev_zenith_1 = profile1.experience[0].evidence_units[0].id
    ev_apex_1 = profile1.experience[1].evidence_units[0].id

    # Reverse experience list
    profile1.experience.reverse()

    # Querying by entity
    zenith_units = get_evidence_for_entity(profile1, "exp_0")
    assert len(zenith_units) == 1
    assert zenith_units[0].id == ev_zenith_1


def test_unknown_custom_section_provenance_and_ledger():
    resume_text = """
    CASEY STONE
    casey@example.com

    WORK EXPERIENCE
    Software Engineer at TechCorp (2022 - Present)
    • Built API gateway in FastAPI.

    PATENTS & INVENTIONS
    • US Patent 10,987,654: Adaptive Stream Multiplexing Algorithm.
    """

    profile = extract_candidate_profile(resume_text)

    assert len(profile.additional_sections) == 1
    add_sec = profile.additional_sections[0]
    assert len(add_sec.evidence_units) == 1

    ev_patent = add_sec.evidence_units[0]
    assert "PATENT" in ev_patent.id
    assert "US Patent 10,987,654" in ev_patent.text

    # Lookup in ledger
    found = get_evidence_by_id(profile, ev_patent.id)
    assert found is not None
    assert found.section == "ADDITIONAL"
    assert "PATENTS" in (found.source_location or "")
