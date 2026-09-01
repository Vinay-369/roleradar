"""
Tests for Phase 1 Canonical CandidateProfile, Entity Models, and EvidenceUnit Provenance.
"""
import pytest
from app.modules.resume.models import (
    CandidateProfile,
    ClaimType,
    EvidenceUnit,
    ProjectEntity,
    WorkExperienceEntity,
)
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    structure_resume_text,
)

SAMPLE_RESUME = """
ALEX R
Bangalore, India | alex@example.com | +91 9876543210 | github.com/alex-dev

PROFESSIONAL SUMMARY
Senior Full Stack Engineer with 5+ years of experience building distributed systems and high-throughput APIs.

TECHNICAL SKILLS
Languages: Python, Go, TypeScript, SQL
Frameworks: FastAPI, React, Docker, Kubernetes, PostgreSQL, Redis

WORK EXPERIENCE
Senior Backend Engineer at CloudScale Technologies (2022 - Present) - Bangalore
• Architected asynchronous task processing queue handling 10,000+ jobs per minute using Redis and Celery, reducing latency by 45%.
• Led a team of 4 engineers to migrate monolith to microservices on AWS EKS.

Software Engineer at DataTech Solutions (2019 - 2022) - Hyderabad
• Developed RESTful APIs using Python and PostgreSQL serving 50,000 daily active users.
• Optimized database indexing queries, improving query throughput by 35%.

TECHNICAL PROJECTS
• AI Document Classifier: Built automated document indexing pipeline using Python, PyTorch, and FastAPI achieving 94% accuracy.
• ShopEase Microservices (Docker, React, Go): Engineered real-time payment gateway integration processing $500k monthly transactions.

EDUCATION
National Institute of Technology Karnataka
B.Tech in Computer Science and Engineering (2015 - 2019) | CGPA: 8.9 / 10.0

CERTIFICATIONS
• AWS Certified Solutions Architect - Associate (2023)
• Certified Kubernetes Administrator (CKA)
"""


def test_extract_candidate_profile_structure_and_provenance():
    profile = extract_candidate_profile(SAMPLE_RESUME)

    assert isinstance(profile, CandidateProfile)
    assert profile.personal["name"] == "ALEX R"
    assert profile.personal["email"] == "alex@example.com"
    assert "bangalore" in profile.personal["location"].lower()

    # Verify Experience Entities
    assert len(profile.experience) >= 1
    assert any("CloudScale" in exp.company or "CloudScale" in exp.role for exp in profile.experience)

    # Verify Project Entities & Preservation
    assert len(profile.projects) == 2
    proj1 = profile.projects[0]
    assert "AI Document Classifier" in proj1.title
    assert len(proj1.bullets) >= 1
    assert any("94%" in b for b in proj1.bullets)

    proj2 = profile.projects[1]
    assert "ShopEase" in proj2.title
    assert any("$500k" in b for b in proj2.bullets)

    # Verify EvidenceUnits & Provenance
    assert len(profile.evidence_units) >= 4
    metrics_evs = [ev for ev in profile.evidence_units if ev.claim_type == ClaimType.METRIC]
    assert len(metrics_evs) >= 2
    assert any("45%" in ev.original_text for ev in metrics_evs)
    assert any("94%" in ev.original_text for ev in metrics_evs)

    # Verify backward compatible dict conversion
    parsed_dict = profile.to_parsed_dict()
    assert "personal" in parsed_dict
    assert "skills" in parsed_dict
    assert "experience_raw" in parsed_dict
    assert "projects_raw" in parsed_dict
    assert "education_raw" in parsed_dict
    assert "certifications" in parsed_dict


def test_candidate_profile_json_serialization_and_deserialization():
    profile = extract_candidate_profile(SAMPLE_RESUME)
    json_str = profile.model_dump_json()
    assert isinstance(json_str, str)
    assert len(json_str) > 100

    # Deserialize from JSON
    restored = CandidateProfile.model_validate_json(json_str)
    assert restored.personal["name"] == profile.personal["name"]
    assert len(restored.projects) == len(profile.projects)
    assert len(restored.evidence_units) == len(profile.evidence_units)


