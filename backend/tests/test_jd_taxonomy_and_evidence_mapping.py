"""
Tests for Phase 3 JD Taxonomy & Phase 4 Explicit Resume <-> JD Evidence Mapping.
"""
import pytest
from app.modules.jobs.taxonomy import (
    RequirementCategory,
    analyze_job_description,
)
from app.modules.matching.evidence_mapping import (
    EvidenceMatchStatus,
    map_resume_to_jd_evidence,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile

SAMPLE_JD = """
Job Title: Senior Backend Engineer
Location: Remote

Job Requirements:
• 4+ years of professional experience building backend systems in Python or Go.
• Deep experience with PostgreSQL, Redis, and database query optimization.
• Hands-on experience with Docker, Kubernetes, and AWS cloud services.

Preferred Qualifications:
• Experience with GraphQL and Apache Kafka.
• Familiarity with Rust or C++.

Responsibilities:
• Architect scalable microservices serving millions of requests.
• Collaborate with cross-functional product and frontend teams.
"""

CANDIDATE_RESUME = """
ALEX R
Bangalore, India | alex@example.com

PROFESSIONAL SUMMARY
Backend Engineer with 5 years experience in Python, FastAPI, and Docker.

TECHNICAL SKILLS
Languages: Python, Go, SQL
Databases & Cloud: PostgreSQL, Redis, Docker, AWS

WORK EXPERIENCE
Backend Engineer at ScaleTech (2021 - Present)
• Built Python microservices using FastAPI and PostgreSQL handling 10,000 req/sec.
• Deployed containers using Docker on AWS ECS.
"""


def test_jd_taxonomy_analysis():
    job_reqs = analyze_job_description(SAMPLE_JD, title="Senior Backend Engineer")
    
    assert job_reqs.job_title == "Senior Backend Engineer"
    assert job_reqs.seniority == "SENIOR"
    assert len(job_reqs.requirements) >= 5

    # Check categories
    categories = [r.category for r in job_reqs.requirements]
    assert RequirementCategory.MUST_HAVE in categories
    assert RequirementCategory.PREFERRED in categories
    assert RequirementCategory.RESPONSIBILITY in categories

    assert "python" in [s.lower() for s in job_reqs.must_have_skills]
    assert "postgresql" in [s.lower() for s in job_reqs.must_have_skills]
    assert "graphql" in [s.lower() for s in job_reqs.preferred_skills]


def test_resume_to_jd_evidence_mapping():
    profile = extract_candidate_profile(CANDIDATE_RESUME)
    job_reqs = analyze_job_description(SAMPLE_JD, title="Senior Backend Engineer")

    matrix = map_resume_to_jd_evidence(profile, job_reqs)

    assert matrix.exact_matches_count >= 2
    assert matrix.overall_evidence_score >= 50.0

    # Exact matches for Python and PostgreSQL
    python_reqs = [m for m in matrix.mappings if "python" in [s.lower() for s in m.matched_skills]]
    assert len(python_reqs) >= 1
    assert python_reqs[0].status == EvidenceMatchStatus.EXACT_MATCH
    assert len(python_reqs[0].matched_evidence_units) >= 1

    # Missing preferred skills (GraphQL, Kafka) must NEVER be hallucinated
    missing_pref = [m for m in matrix.mappings if "graphql" in m.requirement_text.lower() or "kafka" in m.requirement_text.lower()]
    if missing_pref:
        assert missing_pref[0].status == EvidenceMatchStatus.MISSING
        assert len(missing_pref[0].matched_evidence_units) == 0


ML_SPECIALIST_JD = """
Machine Learning Engineer - Computer Vision & Generative AI
Department: Research & Engineering | Location: San Francisco, CA

ABOUT THE ROLE
We are looking for a Machine Learning Engineer to build state-of-the-art vision models.

BASIC QUALIFICATIONS
• BS, MS, or PhD in Computer Science, AI, or related field.
• 3+ years experience with PyTorch, Python, and OpenCV.
• Proven track record training deep learning models on large datasets.

PREFERRED QUALIFICATIONS
• Experience with CUDA kernel optimization and TensorRT deployment.
• Publications in CVPR, ICCV, or NeurIPS is a plus.

DAY TO DAY RESPONSIBILITIES
• Design, train, and deploy real-time computer vision models for edge devices.
• Build automated ETL pipelines for video telemetry dataset curation.
• Collaborate with backend engineers to integrate REST APIs.

DESIRED TRAITS
• Strong analytical thinking, problem solving, and cross-functional communication.
"""

def test_ml_specialist_jd_taxonomy():
    reqs = analyze_job_description(ML_SPECIALIST_JD)
    
    assert "Machine Learning" in reqs.job_title
    assert reqs.domain == "AI & Machine Learning"
    assert "python" in [s.lower() for s in reqs.required_skills]
    assert "pytorch" in [s.lower() for s in reqs.required_skills]
    assert any("Computer Vision" in d or "Deep Learning" in d for d in reqs.domain_terminology)
    assert len(reqs.responsibilities) >= 2
    assert len(reqs.qualifications) >= 1
    assert "communication" in [s.lower() for s in reqs.soft_skills] or "problem solving" in [s.lower() for s in reqs.soft_skills]

def test_inline_prose_requirement_headings_keep_explicit_and_inferred_evidence_distinct():
    from app.modules.jobs.taxonomy import RequirementCategory, analyze_job_description

    text = (
        "What you'll doDesign and maintain production Python services.\n"
        "What we're looking for (must-have)Strong professional experience building software with Python and Git.\n"
        "Nice-to-haveExperience with Kubernetes."
    )
    parsed = analyze_job_description(text, "Platform Engineer")
    assert "Python" in parsed.must_have_skills
    assert "Git" in parsed.must_have_skills
    assert "Kubernetes" in parsed.preferred_skills
    assert any(req.evidence_type == "EXPLICIT" and req.category == RequirementCategory.MUST_HAVE for req in parsed.requirements)
    assert any(req.evidence_type == "INFERRED" and req.category == RequirementCategory.RESPONSIBILITY for req in parsed.requirements)


def test_bare_inline_preferred_heading_keeps_skill_list_out_of_required_skills():
    text = (
        "## Must-have\nExperience with Python and numerical methods.\n"
        "Preferred: PyTorch, NumPy, SciPy, Bayesian optimization, and HPC."
    )
    parsed = analyze_job_description(text, "Applied ML Research Engineer")

    assert "Python" in parsed.must_have_skills
    assert {"PyTorch", "NumPy", "SciPy"}.issubset(set(parsed.preferred_skills))
    assert not {"PyTorch", "NumPy", "SciPy"}.intersection(parsed.must_have_skills)
    assert any(row.category == RequirementCategory.PREFERRED for row in parsed.requirements)


def test_role_overview_requirement_predicate_is_explicit_but_technology_mentions_are_not():
    text = (
        "## Job Description\n"
        "The role works with Python and Linux services.\n"
        "Candidates should have strong experience with Java and PostgreSQL.\n"
        "## Responsibilities\n"
        "Build and maintain software using Docker."
    )
    parsed = analyze_job_description(text, "Platform Engineer")

    explicit_rows = [row for row in parsed.requirements if row.evidence_type == "EXPLICIT"]
    inferred_rows = [row for row in parsed.requirements if row.evidence_type == "INFERRED"]
    assert any("Java" in row.skills_detected and "PostgreSQL" in row.skills_detected for row in explicit_rows)
    assert any(row.category == RequirementCategory.RESPONSIBILITY and "Docker" in row.skills_detected for row in inferred_rows)
    assert "Java" in parsed.must_have_skills
    assert "PostgreSQL" in parsed.must_have_skills


def test_unclassified_jd_does_not_receive_a_default_software_domain():
    from app.modules.jobs.taxonomy import analyze_job_description

    assert analyze_job_description("We value curiosity and communication.").domain is None


def test_inline_mixed_requirements_are_split_with_local_provenance():
    text = (
        "## Job Description\n"
        "The team uses Kafka and Python in its internal tools. Must-have Experience with Linux. "
        "Nice-to-have Experience with Kubernetes. Responsibilities: Design and maintain reliable services."
    )
    parsed = analyze_job_description(text, "Platform Engineer")
    explicit = [row for row in parsed.requirements if row.evidence_type == "EXPLICIT"]
    inferred = [row for row in parsed.requirements if row.evidence_type == "INFERRED"]

    assert parsed.must_have_skills == ["Linux"]
    assert parsed.preferred_skills == ["Kubernetes"]
    assert all(row.category == RequirementCategory.MUST_HAVE for row in explicit if "Linux" in row.skills_detected)
    assert all(row.category == RequirementCategory.PREFERRED for row in explicit if "Kubernetes" in row.skills_detected)
    assert all("Kafka" not in row.skills_detected and "Python" not in row.skills_detected for row in explicit)
    assert any(row.category == RequirementCategory.RESPONSIBILITY and row.text.startswith("Design and maintain") for row in inferred)


def test_ambiguous_technology_mentions_remain_unclassified():
    parsed = analyze_job_description(
        "## Job Description\nThe team uses Python, Kafka, and Kubernetes across its services.",
        "Platform Engineer",
    )

    assert parsed.must_have_skills == []
    assert parsed.preferred_skills == []
    assert not any(row.evidence_type == "EXPLICIT" for row in parsed.requirements)


def test_missing_skill_requirements_are_not_invented():
    parsed = analyze_job_description(
        "## Job Description\nBuild and maintain reliable internal products.",
        "Software Engineer",
    )

    assert parsed.must_have_skills == []
    assert parsed.preferred_skills == []
    assert not any(row.category in (RequirementCategory.MUST_HAVE, RequirementCategory.PREFERRED) for row in parsed.requirements)
