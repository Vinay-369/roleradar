"""
Dedicated Unit Tests for Phase 5 Explicit Resume Evidence <-> JD Requirement Mapping Layer.
Tests:
- exact skill match
- related skill match
- partial evidence
- missing skill (verifying it is NEVER added to candidate profile)
- conflicting evidence
- technology present only in an unrelated project
"""
import pytest
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.matching.evidence_mapping import (
    EvidenceMatchStatus,
    map_resume_to_jd_evidence,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile

TARGET_JD = """
Job Title: Senior Backend Engineer
Location: San Francisco, CA

CORE REQUIREMENTS
• 5+ years experience with Python and PostgreSQL.
• Experience with Django web framework.
• Proven background building large-scale database architectures.
• Active Top Secret security clearance required.

PREFERRED QUALIFICATIONS
• Hands-on production experience with Rust or C++.
• Experience with Apache Kafka for event-driven message queuing.

RESPONSIBILITIES
• Architect high-throughput REST APIs and data processing queues.
"""

CANDIDATE_RESUME = """
RAVI KUMAR
Bangalore, India | ravi@example.com

SUMMARY
Backend Engineer with 4 years building scalable services using FastAPI, Python, and PostgreSQL.

SKILLS
Languages: Python, Go, SQL
Frameworks: FastAPI, Flask, PostgreSQL, Redis, Docker

WORK EXPERIENCE
Software Engineer at ScaleData (2022 - Present) - Bangalore
• Built high-performance REST APIs using Python and FastAPI handling 20,000 req/sec.
• Optimized PostgreSQL database indexing and query latency by 40%.

PROJECTS
• Rust Command Line File Indexer: Built experimental local desktop file search tool in Rust.

EDUCATION
VTU Karnataka
B.E in Computer Science (2018 - 2022)
"""


def test_exact_skill_match():
    profile = extract_candidate_profile(CANDIDATE_RESUME)
    job_reqs = analyze_job_description(TARGET_JD)

    matrix = map_resume_to_jd_evidence(profile, job_reqs)

    # 1. Exact match for Python & PostgreSQL
    python_mapping = next(m for m in matrix.mappings if "python" in m.requirement_text.lower() and "postgresql" in m.requirement_text.lower())
    assert python_mapping.status == EvidenceMatchStatus.EXACT_MATCH
    assert "Python" in python_mapping.matched_skills or "python" in [s.lower() for s in python_mapping.matched_skills]
    assert len(python_mapping.matched_evidence_units) >= 1
    assert any("ScaleData" in ev.entity_id or "exp" in ev.entity_id for ev in python_mapping.matched_evidence_units)


def test_related_skill_match():
    profile = extract_candidate_profile(CANDIDATE_RESUME)
    job_reqs = analyze_job_description(TARGET_JD)

    matrix = map_resume_to_jd_evidence(profile, job_reqs)

    # 2. Related match: JD requires Django, candidate has FastAPI / Flask (Python backend cluster)
    django_mapping = next(m for m in matrix.mappings if "django" in m.requirement_text.lower())
    assert django_mapping.status == EvidenceMatchStatus.RELATED
    assert any(s.lower() in ["fastapi", "flask", "python"] for s in django_mapping.matched_skills)
    assert len(django_mapping.matched_evidence_units) >= 1


def test_partial_evidence():
    profile = extract_candidate_profile(CANDIDATE_RESUME)
    job_reqs = analyze_job_description(TARGET_JD)

    matrix = map_resume_to_jd_evidence(profile, job_reqs)

    # 3. Partial match for database architectures (candidate has db indexing on Postgres)
    db_arch_mapping = next(m for m in matrix.mappings if "database architecture" in m.requirement_text.lower())
    assert db_arch_mapping.status in (EvidenceMatchStatus.PARTIAL, EvidenceMatchStatus.EXACT_MATCH, EvidenceMatchStatus.SUPPORTED)


def test_missing_skill_never_added_to_candidate():
    profile = extract_candidate_profile(CANDIDATE_RESUME)
    job_reqs = analyze_job_description(TARGET_JD)

    original_skills_count = len(profile.skills)
    matrix = map_resume_to_jd_evidence(profile, job_reqs)

    # 4. Missing skill: Kafka (candidate has no Kafka in skills, projects, or experience)
    kafka_mapping = next(m for m in matrix.mappings if "kafka" in m.requirement_text.lower())
    assert kafka_mapping.status == EvidenceMatchStatus.MISSING
    assert len(kafka_mapping.matched_evidence_units) == 0

    # Critical invariant: JD requirement != candidate qualification. Candidate profile remains unaltered.
    assert "Kafka" not in profile.skills
    assert "kafka" not in [s.lower() for s in profile.skills]
    assert len(profile.skills) == original_skills_count


def test_conflicting_evidence():
    profile = extract_candidate_profile(CANDIDATE_RESUME)
    job_reqs = analyze_job_description(TARGET_JD)

    matrix = map_resume_to_jd_evidence(profile, job_reqs)

    # 5. Conflicting: Top Secret security clearance required
    clearance_mapping = next(m for m in matrix.mappings if "clearance" in m.requirement_text.lower())
    assert clearance_mapping.status == EvidenceMatchStatus.CONFLICTING
    assert clearance_mapping.relevance_score == 0.0


def test_technology_present_only_in_unrelated_project():
    profile = extract_candidate_profile(CANDIDATE_RESUME)
    job_reqs = analyze_job_description(TARGET_JD)

    matrix = map_resume_to_jd_evidence(profile, job_reqs)

    # 6. Rust is present only in an experimental desktop project, not work experience
    rust_mapping = next(m for m in matrix.mappings if "rust" in m.requirement_text.lower())
    assert rust_mapping.status == EvidenceMatchStatus.EXACT_MATCH
    assert "Rust" in rust_mapping.matched_skills or "rust" in [s.lower() for s in rust_mapping.matched_skills]
    
    # Scoped strictly to project evidence
    assert len(rust_mapping.matched_evidence_units) >= 1
    assert all(ev.section == "PROJECTS" for ev in rust_mapping.matched_evidence_units)
    assert any("proj" in ev.entity_id for ev in rust_mapping.matched_evidence_units)