def test_candidate_profile_from_parsed_dict_roundtrip():
    # Parse resume into traditional parsed dict
    parsed = structure_resume_text(SAMPLE_RESUME)
    assert isinstance(parsed, dict)

    # Reconstruct canonical CandidateProfile from parsed dict
    profile = CandidateProfile.from_parsed_dict(parsed)
    assert isinstance(profile, CandidateProfile)
    assert profile.personal["name"] == "ALEX R"
    assert len(profile.projects) >= 1
    assert len(profile.evidence_units) >= 1

    # Convert back to parsed dict
    exported_dict = profile.to_parsed_dict()
    assert exported_dict["personal"]["name"] == "ALEX R"
    assert len(exported_dict["skills"]) == len(parsed["skills"])


def test_each_entity_retains_its_own_evidence():
    profile = extract_candidate_profile(SAMPLE_RESUME)
    
    # Check that each project entity contains its own evidence units
    for proj in profile.projects:
        assert len(proj.evidence_units) == len(proj.bullets)
        for ev in proj.evidence_units:
            assert ev.entity_id == proj.id
            assert ev.section == "PROJECTS"

    # Check that each experience entity contains its own evidence units
    for exp in profile.experience:
        for ev in exp.evidence_units:
            assert ev.entity_id == exp.id
            assert ev.section == "EXPERIENCE"


def test_generalized_candidate_profile_sections_and_lookups():
    from app.modules.resume.models import AdditionalSectionEntity

    profile_data = {
        "personal": {"name": "Jordan Lee", "email": "jordan@example.com"},
        "summary": "Accomplished AI researcher and engineering leader.",
        "skills": ["Python", "PyTorch", "Distributed Systems"],
        "publications": ["Scaling Deep Transformers on 10,000 GPUs (NeurIPS 2024)"],
        "research": ["Principal Investigator on Efficient Attention Mechanisms"],
        "leadership": ["Chair, University Open Source Club (2022 - 2024)"],
        "volunteer": ["Volunteer STEM Instructor at CodeKids"],
        "additional_sections": [
            {
                "id": "patents_sec",
                "heading": "Patents",
                "items": ["US Patent 11,234,567: Adaptive Network Routing via Graph Neural Nets"],
            }
        ],
        "experience_raw": ["TechCorp", "Lead AI Engineer (2022 - Present)", "• Spearheaded next-gen model serving platform reducing latency by 50%."],
        "projects_raw": [
            {
                "title": "TorchScale",
                "tech_stack": "PyTorch, CUDA",
                "bullets": ["Engineered parallel training framework scaling to 256 nodes."],
            }
        ],
    }

    profile = CandidateProfile.from_parsed_dict(profile_data)

    # 1. Verify generalized fields
    assert profile.publications == ["Scaling Deep Transformers on 10,000 GPUs (NeurIPS 2024)"]
    assert profile.research == ["Principal Investigator on Efficient Attention Mechanisms"]
    assert profile.leadership == ["Chair, University Open Source Club (2022 - 2024)"]
    assert profile.volunteer == ["Volunteer STEM Instructor at CodeKids"]
    assert len(profile.additional_sections) == 1
    assert profile.additional_sections[0].heading == "Patents"

    # 2. Verify professional_experience alias
    assert profile.professional_experience == profile.experience
    assert len(profile.professional_experience) == 1
    assert profile.professional_experience[0].organization == profile.professional_experience[0].company

    # 3. Verify evidence lookup helpers
    exp_evs = profile.find_evidence_units(section="EXPERIENCE")
    assert len(exp_evs) >= 1
    assert any("50%" in ev.text for ev in exp_evs)

    first_ev_id = exp_evs[0].id
    found_ev = profile.get_evidence_by_id(first_ev_id)
    assert found_ev is not None
    assert found_ev.id == first_ev_id

    # 4. Verify additional sections generated evidence units
    add_evs = profile.find_evidence_units(section="ADDITIONAL")
    assert len(add_evs) == 1
    assert "US Patent" in add_evs[0].text

    # 5. Verify roundtrip to parsed dict preserves all generalized sections
    exported = profile.to_parsed_dict()
    assert exported["publications"] == profile.publications
    assert exported["research"] == profile.research
    assert exported["leadership"] == profile.leadership
    assert exported["volunteer"] == profile.volunteer
    assert len(exported["additional_sections"]) == 1
    assert exported["additional_sections"][0]["heading"] == "Patents"


