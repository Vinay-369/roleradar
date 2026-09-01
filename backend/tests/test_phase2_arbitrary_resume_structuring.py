"""
Comprehensive Phase 2 Tests for Arbitrary Extracted Resume Text Recovery into Canonical CandidateProfile.
Tests malformed bullets, replacement characters, standalone bullet markers, wrapped lines,
long paragraphs, unusual headings, multi-page artifacts, inconsistent dates, and missing sections.
"""
import pytest
from app.modules.resume.models import CandidateProfile, ClaimType
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    structure_resume_text,
)

# 1. Multi-page messy resume with replacement chars, standalone bullets, and unusual headings
MESSY_MULTIPAGE_RESUME = """
JOHNATHAN DOE
New York, NY | jdoe@example.com | (212) 555-0199 | github.com/jdoe | linkedin.com/in/jdoe

SUMMARY OF QUALIFICATIONS
Senior distributed systems engineer with 8+ years building high-throughput financial infrastructure.
\x0c
Page 1 of 2

TECH EXPERTISE
Languages: Python, Go, C++, SQL, Rust
Frameworks & Tools: Docker, Kubernetes, Kafka, Redis, PostgreSQL, AWS, Terraform

CAREER BACKGROUND
Principal Engineer at Apex FinTech (03/2021 - Present) - New York, NY

Architected real-time order matching engine processing 250,000 orders/sec with sub-millisecond p99 latency.

Led a high-performing squad of 8 engineers across 3 geographic regions.

Senior Systems Engineer at CloudMatrix Corp (2017 - 2021) - Jersey City, NJ
> Built high-availability distributed cache layer using Redis and Go, improving hit ratios by 40%.
~ Spearheaded cloud migration from on-premise datacenter to AWS EKS, reducing hosting costs by $350k annually.

SOFTWARE PROJECTS
• Distributed Consensus Engine (Go, Raft)
Technologies: Go, Raft, gRPC
Engineered distributed consensus protocol handling cluster leader elections and state machine replication.

• Crypto Portfolio Tracker
Technologies: Python, FastAPI, React
Built automated crypto portfolio tracking dashboard with real-time WebSocket price updates.

DEGREES & EDUCATION
Columbia University in the City of New York
Master of Science in Computer Science (2015 - 2017) | GPA: 3.9 / 4.0

Page 2 of 2
"""

# 2. Unheaded prose narrative resume with long paragraphs and wrapped lines
UNHEADED_PROSE_RESUME = """
MARIA GONZALEZ
San Francisco, CA | maria@example.com | +1 415 555 9012

Dedicated software engineer specializing in backend systems, databases, and microservices architecture.
At TechStream Innovations from 2020 to Present, served as Lead Backend Engineer where I architected the core video streaming API using Python, FastAPI, and Redis serving over 2 million active mobile clients. Optimized database queries and indexes on PostgreSQL, reducing average query execution times by 55%.
Prior to this, worked at DataFlow Systems (2018 - 2020) building ETL data pipelines in Python and Apache Spark processing 15 TB of daily telemetry logs with 99.99% uptime.

PROJECT WORK
• AI Audio Enhancer (PyTorch, C++): Built deep learning audio de-noising model achieving 18dB SNR improvement.
• OpenSync File Manager (Rust, SQLite): Engineered cross-platform local sync engine with AES-256 encryption.

ACADEMIC HISTORY
University of California, Berkeley
B.S. in Electrical Engineering and Computer Sciences (2014 - 2018)
"""

# 3. Fresher student resume with missing experience, unusual headings, and academic tabular formats
FRESHER_STUDENT_RESUME = """
VIKAS K
Davangere, Karnataka | vikas@example.com | +91 9876543210 | github.com/vikas-dev

PERSONAL PROFILE
Aspiring Software and Machine Learning Engineer eager to contribute to innovative AI and full-stack software development.

TECHNICAL PROFICIENCIES
Programming Languages: Java, Python, C
Frameworks & Web: React, Node.js, Express, Flask, FastAPI, MongoDB, PostgreSQL

SCHOLASTIC RECORD
Bapuji Institute of Engineering and Technology, Davangere
B.E in Computer Science and Engineering (2023 - 2027) | CGPA: 9.1 / 10.0

DRM Science PU College, Davangere
Pre-University Course (PCMB) (2021 - 2023) | Percentage: 94%

KEY INITIATIVES
• AI-Based Ad Viral Potential Analyzer: Built predictive machine learning pipeline using Flask and OpenCV achieving 91% accuracy across 10,000 ad samples.
• ShopVerse E-Commerce: Developed full-stack e-commerce marketplace using React, Node.js, and Stripe payment integration.
• Cataract Prediction System Using Deep Learning: Implemented CNN feature extraction pipeline using OpenCV and PyTorch.

TRAININGS & CERTIFICATIONS
• Smart India Hackathon (SIH) 2024
• Completed Python Programming Course - ScalerLanguages
Telugu, English, Kannada, Hindi
"""


