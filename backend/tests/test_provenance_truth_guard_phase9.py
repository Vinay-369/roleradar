"""
Tests for Phase 9: Provenance-Based Truth Guard.
Validates:
- Rewrite technology and metric verification (no 50% -> 60%, no cross-entity migration)
- Scope, seniority, production, and deployment verification
- Structural integrity (fragments, orphan continuations, truncated bullets, tech-only fragments, duplicates)
- Source coverage (ACCIDENTALLY_LOST fails validation; removal requires reason)
- Safe fallback behavior (auto-reverts to original source evidence without hallucination)
"""
import pytest
from app.modules.resume.models import (
    CandidateProfile,
    TailoringAction,
    TailoringDecision,
    TailoringPlan,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.plan import apply_tailoring_plan
from app.modules.tailoring.validation import (
    TruthGuardAuditResult,
    validate_tailored_profile_truth_guard,
)


def test_truth_guard_rejects_unsupported_technology():
    resume = """
    LUCAS VANCE
    lucas@example.com

    EXPERIENCE
    Backend Developer at DevCorp (2022 - Present)
    • Developed REST APIs using Python and PostgreSQL.
    """
    profile = extract_candidate_profile(resume)
    ev_id = profile.experience[0].evidence_units[0].id

    # Rewrite injects ungrounded Kubernetes
    plan = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.REWRITE,
                proposed_text="Developed REST APIs using Python and Kubernetes.",
                reason="Aligned with JD.",
                source_evidence_ids=[ev_id],
            )
        ]
    )

    tailored = apply_tailoring_plan(profile, plan)
    clean_tailored, report = validate_tailored_profile_truth_guard(profile, tailored, plan, auto_revert=True)

    assert not report.is_valid
    assert "kubernetes" in report.unsupported_technologies
    assert ev_id in report.reverted_evidence_ids
    # Auto-reverted back to verified source text
    assert "Kubernetes" not in clean_tailored.experience[0].evidence_units[0].text
    assert "PostgreSQL" in clean_tailored.experience[0].evidence_units[0].text


def test_truth_guard_rejects_metric_inflation_50_to_60():
    resume = """
    LUCAS VANCE
    lucas@example.com

    EXPERIENCE
    Backend Developer at DevCorp (2022 - Present)
    • Optimized database queries improving response times by 50%.
    """
    profile = extract_candidate_profile(resume)
    ev_id = profile.experience[0].evidence_units[0].id

    # Fabricating 50% -> 60%
    plan = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.REWRITE,
                proposed_text="Optimized database queries improving response times by 60%.",
                reason="Inflated metric.",
                source_evidence_ids=[ev_id],
            )
        ]
    )

    tailored = apply_tailoring_plan(profile, plan)
    clean_tailored, report = validate_tailored_profile_truth_guard(profile, tailored, plan, auto_revert=True)

    assert not report.is_valid
    assert "60%" in report.unsupported_metrics
    assert ev_id in report.reverted_evidence_ids
    # Exact original 50% restored
    assert "50%" in clean_tailored.experience[0].evidence_units[0].text


def test_truth_guard_rejects_cross_entity_metric_migration():
    resume = """
    SARAH CONNOR
    sarah@example.com

    PROJECTS
    Project Alpha (Python)
    • Processed 100k daily records.

    Project Beta (Go)
    • Generated $500k in annual revenue.
    """
    profile = extract_candidate_profile(resume)
    alpha_ev_id = profile.projects[0].evidence_units[0].id

    # Migrating $500k from Project Beta into Project Alpha
    plan = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=alpha_ev_id,
                action=TailoringAction.REWRITE,
                proposed_text="Processed data generating $500k in revenue with Python.",
                reason="Cross-entity metric hallucination.",
                source_evidence_ids=[alpha_ev_id],
            )
        ]
    )

    tailored = apply_tailoring_plan(profile, plan)
    clean_tailored, report = validate_tailored_profile_truth_guard(profile, tailored, plan, auto_revert=True)

    assert not report.is_valid
    assert alpha_ev_id in report.reverted_evidence_ids
    assert any("belongs to another entity" in v for v in report.violations)