def test_arbitrary_structure_fresher_projects_only_no_experience():
    """Validates student/fresher resumes with zero work experience and projects only."""
    fresher_data = {
        "personal": {"name": "Priya Sharma", "email": "priya@example.edu", "phone": "+91 9123456780"},
        "summary": None,  # Missing summary
        "skills": ["Python", "C++", "PyTorch", "SQL"],
        "skills_categorized": ["Languages: Python, C++", "Frameworks: PyTorch"],
        "experience_raw": [],
        "projects_raw": [
            {
                "title": "Autonomous Drone Navigation",
                "tech_stack": "PyTorch, ROS, OpenCV",
                "bullets": [
                    "Implemented vision-based obstacle avoidance achieving 96% detection rate at 30 FPS.",
                    "Reduced sensor processing latency from 120ms to 45ms using CUDA acceleration.",
                ],
            },
            {
                "title": "Campus Marketplace App",
                "tech_stack": "React Native, Firebase",
                "bullets": ["Developed real-time chat and payment system supporting 2,500 active student users."],
            },
        ],
        "education_raw": [
            {
                "institution": "Indian Institute of Technology Madras",
                "degree": "B.Tech in Computer Science",
                "dates": "2021 - 2025",
                "cgpa": "9.2/10.0",
            }
        ],
        "certifications": ["Deep Learning Specialization (Coursera)"],
        "achievements": ["1st Place, National AI Hackathon 2024"],
    }

    profile = CandidateProfile.from_parsed_dict(fresher_data)

    assert len(profile.experience) == 0
    assert len(profile.projects) == 2
    assert profile.summary is None
    assert len(profile.evidence_units) == 3

    # Stable evidence unit IDs
    proj_evs = profile.find_evidence_units(section="PROJECTS")
    assert len(proj_evs) == 3
    assert all(ev.id.startswith("PROJ_") for ev in proj_evs)
    assert any("96%" in ev.text for ev in proj_evs)
    assert any("45ms" in ev.text for ev in proj_evs)

    # Serialization test
    serialized = profile.model_dump_json()
    deserialized = CandidateProfile.model_validate_json(serialized)
    assert len(deserialized.experience) == 0
    assert len(deserialized.projects) == 2
    assert deserialized.personal["name"] == "Priya Sharma"


def test_arbitrary_structure_multi_role_promotions_and_responsibility_groups():
    """Validates multi-role progression and sub-responsibility headings under a single employer."""
    hierarchical_data = {
        "personal": {"name": "Akhil Rana", "email": "akhil@example.com"},
        "summary": "Engineering Leader with 8+ years experience scaling cloud infrastructure.",
        "skills": ["Go", "Kubernetes", "Distributed Systems", "AWS"],
        "experience_raw": [
            "Tech Enterprise Corp",
            "Staff Software Engineer (2022 - Present)",
            "Senior Software Engineer (2020 - 2022)",
            "Software Engineer (2018 - 2020)",
            "Bangalore, India",
            "Core Infrastructure:",
            "• Architected multi-region Kubernetes control plane managing 5,000+ nodes with 99.99% uptime.",
            "• Reduced cloud infrastructure spend by $350k annually through automated autoscaling policies.",
            "Developer Experience:",
            "• Built internal deployment CLI adopted by 300+ engineers, cutting release cycles from 3 hours to 10 minutes.",
        ],
        "projects_raw": [],
        "education_raw": [{"institution": "BITS Pilani", "degree": "B.E. Computer Science", "dates": "2014 - 2018"}],
    }

    profile = CandidateProfile.from_parsed_dict(hierarchical_data)

    assert len(profile.experience) == 1
    exp = profile.experience[0]
    assert "Tech Enterprise" in exp.company
    assert len(exp.progression) == 3
    assert exp.progression[0].title == "Staff Software Engineer"
    assert exp.progression[1].title == "Senior Software Engineer"
    assert exp.progression[2].title == "Software Engineer"
    assert len(exp.responsibility_groups) == 2
    assert "Core Infrastructure" in exp.responsibility_groups[0].heading
    assert "Developer Experience" in exp.responsibility_groups[1].heading

    # Evidence Units check
    exp_evs = profile.find_evidence_units(section="EXPERIENCE")
    assert len(exp_evs) == 3
    assert any("99.99%" in ev.text for ev in exp_evs)
    assert any("$350k" in ev.text for ev in exp_evs)
    assert any("3 hours to 10 minutes" in ev.text for ev in exp_evs)


