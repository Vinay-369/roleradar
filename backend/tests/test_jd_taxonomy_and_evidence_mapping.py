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

