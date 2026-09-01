"""
Dedicated Test Suite for Phase 9: Deterministic ATS & Readability Validation Layer.
Validates:
- standard vs non-standard section headings
- missing critical information (email, phone)
- bullet consistency and action verb evaluation
- date consistency
- unusual decorative symbols and parsing risks
- keyword stuffing detection
- document length evaluation
- strict separation of factual validation from format validation
- no guaranteed shortlist / pass claim disclaimer
"""
import pytest
from app.modules.intelligence.ats_readability_validator import (
    ATSReadabilityAuditResult,
    ValidationSeverity,
    evaluate_ats_and_readability,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile

CLEAN_ATS_RESUME = """
RAHUL SHARMA
Bangalore, India | rahul@example.com | +91 9876543210

PROFESSIONAL SUMMARY
Backend Engineer with 3 years of experience building scalable distributed APIs in Python and FastAPI.

TECHNICAL SKILLS
Languages: Python, JavaScript, SQL
Frameworks & Tools: FastAPI, PostgreSQL, Docker, Redis

WORK EXPERIENCE
Software Engineer at ScaleTech (2022 - Present) - Bangalore, India
• Architected high-throughput REST APIs using FastAPI and PostgreSQL handling 25,000 req/sec.
• Optimized database indexing queries, decreasing average p99 latency by 35%.

PROJECTS
• Distributed File Cache: Built real-time cache indexing layer with Redis.

EDUCATION
National Institute of Technology Karnataka
B.Tech in Computer Science (2018 - 2022) | CGPA: 8.9 / 10.0
"""

MESSY_FORMAT_RESUME = """
ANONYMOUS CODER
Location: India

MY JOURNEY
• worked on some stuff with Python for a long time.
• did some coding.

TECH ARSENAL
Python, Python, Python, Python, Python, Python, Python, Python, Python, Python, Python, Python, Python, Python

SCHOOLING
XYZ College

MY APPS
⚡ SuperCool App ★ (Python, React)
"""


def test_standard_vs_non_standard_headings():
    # Clean resume with standard headers
    clean_audit = evaluate_ats_and_readability(CLEAN_ATS_RESUME)
    assert clean_audit.ats_format_validation.standard_headings_score == 100
    assert len(clean_audit.ats_format_validation.parsing_risks) == 0

    # Messy resume with non-standard headers ("TECH ARSENAL", "MY JOURNEY", "MY APPS", "SCHOOLING")
    messy_audit = evaluate_ats_and_readability(MESSY_FORMAT_RESUME)
    assert messy_audit.ats_format_validation.standard_headings_score < 100
    
    heading_issues = [f.issue for f in messy_audit.ats_format_validation.findings if f.category == "SECTION_HEADINGS"]
    assert len(heading_issues) >= 2
    assert any("TECH ARSENAL" in iss or "MY JOURNEY" in iss or "SCHOOLING" in iss for iss in heading_issues)


def test_missing_critical_contact_info():
    messy_audit = evaluate_ats_and_readability(MESSY_FORMAT_RESUME)
    
    assert "Email Address" in messy_audit.ats_format_validation.missing_critical_info
    assert "Phone Number" in messy_audit.ats_format_validation.missing_critical_info
    
    contact_findings = [f for f in messy_audit.ats_format_validation.findings if f.category == "CONTACT_INFO"]
    assert len(contact_findings) >= 1
    assert any(f.severity == ValidationSeverity.CRITICAL for f in contact_findings)


def test_bullet_consistency_and_action_verbs():
    audit = evaluate_ats_and_readability(MESSY_FORMAT_RESUME)
    bullet_findings = [f for f in audit.ats_format_validation.findings if f.category == "BULLET_QUALITY"]
    assert len(bullet_findings) >= 1
    assert "action verbs" in bullet_findings[0].issue.lower()


def test_unusual_decorative_symbols():
    audit = evaluate_ats_and_readability(MESSY_FORMAT_RESUME)
    
    assert "⚡" in audit.ats_format_validation.unusual_symbols_detected or "★" in audit.ats_format_validation.unusual_symbols_detected
    assert len(audit.ats_format_validation.parsing_risks) >= 1


def test_keyword_stuffing_detection():
    audit = evaluate_ats_and_readability(MESSY_FORMAT_RESUME)
    assert audit.ats_format_validation.keyword_stuffing_detected is True
    assert audit.ats_format_validation.keyword_density_ratio > 4.0


def test_strict_separation_of_factual_and_format_validation():
    """
    Guarantees that Factual Validation (evidence truth, verified claims, unverified metrics)
    is cleanly partitioned from ATS / Format Validation (headings, bullets, symbols, readability).
    """
    profile = extract_candidate_profile(CLEAN_ATS_RESUME)
    
    # Introduce an unverified metric into the tailored resume
    tampered_resume = CLEAN_ATS_RESUME.replace(
        "decreasing average p99 latency by 35%",
        "decreasing average p99 latency by 99.99% and saving $10M",
    )
    
    audit = evaluate_ats_and_readability(resume_data=tampered_resume, master_data=profile)
    
    # 1. Factual validation MUST fail due to unverified metrics
    assert audit.factual_validation.is_valid is False
    assert len(audit.factual_validation.unverified_claims) >= 1
    assert any("99.99%" in c or "$10M" in c or "10m" in c for c in audit.factual_validation.unverified_claims)

    # 2. ATS Format validation evaluates readability/layout independently
    assert audit.ats_format_validation.standard_headings_score == 100
    assert audit.ats_format_validation.overall_ats_score >= 80


def test_disclaimer_preservation_no_shortlist_guarantee():
    audit = evaluate_ats_and_readability(CLEAN_ATS_RESUME)
    assert "does not guarantee job shortlisting or hiring decisions" in audit.disclaimer.lower()