def test_arbitrary_structure_unknown_sections_and_zero_information_loss():
    """Validates that unusual sections (e.g. Grants, Teaching, Speaking, Patents) are 100% preserved."""
    academic_data = {
        "personal": {"name": "Dr. Sarah Lin", "email": "sarah.lin@stanford.edu"},
        "summary": "Postdoctoral Researcher in Quantum Computing algorithms.",
        "skills": ["Qiskit", "Python", "Quantum Error Correction", "Linear Algebra"],
        "publications": ["Fault-Tolerant Surface Codes on 100-Qubit Processors (Nature Physics 2025)"],
        "research": ["Principal Investigator on Topological Qubit Simulation Grant"],
        "leadership": ["Co-chair, IEEE Quantum Computing Workshop 2024"],
        "volunteer": ["Mentor, Women in Physics Society"],
        "additional_sections": [
            {
                "id": "grants_01",
                "heading": "Research Grants & Funding",
                "semantic_type": "GRANTS",
                "items": ["DOE Quantum Information Science Grant ($1.2M, 2023 - 2026)"],
                "text": "DOE Quantum Information Science Grant ($1.2M, 2023 - 2026)",
            },
            {
                "id": "teaching_01",
                "heading": "Teaching Experience",
                "semantic_type": "TEACHING",
                "items": ["Head TA, CS 269: Advanced Quantum Algorithms (Fall 2023, 120 students)"],
                "text": "Head TA, CS 269: Advanced Quantum Algorithms (Fall 2023, 120 students)",
            },
        ],
        "experience_raw": ["Stanford University", "Postdoctoral Fellow (2022 - Present)", "• Developed error decoding algorithm reducing logical error rate by 40%."],
        "projects_raw": [],
        "education_raw": [{"institution": "MIT", "degree": "Ph.D. in Physics", "dates": "2017 - 2022"}],
    }

    profile = CandidateProfile.from_parsed_dict(academic_data)

    # Check custom sections
    assert len(profile.additional_sections) == 2
    assert profile.additional_sections[0].heading == "Research Grants & Funding"
    assert profile.additional_sections[0].semantic_type == "GRANTS"
    assert profile.additional_sections[1].heading == "Teaching Experience"
    assert profile.additional_sections[1].semantic_type == "TEACHING"

    # Check that evidence units were created with provenance
    grant_ev = profile.get_evidence_by_id(profile.additional_sections[0].evidence_units[0].id)
    assert grant_ev is not None
    assert "$1.2M" in grant_ev.text
    assert grant_ev.section == "ADDITIONAL"

    # Check 100% round-trip fidelity
    exported = profile.to_parsed_dict()
    assert exported["personal"]["name"] == "Dr. Sarah Lin"
    assert len(exported["additional_sections"]) == 2
    assert exported["publications"] == profile.publications
    assert exported["research"] == profile.research
    assert exported["leadership"] == profile.leadership
    assert exported["volunteer"] == profile.volunteer