def test_messy_multipage_resume_recovery():
    profile = extract_candidate_profile(MESSY_MULTIPAGE_RESUME)
    assert isinstance(profile, CandidateProfile)
    assert profile.personal["name"] == "JOHNATHAN DOE"
    assert profile.personal["email"] == "jdoe@example.com"

    # Verify Experience recovered despite unusual heading "CAREER BACKGROUND" and standalone bullet lines
    assert len(profile.experience) == 2
    apex_exp = next(e for e in profile.experience if "Apex" in e.company or "Apex" in e.role)
    assert any("250,000" in b for b in apex_exp.bullets)
    assert any("8 engineers" in b for b in apex_exp.bullets)

    # Verify Projects recovered despite "SOFTWARE PROJECTS" heading and "Technologies: ..." line
    assert len(profile.projects) == 2
    p1 = profile.projects[0]
    assert "Distributed Consensus Engine" in p1.title
    assert "Go" in p1.tech_stack or "Raft" in p1.tech_stack

    # Verify Education recovered despite "DEGREES & EDUCATION" heading and multi-page artifacts
    assert len(profile.education) >= 1
    assert "Columbia University" in profile.education[0].institution

    # Verify EvidenceUnits retain metrics
    metric_evs = [ev for ev in profile.evidence_units if ev.claim_type == ClaimType.METRIC]
    assert len(metric_evs) >= 2
    assert any("250,000" in ev.original_text for ev in metric_evs)
    assert any("$350k" in ev.original_text for ev in metric_evs)


def test_unheaded_prose_resume_recovery():
    profile = extract_candidate_profile(UNHEADED_PROSE_RESUME)
    assert isinstance(profile, CandidateProfile)
    assert profile.personal["name"] == "MARIA GONZALEZ"
    assert profile.personal["email"] == "maria@example.com"

    # Verify projects recovered under "PROJECT WORK"
    assert len(profile.projects) == 2
    assert "AI Audio Enhancer" in profile.projects[0].title
    assert "OpenSync File Manager" in profile.projects[1].title
    assert any("18dB" in b for b in profile.projects[0].bullets)

    # Verify education recovered under "ACADEMIC HISTORY"
    assert len(profile.education) >= 1
    assert "University of California, Berkeley" in profile.education[0].institution

    # Verify backward compatible dictionary export
    parsed_dict = profile.to_parsed_dict()
    assert "personal" in parsed_dict
    assert "projects_raw" in parsed_dict
    assert "education_raw" in parsed_dict


def test_fresher_student_regression_and_glued_languages():
    profile = extract_candidate_profile(FRESHER_STUDENT_RESUME)
    assert isinstance(profile, CandidateProfile)
    assert profile.personal["name"] == "VIKAS K"

    # 1. Verify Education Degree preservation ("B.E" not corrupted)
    assert len(profile.education) >= 1
    assert "Bapuji Institute of Engineering and Technology" in profile.education[0].institution
    assert "B.E in Computer Science" in profile.education[0].degree or "B.E" in profile.education[0].degree

    # 2. Verify Projects preserved ("AI-Based" and "Cataract" titles intact)
    assert len(profile.projects) == 3
    proj_titles = [p.title for p in profile.projects]
    assert any("AI-Based Ad Viral Potential Analyzer" in t for t in proj_titles)
    assert any("Cataract Prediction System" in t for t in proj_titles)
    assert any("ShopVerse E-Commerce" in t for t in proj_titles)

    # 3. Verify Certifications & Spoken Languages split cleanly
    assert "Smart India Hackathon (SIH) 2024" in profile.certifications
    assert any("Scaler" in c for c in profile.certifications)
    assert set(profile.languages) == {"Telugu", "English", "Kannada", "Hindi"}

    # 4. Spoken languages must never contaminate programming languages
    assert "Java" not in profile.languages
    assert "Python" not in profile.languages
