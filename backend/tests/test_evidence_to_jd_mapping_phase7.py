"""
Tests for Phase 7: Evidence to JD Mapping.
Validates exact matches, synonyms, related adjacent skills, transferable experience,
missing skills, conflicting requirements, multi-evidence mappings, and query helpers.
"""
import pytest
from app.modules.jobs.taxonomy import analyze_jd_requirements
from app.modules.matching.evidence_mapping import (
    EvidenceJDMap,
    EvidenceMatchStatus,
    MatchLevel,
    map_resume_to_jd_evidence,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile


def test_exact_technology_mapping():
    resume = """
    JANE DOE
    jane@example.com

    EXPERIENCE
    Software Engineer at Alpha Corp (2022 - Present)
    • Engineered distributed backend services in Python and Docker.
    """
    jd_text = """
    Backend Engineer
    Requirements:
    • Expert in Python and Docker.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    mapping: EvidenceJDMap = map_resume_to_jd_evidence(profile, jd)

    exact_matches = [m for m in mapping.matches if m.status == EvidenceMatchStatus.EXACT_MATCH]
    assert len(exact_matches) >= 1
    assert "python" in [s.lower() for s in exact_matches[0].matched_skills]
    assert len(exact_matches[0].evidence_ids) >= 1


def test_synonym_technology_mapping():
    # JD asks for Postgres, resume has PostgreSQL
    resume = """
    BOB SMITH
    bob@example.com

    EXPERIENCE
    Database Engineer at Beta Labs (2021 - Present)
    • Optimized PostgreSQL query performance and indexing.
    """
    jd_text = """
    Data Engineer
    Requirements:
    • Strong experience with Postgres.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    mapping: EvidenceJDMap = map_resume_to_jd_evidence(profile, jd)

    matches = [m for m in mapping.matches if m.status in (EvidenceMatchStatus.STRONG_MATCH, EvidenceMatchStatus.EXACT_MATCH)]
    assert len(matches) >= 1
    assert "postgresql" in [s.lower() for s in matches[0].matched_skills]


def test_related_adjacent_technology_is_not_inflated_to_exact():
    # JD asks for Flask, candidate only has FastAPI and Django (related python backend)
    resume = """
    ALEX VANCE
    alex@example.com

    EXPERIENCE
    Backend Developer at CloudCo (2022 - Present)
    • Developed REST APIs using FastAPI and Django.
    """
    jd_text = """
    Python Developer
    Requirements:
    • 3+ years experience building web applications with Flask.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    mapping: EvidenceJDMap = map_resume_to_jd_evidence(profile, jd)

    # Must be RELATED or PARTIAL, NOT EXACT_MATCH
    flask_match = next((m for m in mapping.matches if "flask" in m.requirement_text.lower()), None)
    assert flask_match is not None
    assert flask_match.status == EvidenceMatchStatus.RELATED
    assert flask_match.status != EvidenceMatchStatus.EXACT_MATCH
    assert "fastapi" in [s.lower() for s in flask_match.matched_skills] or "django" in [s.lower() for s in flask_match.matched_skills]


def test_missing_skill_identified():
    resume = """
    LISA RAY
    lisa@example.com

    EXPERIENCE
    Frontend Developer at WebCorp (2021 - Present)
    • Built user interfaces in React and TypeScript.
    """
    jd_text = """
    Full Stack Engineer
    Requirements:
    • Advanced experience with Kubernetes and Go.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    mapping: EvidenceJDMap = map_resume_to_jd_evidence(profile, jd)

    missing_matches = [m for m in mapping.matches if m.status == EvidenceMatchStatus.MISSING]
    assert len(missing_matches) >= 1
    assert any("kubernetes" in m.requirement_text.lower() or "go" in m.requirement_text.lower() for m in missing_matches)


def test_conflicting_experience_identified():
    # Candidate is a student/fresher, JD strictly requires 15+ years Director
    resume = """
    TIM GREEN
    tim@university.edu

    EDUCATION
    State University
    B.S. in Computer Science (2023 - 2027)

    PROJECTS
    • ChatBot: Built in Python.
    """
    jd_text = """
    Vice President of Engineering
    Requirements:
    • 15+ years of software engineering leadership experience.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    mapping: EvidenceJDMap = map_resume_to_jd_evidence(profile, jd)

    conflicts = [m for m in mapping.matches if m.status == EvidenceMatchStatus.CONFLICTING]
    assert len(conflicts) >= 1
    assert len(mapping.conflicting_requirements) >= 1


def test_multiple_evidence_units_supporting_single_requirement():
    resume = """
    MARK TAYLOR
    mark@example.com

    EXPERIENCE
    Senior Engineer at Zenith (2023 - Present)
    • Architected Python data pipelines.

    Engineer at Apex (2021 - 2023)
    • Built Python microservices.
    """
    jd_text = """
    Python Developer
    Requirements:
    • Deep expertise in Python.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    mapping: EvidenceJDMap = map_resume_to_jd_evidence(profile, jd)

    python_matches = [m for m in mapping.matches if "python" in m.requirement_text.lower()]
    assert len(python_matches) >= 1
    # Both evidence units mapped
    assert len(python_matches[0].evidence_ids) >= 2


def test_evidence_jd_map_helper_queries():
    resume = """
    CHRIS EVANS
    chris@example.com

    EXPERIENCE
    Software Engineer at TechCorp (2022 - Present)
    • Built React frontend and Node.js backend.
    """
    jd_text = """
    Full Stack Developer
    Requirements:
    • React frontend development.
    • Node.js backend services.
    """

    profile = extract_candidate_profile(resume)
    jd = analyze_jd_requirements(jd_text)
    mapping: EvidenceJDMap = map_resume_to_jd_evidence(profile, jd)

    # 1. Query by requirement ID
    first_req_id = [r.id for r in jd.requirements if r.skills_detected][0]
    req_matches = mapping.get_matches_for_requirement(first_req_id)
    assert len(req_matches) >= 1

    # 2. Query supporting evidence IDs
    supporting_eids = mapping.get_supporting_evidence_ids()
    assert len(supporting_eids) >= 1

    # 3. Top supporting evidence
    top_ev = mapping.get_top_supporting_evidence(first_req_id, limit=1)
    assert len(top_ev) == 1
