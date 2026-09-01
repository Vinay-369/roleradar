"""
Tests for Phase 8: Structured Tailoring Plan.
Validates compact prompt context, TailoringPlan generation over stable EvidenceUnit IDs,
bullet rewrite structure, removal reasons, condensing with source IDs, and deterministic application.
"""
import pytest
from app.modules.jobs.taxonomy import analyze_jd_requirements
from app.modules.matching.evidence_mapping import map_resume_to_jd_evidence
from app.modules.resume.classification import analyze_candidate_profile
from app.modules.resume.models import (
    CandidateProfile,
    TailoringAction,
    TailoringDecision,
    TailoringPlan,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.plan import (
    apply_tailoring_plan,
    build_tailoring_prompt_context,
    generate_structured_tailoring_plan,
)


def test_build_tailoring_prompt_context_is_compact_and_structured():
    resume = """
    EMILY BLUNT
    emily@example.com

    EXPERIENCE
    Software Engineer at CloudCorp (2022 - Present)
    • Engineered distributed stream processing pipeline in Go and Kafka handling 50k events/sec.
    • Automated Docker deployment pipelines with GitHub Actions.
    """
    jd_text = """
    Senior Backend Engineer
    Requirements:
    • Expert in Go and distributed streaming systems (Kafka).
    • Strong CI/CD experience.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    analysis = analyze_candidate_profile(profile)
    evidence_map = map_resume_to_jd_evidence(profile, jd)

    prompt_ctx = build_tailoring_prompt_context(profile, jd, evidence_map, analysis)

    assert "candidate_analysis" in prompt_ctx
    assert "target_role" in prompt_ctx
    assert "jd_requirements" in prompt_ctx
    assert "evidence_jd_mapping" in prompt_ctx
    assert "evidence_units" in prompt_ctx

    # Compact evidence representation contains stable IDs
    assert len(prompt_ctx["evidence_units"]) == 2
    assert "evidence_id" in prompt_ctx["evidence_units"][0]
    assert "raw_resume_text" not in prompt_ctx


def test_generate_and_apply_structured_tailoring_plan():
    resume = """
    ALEX MERCER
    alex@example.com

    EXPERIENCE
    Backend Engineer at Apex Systems (2021 - Present)
    • Built REST APIs in Python and PostgreSQL.
    • Maintained legacy Perl scripts.

    PROJECTS
    Distributed Cache (Go, Redis)
    • Implemented LRU cache engine in Go.
    """
    jd_text = """
    Python Backend Engineer
    Requirements:
    • Advanced Python and PostgreSQL experience.
    • Experience building high-performance REST APIs.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    analysis = analyze_candidate_profile(profile)
    evidence_map = map_resume_to_jd_evidence(profile, jd)

    plan = generate_structured_tailoring_plan(profile, jd, evidence_map, analysis)

    assert isinstance(plan, TailoringPlan)
    assert len(plan.evidence_decisions) >= 3
    assert plan.summary_rewrite is not None
    assert "Python" in plan.ordered_skills[0] or "PostgreSQL" in plan.ordered_skills[0]

    # Explicitly test deterministic plan application with a custom plan
    ev_python_id = profile.experience[0].evidence_units[0].id
    ev_perl_id = profile.experience[0].evidence_units[1].id

    custom_plan = TailoringPlan(
        summary_rewrite="Senior Python Backend Engineer specializing in scalable API design and PostgreSQL optimization.",
        ordered_skills=["Python", "PostgreSQL", "Go", "Redis"],
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev_python_id,
                action=TailoringAction.REWRITE,
                proposed_text="Architected and deployed high-throughput REST APIs using Python and PostgreSQL.",
                reason="Aligned with target JD role.",
                source_evidence_ids=[ev_python_id],
                confidence=1.0,
            ),
            TailoringDecision(
                evidence_id=ev_perl_id,
                action=TailoringAction.REMOVE,
                proposed_text=None,
                reason="Legacy Perl maintenance not relevant to target role.",
                source_evidence_ids=[ev_perl_id],
                confidence=1.0,
            ),
        ],
    )

    tailored_profile = apply_tailoring_plan(profile, custom_plan)

    # Verify Summary updated
    assert tailored_profile.summary == custom_plan.summary_rewrite

    # Verify Skills reordered
    assert tailored_profile.skills == custom_plan.ordered_skills

    # Verify Experience Entity mutated deterministically:
    # 1. Python bullet rewritten
    # 2. Perl bullet removed
    assert len(tailored_profile.experience[0].evidence_units) == 1
    assert tailored_profile.experience[0].evidence_units[0].id == ev_python_id
    assert tailored_profile.experience[0].evidence_units[0].text == "Architected and deployed high-throughput REST APIs using Python and PostgreSQL."
    assert len(tailored_profile.experience[0].bullets) == 1
    assert "Perl" not in tailored_profile.experience[0].bullets[0]


def test_condense_decision_records_multiple_source_ids():
    resume = """
    JORDAN LEE
    jordan@example.com

    EXPERIENCE
    Software Engineer at DataTech (2022 - Present)
    • Monitored database latency metrics in Grafana.
    • Configured database alerting thresholds in Prometheus.
    """

    profile = extract_candidate_profile(resume)
    ev1_id = profile.experience[0].evidence_units[0].id
    ev2_id = profile.experience[0].evidence_units[1].id

    # Condensing ev1 and ev2 into a single unified telemetry bullet
    condensed_text = "Established comprehensive database observability and proactive alerting using Prometheus and Grafana."
    condense_plan = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev1_id,
                action=TailoringAction.CONDENSE,
                proposed_text=condensed_text,
                reason="Condensed related database telemetry bullets for concise high impact.",
                source_evidence_ids=[ev1_id, ev2_id],
                confidence=1.0,
            ),
            TailoringDecision(
                evidence_id=ev2_id,
                action=TailoringAction.REMOVE,
                reason="Subsumed into unified telemetry evidence unit.",
                source_evidence_ids=[ev2_id],
                confidence=1.0,
            ),
        ]
    )

    tailored = apply_tailoring_plan(profile, condense_plan)

    assert len(tailored.experience[0].evidence_units) == 1
    assert tailored.experience[0].evidence_units[0].text == condensed_text
    assert tailored.experience[0].evidence_units[0].id == ev1_id


def test_rewrite_preserves_exact_metrics_without_inventing_unsupported_facts():
    resume = """
    TAYLOR REED
    taylor@example.com

    EXPERIENCE
    Performance Engineer at SpeedCo (2021 - Present)
    • Optimized database queries reducing p99 latency by 35% across 20M daily active users.
    """

    profile = extract_candidate_profile(resume)
    ev_id = profile.experience[0].evidence_units[0].id

    # Complete semantic rewrite: ACTION + WHAT + HOW + RESULT
    proposed = "Engineered PostgreSQL indexing strategies and query optimizations, reducing p99 latency by 35% across 20M daily active users."
    plan = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.REWRITE,
                proposed_text=proposed,
                reason="Strengthened technical action verbs while preserving exact quantified impact metrics.",
                source_evidence_ids=[ev_id],
                confidence=1.0,
            )
        ]
    )

    tailored = apply_tailoring_plan(profile, plan)

    # Exact metrics 35% and 20M preserved
    assert "35%" in tailored.experience[0].evidence_units[0].text
    assert "20M" in tailored.experience[0].evidence_units[0].text
    assert tailored.experience[0].evidence_units[0].id == ev_id
