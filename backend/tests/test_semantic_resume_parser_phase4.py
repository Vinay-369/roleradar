"""
Tests for Phase 4: General Semantic Resume Parser.
Validates generalized section detection, unheaded summary detection,
relationship reconstruction, wrapped evidence reconstitution,
custom section preservation, and deterministic structural validation.
"""
import pytest
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    structure_resume_text,
    validate_candidate_profile,
)
from app.modules.resume.parsing.document import NormalizedDocument


def test_generalized_semantic_section_detection():
    resume_text = """
    MORGAN VANCE
    morgan@example.com | +1 555-0188 | Boston, MA | github.com/mvance

    CAREER HISTORY
    Senior Cloud Architect at Nexus Systems (2021 - Present)
    • Architected multi-tenant Kubernetes platform handling 250M daily API events.
    • Reduced multi-region data replication latency by 65%.

    SOFTWARE PROJECTS
    HyperScale Cache (Go, Redis)
    • Built distributed in-memory cache supporting 1M concurrent connections.

    ACADEMIC QUALIFICATIONS
    B.S. in Computer Engineering, MIT, 2017 - 2021

    PEER-REVIEWED PUBLICATIONS
    • "High-Throughput Consensus Protocols in Hybrid Clouds", IEEE Cloud 2022.

    SCIENTIFIC RESEARCH
    • Investigated asynchronous replication guarantees in distributed transactional databases.

    COMMUNITY LEADERSHIP
    • Organizer for Boston Go Users Meetup with 1,200+ members.

    VOLUNTEER EXPERIENCE
    • Mentored underrepresented STEM high school students in algorithmic programming.

    HONORS & AWARDS
    • 1st Place National Distributed Systems Hackathon 2020.
    """

    profile = extract_candidate_profile(resume_text)

    # 1. Identity
    assert profile.identity.name == "MORGAN VANCE"
    assert profile.identity.email == "morgan@example.com"
    assert any("github.com/mvance" in link for link in profile.links) or "github.com/mvance" in (profile.identity.github or "")

    # 2. Career History -> experience
    assert len(profile.experience) == 1
    assert "Nexus Systems" in profile.experience[0].company
    assert len(profile.experience[0].evidence_units) == 2
    assert "250M daily API events" in profile.experience[0].evidence_units[0].text

    # 3. Software Projects -> projects
    assert len(profile.projects) == 1
    assert "HyperScale Cache" in profile.projects[0].title
    assert len(profile.projects[0].evidence_units) == 1

    # 4. Academic Qualifications -> education
    assert len(profile.education) == 1
    assert "MIT" in profile.education[0].institution or "MIT" in profile.education[0].raw_text

    # 5. Publications, Research, Leadership, Volunteer, Achievements
    assert len(profile.publications) == 1
    assert "High-Throughput Consensus Protocols" in profile.publications[0]

    assert len(profile.research) == 1
    assert "asynchronous replication guarantees" in profile.research[0]

    assert len(profile.leadership) == 1
    assert "Boston Go Users Meetup" in profile.leadership[0]

    assert len(profile.volunteer) == 1
    assert "Mentored underrepresented STEM" in profile.volunteer[0]

    assert len(profile.achievements) == 1
    assert "Distributed Systems Hackathon" in profile.achievements[0]


def test_unheaded_introductory_summary_detection():
    resume_text = """
    DR. SAMANTHA REID
    samantha.reid@example.com | Austin, TX

    Distinguished Distributed Systems Architect with 12+ years of experience leading engineering teams, designing fault-tolerant cloud backends, and scaling global infrastructure.

    TECHNICAL STACK
    Languages: Go, Rust, Python, C++
    Infrastructure: Kubernetes, Terraform, AWS, Kafka

    EMPLOYMENT
    Lead Infrastructure Engineer at DataMesh (2019 - Present)
    • Designed edge compute architecture serving 10M active endpoints.
    """

    profile = extract_candidate_profile(resume_text)

    assert profile.identity.name == "DR. SAMANTHA REID"
    assert profile.summary is not None
    assert "Distinguished Distributed Systems Architect" in profile.summary
    assert "12+ years of experience" in profile.summary
    assert len(profile.experience) == 1


