"""
Tests for Phase 6: Candidate Analysis + JD Understanding.
Validates multi-signal career stage classification, non-overlapping experience calculation,
structured JD requirements extraction, and strict separation between JD and candidate evidence.
"""
import pytest
from app.modules.jobs.taxonomy import (
    JDRequirements,
    analyze_jd_requirements,
    analyze_job_description,
)
from app.modules.resume.classification import (
    CareerClassification,
    analyze_candidate_profile,
    calculate_experience_duration,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile


def test_experience_calculation_merges_overlapping_roles_without_blind_addition():
    # Role A: Jan 2020 to Dec 2022 (36 months)
    # Role B (concurrent / contract): Jun 2021 to Jun 2023 (25 months)
    # Combined non-overlapping span: Jan 2020 to Jun 2023 = 42 months (3.5 years), NOT 3.0 + 2.1 = 5.1 years!
    dates = ["Jan 2020 - Dec 2022", "Jun 2021 - Jun 2023"]
    duration = calculate_experience_duration(dates)

    assert 3.4 <= duration <= 3.6


def test_candidate_analysis_student_profile():
    resume = """
    MAYA CHEN
    maya@stanford.edu

    EDUCATION
    Stanford University
    B.S. in Computer Science (2023 - 2027)

    PROJECTS
    • NeuralSynth: Audio synthesis with PyTorch.
    • DistributedKV: Raft consensus in Go.
    """
    profile = extract_candidate_profile(resume)
    analysis = analyze_candidate_profile(profile)

    assert analysis.classification in (CareerClassification.STUDENT, CareerClassification.FRESHER)
    assert analysis.is_student is True
    assert analysis.project_depth in ("LIGHT", "STRONG")
    assert analysis.years_of_experience == 0.0


def test_candidate_analysis_research_academic_profile():
    resume = """
    DR. MARCUS VANCE
    marcus@mit.edu

    EDUCATION
    Massachusetts Institute of Technology
    Ph.D. in Computer Science (2018 - 2023)

    PUBLICATIONS
    • Low-Rank Adaptation of Multimodal Foundation Models (ICML 2023)
    • Graph Neural Networks for Molecular Property Prediction (NeurIPS 2022)

    RESEARCH
    • Principal Investigator, DARPA Neuro-Symbolic AI Grant ($500k)

    EXPERIENCE
    Postdoctoral Researcher at MIT CSAIL (2023 - Present)
    • Conducted foundational research on transformer scaling laws.
    """
    profile = extract_candidate_profile(resume)
    analysis = analyze_candidate_profile(profile)

    assert analysis.research_orientation is True
    assert analysis.research_score >= 0.5
    assert analysis.classification in (CareerClassification.RESEARCH, CareerClassification.ACADEMIC, CareerClassification.PROFESSIONAL)


def test_candidate_analysis_career_switcher():
    resume = """
    DAVID MILLER
    david@example.com

    EDUCATION
    Purdue University
    B.S. in Mechanical Engineering (2016 - 2020)

    EXPERIENCE
    Software Engineer at AppWorks (2022 - Present)
    • Built backend APIs in Python and Django.
    """
    profile = extract_candidate_profile(resume)
    analysis = analyze_candidate_profile(profile)

    assert len(analysis.career_transition_indicators) >= 1
    assert "non-computing" in analysis.career_transition_indicators[0].lower() or "mechanical" in analysis.career_transition_indicators[0].lower()


def test_structured_jd_requirements_extraction():
    jd_text = """
    Lead Cloud Infrastructure Engineer

    About the Role:
    We are seeking a Lead Cloud Engineer with 7+ years of experience to design distributed cloud systems.

    Responsibilities:
    • Architect multi-region AWS infrastructure with Terraform and Kubernetes.
    • Mentor junior site reliability engineers.
    • Drive cloud cost optimization and reliability metrics.

    Requirements:
    • 7+ years of experience in Cloud & DevOps engineering.
    • Deep expertise in AWS, Kubernetes, Terraform, Docker, Python.
    • Strong communication and stakeholder management skills.

    Preferred Qualifications:
    • Experience with Go, Prometheus, and Grafana.
    • AWS Solutions Architect Professional certification.
    """

    jd: JDRequirements = analyze_jd_requirements(jd_text)

    assert "Lead Cloud" in (jd.target_role or jd.job_title or "")
    assert jd.seniority == "SENIOR"
    assert jd.experience_requirements is not None
    assert "7+" in jd.experience_requirements or "7" in jd.experience_requirements

    # Required skills
    assert any("aws" in s.lower() for s in jd.required_skills)
    assert any("kubernetes" in s.lower() for s in jd.required_skills)
    assert any("terraform" in s.lower() for s in jd.required_skills)

    # Preferred skills
    assert any("go" in s.lower() for s in jd.preferred_skills)

    # Behavioral expectations / soft skills
    assert any("communication" in s.lower() for s in jd.behavioral_expectations)

    # Domain
    assert jd.domain is not None


def test_strict_separation_jd_skills_never_injected_into_candidate():
    candidate_resume = """
    SARAH CONNOR
    sarah@example.com

    EXPERIENCE
    Software Engineer at TechCorp (2021 - Present)
    • Developed backend services in Python and PostgreSQL.
    """

    profile = extract_candidate_profile(candidate_resume)

    # Verify candidate does NOT have Kubernetes or Rust
    candidate_skills = {s.lower() for s in profile.skills}
    for exp in profile.experience:
        for ev in exp.evidence_units:
            candidate_skills.update({t.lower() for t in ev.technologies})

    assert "kubernetes" not in candidate_skills
    assert "rust" not in candidate_skills

    # Analyze JD requiring Kubernetes and Rust
    jd_text = """
    Senior Systems Engineer
    Requirements:
    • Expert in Kubernetes, Rust, Docker, and AWS.
    """
    jd = analyze_jd_requirements(jd_text)

    # Verify JD has Kubernetes and Rust
    assert any("kubernetes" in s.lower() for s in jd.required_skills)
    assert any("rust" in s.lower() for s in jd.required_skills)

    # STRICT SEPARATION ASSERTION: CandidateProfile must remain completely unmutated!
    candidate_skills_after = {s.lower() for s in profile.skills}
    for exp in profile.experience:
        for ev in exp.evidence_units:
            candidate_skills_after.update({t.lower() for t in ev.technologies})

    assert "kubernetes" not in candidate_skills_after
    assert "rust" not in candidate_skills_after
    assert len(profile.evidence_units) == 1
    assert "Kubernetes" not in profile.evidence_units[0].normalized_text
