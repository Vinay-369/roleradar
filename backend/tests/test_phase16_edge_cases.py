"""
Tests for Phase 16: Fix Generalized Phase 15 Edge Cases.
Verifies:
1. P1: Multiple roles / Progression evidence extraction & deduplication.
2. P2: Truth Guard summary & role title grounding without false positives.
3. P3: Single-line delimited contact header normalization (pipe, tilde, bullet, dash).
"""
import pytest

from app.modules.matching.evidence_mapping import map_resume_to_jd_evidence
from app.modules.resume.classification import analyze_candidate_profile
from app.modules.resume.models import (
    CandidateProfile,
    ClaimType,
    EvidenceUnit,
    RoleProgression,
    TailoringDecision,
    TailoringPlan,
    WorkExperienceEntity,
)
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    parse_experience_section,
    structure_resume_text,
)
from app.modules.tailoring.plan import apply_tailoring_plan
from app.modules.tailoring.validation import validate_tailored_profile_truth_guard


# ============================================================================
# P1 Tests: Multiple Roles / Role Progression Evidence Extraction
# ============================================================================

def test_p1_multiple_roles_progression_evidence_extraction():
    """Verify evidence units are extracted from sub-roles under a single company."""
    resume_text = """
    ELENA ROSTOVA
    elena.r@email.com | (555) 123-4567 | San Francisco, CA

    EXPERIENCE
    Uber Technologies
    Senior Software Engineer (2022 - Present)
    • Architected real-time dispatch engine handling 50k requests/sec.
    • Reduced dispatch p99 latency by 35% using in-memory indices.

    Software Engineer II (2020 - 2022)
    • Ingested 2B daily telemetry points via Kafka stream pipeline.
    • Maintained 99.99% service availability across 12 zones.

    Software Engineer I (2018 - 2020)
    • Built driver onboarding verification microservices in Python.
    """
    profile = extract_candidate_profile(resume_text)
    
    assert len(profile.experience) == 1
    exp = profile.experience[0]
    assert "Uber" in exp.company
    assert len(exp.progression) >= 3
    
    # Check that evidence units exist and match the bullets
    ev_units = [ev for ev in profile.evidence_units if ev.section == "EXPERIENCE"]
    assert len(ev_units) == 5
    
    # Check that individual progressions also have evidence units
    assert len(exp.progression[0].evidence_units) == 2
    assert len(exp.progression[1].evidence_units) == 2
    assert len(exp.progression[2].evidence_units) == 1


def test_p1_mixed_responsibility_and_progression():
    """Verify mixed responsibility groups and role progression deduplicate cleanly."""
    resume_text = """
    MARCUS VANCE
    marcus@vance.io | Seattle, WA

    EXPERIENCE
    Amazon Web Services
    Staff Systems Engineer (2021 - Present)
    Core Infrastructure:
    • Managed 10,000 EC2 bare metal instances with 99.999% uptime.
    • Automated kernel patching cycle saving 40 engineering hours weekly.

    Senior DevOps Engineer (2018 - 2021)
    CI/CD Automation:
    • Built deployment pipeline for 200 microservices using AWS CDK.
    """
    profile = extract_candidate_profile(resume_text)
    assert len(profile.experience) == 1
    ev_units = [ev for ev in profile.evidence_units if ev.section == "EXPERIENCE"]
    assert len(ev_units) >= 3
    # Ensure no duplicates
    ev_texts = [ev.text.strip() for ev in ev_units]
    assert len(ev_texts) == len(set(ev_texts))


# ============================================================================
# P2 Tests: Truth Guard Summary & Role Grounding
# ============================================================================