def test_truth_guard_rejects_scope_and_seniority_escalation():
    resume = """
    JANE DOE
    jane@example.com

    EXPERIENCE
    Software Engineering Intern at StartupX (2023)
    • Assisted team with writing unit tests in Python.
    """
    profile = extract_candidate_profile(resume)
    ev_id = profile.experience[0].evidence_units[0].id

    # Escalating intern test assistant to enterprise VP leadership
    plan = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.REWRITE,
                proposed_text="Spearheaded enterprise testing strategy directing a team of 15 engineers in production.",
                reason="Scope inflation.",
                source_evidence_ids=[ev_id],
            )
        ]
    )

    tailored = apply_tailoring_plan(profile, plan)
    clean_tailored, report = validate_tailored_profile_truth_guard(profile, tailored, plan, auto_revert=True)

    assert not report.is_valid
    assert any("Leadership claim" in v for v in report.violations)
    assert any("Production scope modifier" in v for v in report.violations)
    assert ev_id in report.reverted_evidence_ids


def test_truth_guard_rejects_structural_fragments_and_tech_only_lists():
    resume = """
    ALEX SMITH
    alex@example.com

    EXPERIENCE
    Developer at TechLab (2022 - Present)
    • Developed automated test suites in Python.
    • Built customer reporting dashboard.
    """
    profile = extract_candidate_profile(resume)
    ev1_id = profile.experience[0].evidence_units[0].id
    ev2_id = profile.experience[0].evidence_units[1].id

    # ev1 -> tech-only list; ev2 -> orphan continuation
    plan = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev1_id,
                action=TailoringAction.REWRITE,
                proposed_text="Python, Docker, React.",
                reason="Tech only list.",
                source_evidence_ids=[ev1_id],
            ),
            TailoringDecision(
                evidence_id=ev2_id,
                action=TailoringAction.REWRITE,
                proposed_text="and deployed on AWS.",
                reason="Orphan continuation.",
                source_evidence_ids=[ev2_id],
            ),
        ]
    )

    tailored = apply_tailoring_plan(profile, plan)
    clean_tailored, report = validate_tailored_profile_truth_guard(profile, tailored, plan, auto_revert=True)

    assert not report.is_valid
    assert len(report.structural_violations) >= 2
    assert ev1_id in report.reverted_evidence_ids
    assert ev2_id in report.reverted_evidence_ids


def test_truth_guard_enforces_source_coverage_and_accidental_loss():
    resume = """
    CHRIS GREEN
    chris@example.com

    EXPERIENCE
    Engineer at CloudTech (2021 - Present)
    • Built payment microservices with Go.
    • Maintained legacy authentication service.
    """
    profile = extract_candidate_profile(resume)
    ev_legacy_id = profile.experience[0].evidence_units[1].id

    # 1. Accidental loss (dropped without plan removal decision)
    # Simulate accidental drop
    dropped_profile = extract_candidate_profile(resume)
    dropped_profile.experience[0].evidence_units.pop(1)
    dropped_profile.evidence_units.pop(1)

    _, report_loss = validate_tailored_profile_truth_guard(profile, dropped_profile, None)
    assert not report_loss.is_valid
    assert report_loss.source_coverage_summary["accidental_loss"] == 1
    assert any("ACCIDENTALLY_LOST" in v for v in report_loss.violations)

    # 2. Intentional removal without reason -> fails
    plan_no_reason = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev_legacy_id,
                action=TailoringAction.REMOVE,
                reason="",  # Empty reason
                source_evidence_ids=[ev_legacy_id],
            )
        ]
    )
    tailored_no_reason = apply_tailoring_plan(profile, plan_no_reason)
    _, report_no_reason = validate_tailored_profile_truth_guard(profile, tailored_no_reason, plan_no_reason)
    assert not report_no_reason.is_valid
    assert any("missing a mandatory reason" in v for v in report_no_reason.violations)

    # 3. Intentional removal WITH reason -> passes
    plan_with_reason = TailoringPlan(
        evidence_decisions=[
            TailoringDecision(
                evidence_id=ev_legacy_id,
                action=TailoringAction.REMOVE,
                reason="Legacy auth maintenance deprioritized for modern Go backend JD.",
                source_evidence_ids=[ev_legacy_id],
            )
        ]
    )
    tailored_with_reason = apply_tailoring_plan(profile, plan_with_reason)
    _, report_with_reason = validate_tailored_profile_truth_guard(profile, tailored_with_reason, plan_with_reason)
    assert report_with_reason.is_valid
    assert report_with_reason.source_coverage_summary["removed"] == 1
    assert report_with_reason.source_coverage_summary["accidental_loss"] == 0