def test_custom_unknown_section_preservation():
    resume_text = """
    JORDAN LEE
    jordan@example.com

    CORE COMPETENCIES
    Python, PyTorch, Ray, CUDA

    WORK EXPERIENCE
    AI Research Engineer at TensorLab (2022 - Present)
    • Optimized distributed model parallelism reducing training epoch duration by 30%.

    PATENTS & INVENTIONS
    • US Patent 11,234,567: Dynamic Attention Kernel Acceleration on Heterogeneous Compute.
    • US Patent 11,890,123: Zero-Overhead Memory Quantization for Edge LLMs.

    SPEAKING ENGAGEMENTS:
    • Keynote Speaker at Open Data Science Conference 2024.
    • Panelist on Scalable Machine Learning at NeurIPS Workshop 2023.
    """

    profile = extract_candidate_profile(resume_text)

    assert len(profile.experience) == 1
    assert len(profile.additional_sections) == 2

    # Verify custom sections preserved with headings and items
    patent_sec = next(s for s in profile.additional_sections if "patent" in s.heading.lower())
    assert len(patent_sec.items) == 2
    assert any("US Patent 11,234,567" in it for it in patent_sec.items)

    speaking_sec = next(s for s in profile.additional_sections if "speaking" in s.heading.lower())
    assert len(speaking_sec.items) == 2
    assert any("Keynote Speaker" in it for it in speaking_sec.items)


def test_wrapped_multiline_evidence_reconstruction():
    resume_text = """
    DEVON SHARP
    devon@example.com

    WORK EXPERIENCE
    Senior Backend Engineer at StreamTech (2020 - 2023)
    • Architected and deployed a highly reliable stream processing pipeline
      utilizing Apache Flink and Kafka that handled over 400,000 events
      per second with sub-10ms p99 latency across three AWS availability zones.
    • Spearheaded database partitioning strategy eliminating query timeouts.
    """

    profile = extract_candidate_profile(resume_text)

    assert len(profile.experience) == 1
    units = profile.experience[0].evidence_units

    assert len(units) == 2
    # Verify wrapped lines are unified into a single coherent EvidenceUnit
    assert "Apache Flink and Kafka" in units[0].text
    assert "400,000 events" in units[0].text
    assert "sub-10ms p99 latency" in units[0].text
    assert "Spearheaded database partitioning strategy" in units[1].text


def test_polymorphic_normalized_document_input():
    # Pass NormalizedDocument instance directly into extract_candidate_profile
    norm_doc = NormalizedDocument(
        full_text="CASEY ROWE\ncasey@example.com\n\nEXPERIENCE\nDevOps Engineer at CloudOps (2022 - Present)\n• Automated Terraform pipelines.",
        normalized_text="CASEY ROWE\ncasey@example.com\n\nEXPERIENCE\nDevOps Engineer at CloudOps (2022 - Present)\n• Automated Terraform pipelines.",
    )

    profile = extract_candidate_profile(norm_doc)

    assert profile.identity.name == "CASEY ROWE"
    assert profile.identity.email == "casey@example.com"
    assert len(profile.experience) == 1
    assert "CloudOps" in profile.experience[0].company
    assert len(profile.experience[0].evidence_units) == 1


def test_deterministic_structural_validation():
    # Profile with valid and missing fields
    profile = extract_candidate_profile("""
    TAYLOR REESE
    taylor@example.com

    WORK EXPERIENCE
    Software Engineer (2022 - Present)
    • Engineered GraphQL API microservices.

    PROJECTS
    • Implemented real-time dashboard in Next.js and Tailwind.
    """)

    issues = validate_candidate_profile(profile)

    # Empty company was assigned fallback
    assert profile.experience[0].company != ""
    # Project with no explicit title assigned fallback
    assert profile.projects[0].title != ""
    # No duplicate evidence IDs
    assert not any("Duplicate Evidence ID" in issue for issue in issues)