def test_p2_truth_guard_summary_and_role_grounding():
    """Verify candidate terms from summary, role titles, and projects pass Truth Guard."""
    resume_text = """
    MARCUS STERLING
    marcus.s@email.com | Austin, TX

    SUMMARY
    DevOps & Platform Engineer specializing in Kubernetes infrastructure.

    EXPERIENCE
    Site Reliability Engineer at Zenith Cloud (2021 - Present)
    • Automated multi-tenant Kubernetes cluster provisioning using Terraform.

    SKILLS
    Kubernetes, Docker, Go, Python, Terraform, Helm, ArgoCD, AWS
    """
    profile = extract_candidate_profile(resume_text)
    
    # Create tailored profile rewriting summary with candidate-owned title 'DevOps Engineer'
    plan = TailoringPlan(
        strategy="REVISE_FOR_ALIGNMENT",
        rationale="Align with SRE/DevOps role",
        evidence_decisions=[
            TailoringDecision(
                evidence_id="SUM_001",
                action="REWRITE",
                rewritten_text="DevOps & Platform Engineer specializing in high-scale Kubernetes infrastructure.",
                reason="Highlight platform engineering expertise",
            )
        ]
    )
    tailored = apply_tailoring_plan(profile, plan)
    
    tailored_final, audit = validate_tailored_profile_truth_guard(profile, tailored, plan)
    assert audit.is_valid is True
    assert len(audit.violations) == 0


def test_p2_truth_guard_still_blocks_jd_only_unsupported_technologies():
    """Verify Truth Guard still strictly blocks technical terms not in candidate profile."""
    resume_text = """
    JANE DOE
    jane.doe@email.com | New York, NY

    EXPERIENCE
    Backend Engineer at TechCorp (2021 - Present)
    • Built REST APIs using Python and PostgreSQL.

    SKILLS
    Python, PostgreSQL, Git
    """
    profile = extract_candidate_profile(resume_text)
    
    target_ev_id = profile.evidence_units[0].id
    # Fabricate 'Kubernetes', 'Solidity', 'Rust' which are not in candidate profile
    plan = TailoringPlan(
        strategy="REVISE_FOR_ALIGNMENT",
        rationale="Align with blockchain JD",
        evidence_decisions=[
            TailoringDecision(
                evidence_id=target_ev_id,
                action="REWRITE",
                rewritten_text="Built REST APIs and Solidity smart contracts deployed on Kubernetes and Rust microservices.",
                reason="Target Web3 JD requirements",
            )
        ]
    )
    tailored = apply_tailoring_plan(profile, plan)
    
    tailored_final, audit = validate_tailored_profile_truth_guard(profile, tailored, plan)
    # Must flag unsupported technologies
    assert audit.is_valid is False
    assert any("contains ungrounded technologies" in v for v in audit.violations)
    # Must auto-revert to original text
    reverted_ev = next(ev for ev in tailored_final.evidence_units if ev.id == target_ev_id)
    assert "Solidity" not in reverted_ev.text


# ============================================================================
# P3 Tests: Delimited Single-Line Contact Header Normalization
# ============================================================================

@pytest.mark.parametrize("header_line, expected_name", [
    ("JAMES WILSON | james.wilson@email.com | (555) 999-0000 | Phoenix, AZ", "JAMES WILSON"),
    ("SANJAY GUPTA ~ sanjay.g@email.com ~ +91 9123456789 ~ Hyderabad", "SANJAY GUPTA"),
    ("EMILY CHEN • emily.chen@domain.org • (555) 234-5678 • Seattle, WA", "EMILY CHEN"),
    ("ROBERT TAYLOR - robert.t@gmail.com - (555) 345-6789 - Chicago, IL", "ROBERT TAYLOR"),
    ("*** VIKRAM MALHOTRA *** | vikram.m@email.com | (555) 789-0123", "VIKRAM MALHOTRA"),
    ("Name: SARAH JENKINS | s.jenkins@email.com | (555) 321-7654", "SARAH JENKINS"),
])
def test_p3_delimited_single_line_headers(header_line: str, expected_name: str):
    resume_text = f"""
    {header_line}

    EXPERIENCE
    Software Engineer at TechLab (2020 - Present)
    • Developed web applications using Python and React.

    SKILLS
    Python, React, SQL
    """
    profile = extract_candidate_profile(resume_text)
    assert profile.personal.get("name") == expected_name
    assert profile.personal.get("email") is not None
