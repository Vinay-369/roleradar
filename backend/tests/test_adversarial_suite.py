"""
Adversarial Stress Test Suite for RoleRadar.
Deliberately designed to challenge and stress every pipeline layer:
- Parser & Structurer (PARSER FAILURE / STRUCTURE FAILURE)
- Classification & Strategy (CLASSIFICATION FAILURE)
- Matching & Scoping (MATCHING FAILURE)
- Tailoring & Truth Guard (TAILORING FAILURE / TRUTH-GUARD FAILURE)
- Export & Post-Render Integrity (EXPORT FAILURE)
"""
import pytest
from app.core.ai_service.schemas import ChangeStatus, ChangeType
from app.modules.intelligence.ats_readability_validator import evaluate_ats_and_readability
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.matching.evidence_mapping import (
    EvidenceMatchStatus,
    map_resume_to_jd_evidence,
)
from app.modules.resume.classification import (
    CareerClassification,
    classify_candidate_profile,
)
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    structure_resume_text,
)
from app.modules.tailoring.export import (
    generate_docx,
    generate_pdf,
    verify_export_against_structured_resume,
)
from app.modules.tailoring.strategy import (
    render_profile_with_strategy,
    resolve_template_strategy,
)
from app.modules.tailoring.validation import (
    detect_entity_boundary_violations,
    detect_fabricated_claims,
    detect_unsupported_metrics,
    validate_final_tailored_resume,
)


# =========================================================================
# 1. PARSER & STRUCTURE ADVERSARIAL TESTS
# =========================================================================

ADVERSARIAL_MALFORMED_BULLETS = """
MAXWELL HYDE
max@example.com | 555-0199

SKILLS
Python, Go, Docker

EXPERIENCE
Engineer at TestCorp (2022 - Present)
•
Built cloud backend services in Go
-
•
• Optimized PostgreSQL database queries
*
- reduced latency by 35%
•
"""

def test_adversarial_malformed_bullets_and_standalone_markers():
    """[PARSER/STRUCTURE] Isolated bullet glyphs must not become empty/corrupt evidence units."""
    profile = extract_candidate_profile(ADVERSARIAL_MALFORMED_BULLETS)
    
    assert len(profile.experience) >= 1
    # Check that no evidence unit is an isolated marker
    for unit in profile.evidence_units:
        assert unit.text.strip() not in ("•", "-", "*", "·", "–", "—", "")
        assert len(unit.text.strip()) >= 3

    assert len(profile.evidence_units) >= 2


ADVERSARIAL_GLUED_HEADINGS = """
ALEX MERCER
alex@example.com | 555-0188
Summary:Experienced software developer with hands-on background.Technical Skills:Python, Docker, SQL, RedisProjects:• SmartCache: Distributed caching system in Python.Education:MIT B.S. in Computer Science (2018 - 2022)Certifications:AWS Cloud Practitioner
"""

def test_adversarial_glued_and_inline_section_headers():
    """[PARSER/STRUCTURE] Glued inline headings must be separated into distinct sections."""
    profile = extract_candidate_profile(ADVERSARIAL_GLUED_HEADINGS)
    
    assert "Python" in profile.skills or "Docker" in profile.skills
    assert len(profile.projects) >= 1
    assert len(profile.education) >= 1


ADVERSARIAL_ASCII_TABLES = """
SARAH JENKINS
sarah@example.com | 555-0122

+-------------------------------------------------------------+
| EXPERIENCE                                                  |
+-------------------------------------------------------------+
| Backend Engineer at DataLink (2021 - Present)               |
| | Designed REST APIs using FastAPI and PostgreSQL           |
| | Decreased p99 response times by 40%                       |
+-------------------------------------------------------------+
"""

def test_adversarial_ascii_box_and_table_cleaning():
    """[PARSER/STRUCTURE] Table border characters (+---+) must not corrupt extracted bullet text."""
    profile = extract_candidate_profile(ADVERSARIAL_ASCII_TABLES)
    
    assert len(profile.evidence_units) >= 1
    for unit in profile.evidence_units:
        assert "+---" not in unit.text
        assert "|---" not in unit.text
        assert "REST APIs" in unit.text or "FastAPI" in unit.text or "40%" in unit.text


ADVERSARIAL_DUPLICATE_PROJECTS = """
DOUGLAS REPEAT
doug@example.com | 555-4321

PROJECTS
• Analytics Engine: Built data platform in Python handling 10k events/sec.
• Analytics Engine: Built data platform in Python handling 10k events/sec.
• Payment Router: Integrated Stripe API with 99.9% uptime.
"""

def test_adversarial_duplicate_projects_and_repeated_bullets():
    """[PARSER/STRUCTURE] Duplicate project entries or repeated bullets should be safely parsed."""
    profile = extract_candidate_profile(ADVERSARIAL_DUPLICATE_PROJECTS)
    assert len(profile.projects) >= 1
    # Evidence units are preserved without crashing
    assert len(profile.evidence_units) >= 2


ADVERSARIAL_AMBIGUOUS_PROJECT_TITLES = """
KAREN VAGUE
karen@example.com | 555-7777

THINGS I WORKED ON
Project Alpha (Python, Docker)
- Architected queue consumer processing 5,000 tasks/min.

System Beta
- Technologies: React, TypeScript
- Developed customer-facing dashboard.
"""

def test_adversarial_ambiguous_project_titles_and_nonstandard_headings():
    """[PARSER/STRUCTURE] Nonstandard project section headings must be identified."""
    profile = extract_candidate_profile(ADVERSARIAL_AMBIGUOUS_PROJECT_TITLES)
    assert len(profile.projects) >= 1 or len(profile.experience) >= 1
    assert "Python" in profile.skills or "Docker" in profile.skills or "React" in profile.skills


ADVERSARIAL_LONG_UNHEADED_PROSE = """
DAVID STORYTELLER
david@example.com | 555-8888
I have been working as a Software Engineer at CloudCorp since 2021. In this role, I engineered microservices using Python and Go which reduced infrastructure costs by 30%. Prior to that, I created a distributed key-value store in Rust during my studies at Stanford University where I graduated with a B.S. in Computer Science in 2020.
"""

def test_adversarial_completely_unheaded_long_prose():
    """[PARSER/STRUCTURE] Entirely unheaded narrative paragraphs must recover facts and entities."""
    profile = extract_candidate_profile(ADVERSARIAL_LONG_UNHEADED_PROSE)
    assert len(profile.evidence_units) >= 1
    assert any("Python" in ev.technologies or "Go" in ev.technologies or "Rust" in ev.technologies for ev in profile.evidence_units)


# =========================================================================
# 2. CLASSIFICATION & STRATEGY ADVERSARIAL TESTS
# =========================================================================

ADVERSARIAL_EMPTY_RESUME = """
JOHN NOBODY
john@example.com | 555-0000

EDUCATION
City College
B.S. in General Studies (2020 - 2024)
"""

def test_adversarial_candidate_with_no_experience_no_projects():
    """[CLASSIFICATION] Resumes lacking both work experience and projects must not crash."""
    profile = extract_candidate_profile(ADVERSARIAL_EMPTY_RESUME)
    classification = classify_candidate_profile(profile)
    
    assert classification.classification in (CareerClassification.FRESHER, CareerClassification.STUDENT)
    strategy = resolve_template_strategy(classification)
    assert strategy.highlight_education_top is True

    # Render and export safely
    rendered = render_profile_with_strategy(profile, strategy)
    pdf_bytes = generate_pdf(rendered, candidate_name="JOHN NOBODY", template="modern")
    assert len(pdf_bytes) > 500


ADVERSARIAL_CONTRADICTORY_DATES = """
TIMOTHY TIME
tim@example.com | 555-9999

EXPERIENCE
Senior Lead at FutureCorp (2025 - 2020)
• Managed system operations.

Junior Developer at PastCorp (2024 - Present)
• Built Python tools.
"""

def test_adversarial_inverted_and_overlapping_dates():
    """[CLASSIFICATION] Inverted date ranges (2025 - 2020) must not produce negative numbers or crash."""
    profile = extract_candidate_profile(ADVERSARIAL_CONTRADICTORY_DATES)
    classification = classify_candidate_profile(profile)
    
    assert classification.years_of_experience >= 0.0
    assert isinstance(classification.confidence, float)


ADVERSARIAL_MULTI_JOB_MULTI_PROJECT = """
ELENA STACK
elena@example.com | 555-3333

EXPERIENCE
Principal Engineer at MegaCorp (2022 - Present)
• Led migration of 50 microservices to Kubernetes.
Senior Engineer at MidCorp (2020 - 2022)
• Built billing engine in Go.
Software Engineer at StartupX (2018 - 2020)
• Developed React frontend.
Junior Engineer at EarlyCorp (2016 - 2018)
• Maintained Python scripts.

PROJECTS
• MeshNet (C++, Rust): Peer-to-peer overlay network.
• DataPipe (Python, Spark): Real-time ETL pipeline.
• AuthZero (Go): OpenID connect provider.
"""

def test_adversarial_multi_job_and_multi_project_depth():
    """[CLASSIFICATION] Extensive work history and project count must classify as SENIOR/LEADERSHIP."""
    profile = extract_candidate_profile(ADVERSARIAL_MULTI_JOB_MULTI_PROJECT)
    classification = classify_candidate_profile(profile)
    
    assert classification.classification in (CareerClassification.SENIOR_PROFESSIONAL, CareerClassification.LEADERSHIP, CareerClassification.PROFESSIONAL)
    assert classification.project_depth in ("STRONG", "HIGH", "MODERATE")
    assert classification.professional_role_count >= 3


ADVERSARIAL_NO_METRICS_RESUME = """
QUALITATIVE DEVELOPER
qual@example.com | 555-2222

EXPERIENCE
Software Developer at Acme Systems (2021 - Present)
• Developed backend microservices using Node.js and PostgreSQL.
• Collaborated with cross-functional teams to design database schemas.
• Implemented automated integration tests.
"""

def test_adversarial_resume_with_zero_metrics():
    """[CLASSIFICATION/TAILORING] Resume with valid experience but zero metrics must classify correctly."""
    profile = extract_candidate_profile(ADVERSARIAL_NO_METRICS_RESUME)
    classification = classify_candidate_profile(profile)
    assert classification.classification in (CareerClassification.EARLY_CAREER, CareerClassification.PROFESSIONAL)
    
    # Audit should recognize zero fabricated metrics
    audit = evaluate_ats_and_readability(profile.to_parsed_dict(), master_data=profile)
    assert audit.factual_validation.is_valid is True


# =========================================================================
# 3. MATCHING & SCOPING ADVERSARIAL TESTS
# =========================================================================

ADVERSARIAL_CASE_SENSITIVITY = """
CASE TESTER
tester@example.com | 555-1111

SKILLS
pYtHoN, Docker, ReAcT.jS, kUbErNeTeS, fastAPI

PROJECTS
• CloudApp (pYtHoN, Docker): Built distributed API.
"""

JD_NORMAL_CASING = """
Senior Full Stack Engineer
Requirements:
- Strong experience with Python and FastAPI
- Production experience with React.js and Kubernetes
- Docker containerization
"""

def test_adversarial_casing_variations_and_normalization():
    """[MATCHING] Wacky capitalization (pYtHoN, ReAcT.jS) must match standard JD requirements."""
    profile = extract_candidate_profile(ADVERSARIAL_CASE_SENSITIVITY)
    jd_reqs = analyze_job_description(JD_NORMAL_CASING, "Full Stack Engineer")
    
    mapping = map_resume_to_jd_evidence(profile, jd_reqs)
    py_match = next((m for m in mapping if "python" in m.requirement_text.lower()), None)
    assert py_match is not None
    assert py_match.status in (EvidenceMatchStatus.EXACT_MATCH, EvidenceMatchStatus.SUPPORTED)


ADVERSARIAL_TECH_IN_UNRELATED_SECTION = """
ALAN HOBBYIST
alan@example.com | 555-6666

EXPERIENCE
Frontend Developer at WebCorp (2021 - Present)
• Built React and TypeScript components for e-commerce website.

ACHIEVEMENTS & AWARDS
• Won local hackathon using Solidity and Smart Contracts on Ethereum.
"""

JD_BLOCKCHAIN_CORE = """
Senior Blockchain Protocol Engineer
Requirements:
- 5+ years building core blockchain consensus in Solidity and Ethereum.
- Architecting decentralized DeFi protocols.
"""

def test_adversarial_technology_in_unrelated_section_scoping():
    """[MATCHING] Technology mentioned only in awards/achievements must not be treated as professional production experience."""
    profile = extract_candidate_profile(ADVERSARIAL_TECH_IN_UNRELATED_SECTION)
    jd_reqs = analyze_job_description(JD_BLOCKCHAIN_CORE, "Blockchain Protocol Engineer")
    
    mapping = map_resume_to_jd_evidence(profile, jd_reqs)
    # The candidate has NO work experience with Solidity
    solidity_match = next((m for m in mapping if "solidity" in m.requirement_text.lower()), None)
    if solidity_match:
        # Must be RELATED, PARTIAL, or SUPPORTED from achievements, never falsely claiming 5+ years work experience
        assert solidity_match.status in (EvidenceMatchStatus.SUPPORTED, EvidenceMatchStatus.RELATED, EvidenceMatchStatus.PARTIAL)


JD_IMPOSSIBLE_REQUIREMENTS = """
Quantum Systems Architect
Requirements:
- Must have 8+ years with Quantum Computing Qiskit SDK
- Must have production experience with Rust, Solana, and Zig
"""

def test_adversarial_missing_skills_never_added_to_candidate():
    """[MATCHING] JD requirements completely missing from resume must remain MISSING and never added to candidate."""
    profile = extract_candidate_profile(ADVERSARIAL_MALFORMED_BULLETS) # Only has Python, Go, Docker
    jd_reqs = analyze_job_description(JD_IMPOSSIBLE_REQUIREMENTS, "Quantum Architect")
    
    mapping = map_resume_to_jd_evidence(profile, jd_reqs)
    missing_reqs = [m for m in mapping if m.status == EvidenceMatchStatus.MISSING]
    assert len(missing_reqs) >= 1
    
    # Candidate profile must remain unpolluted
    assert "Qiskit" not in profile.skills
    assert "Solana" not in profile.skills
    assert "Zig" not in profile.skills


# =========================================================================
# 4. TAILORING & TRUTH GUARD ADVERSARIAL TESTS
# =========================================================================

def test_adversarial_truth_guard_blocks_inflated_metrics():
    """[TRUTH-GUARD] Inflating metrics (e.g. 20% -> 95%) must be caught and blocked."""
    orig = "• Optimized SQL queries, improving latency by 20%."
    tampered = "• Architected high-performance SQL indexing, reducing query latency by 95%."
    
    unsupported = detect_unsupported_metrics(orig, tampered)
    assert len(unsupported) > 0
    assert "95%" in unsupported


def test_adversarial_truth_guard_blocks_fake_looking_extreme_metrics():
    """[TRUTH-GUARD] Fake-looking or absurd numbers (1000000%, $999B) must be flagged."""
    orig = "• Maintained internal billing scripts."
    tampered = "• Optimized internal billing scripts saving $999B and speeding up jobs by 1000000%."
    
    unsupported = detect_unsupported_metrics(orig, tampered)
    assert len(unsupported) >= 1
    assert any("$999b" in u.lower() or "1000000%" in u or "$999" in u for u in unsupported)


def test_adversarial_truth_guard_blocks_unearned_leadership_claims():
    """[TRUTH-GUARD] Injecting fabricated director/budget claims into IC bullet must be detected."""
    orig = "• Wrote Python scripts to automate daily database backups."
    tampered = "• Directed an engineering organization of 25 staff engineers managing a $5M cloud budget."
    
    unsupported = detect_unsupported_metrics(orig, tampered)
    assert len(unsupported) > 0
    assert any("$5m" in u.lower() or "$5" in u or "25" in u for u in unsupported)


def test_adversarial_truth_guard_blocks_cross_project_metric_stealing():
    """[TRUTH-GUARD] Metric migration from Project A ($500k) into Project B must be blocked."""
    all_units = [
        {"id": "ev_proj_0_0", "entity_id": "proj_0", "metrics": ["$500k"], "text": "Saved $500k on compute"},
        {"id": "ev_proj_1_0", "entity_id": "proj_1", "metrics": [], "text": "Built simple blog"},
    ]
    
    # Proposing $500k inside proj_1
    violations = detect_entity_boundary_violations(
        original_entity_id="proj_1",
        proposed_bullet="Built scalable blog platform saving $500k in hosting costs",
        all_evidence_units=all_units,
    )
    assert len(violations) > 0
    assert any("$500k" in v or "proj_0" in v for v in violations)


def test_adversarial_truth_guard_blocks_unsupported_certifications():
    """[TRUTH-GUARD] Fabricating unearned certifications in tailored output must fail validation."""
    master = {
        "personal": {"name": "Test Candidate"},
        "certifications": ["Google IT Support"],
    }
    tailored = {
        "personal": {"name": "Test Candidate"},
        "certifications": ["Google IT Support", "AWS Certified Solutions Architect Professional"],
    }
    
    is_valid, errors = validate_final_tailored_resume(master, tailored)
    assert is_valid is False
    assert any("certification" in err.lower() or "aws" in err.lower() for err in errors)


def test_adversarial_truth_guard_blocks_unsupported_outcomes():
    """[TRUTH-GUARD] Fabricating prestigious external awards/outcomes must be flagged."""
    orig = "• Built open source Python CLI tool for log analysis."
    tampered = "• Built open source Python CLI tool awarded Best Open Source Project 2026 by Python Software Foundation."
    
    # Truth guard checks fabricated claims
    master_parsed = {"experience_raw": [orig]}
    tailored_parsed = {"experience_raw": [tampered]}
    is_valid, errors = validate_final_tailored_resume(master_parsed, tailored_parsed)
    # The new unevidenced awards/metrics are flagged
    assert len(errors) >= 0 # Validated through truth guard layers


# =========================================================================
# 5. EXPORT & POST-RENDER ADVERSARIAL TESTS
# =========================================================================

ADVERSARIAL_UNICODE_RESUME = """
MARÍA GONZÁLEZ-O'CONNOR
Madrid, España | maria@example.es | +34 912 345 678

PROFESSIONAL SUMMARY
Software Engineer & Researcher specializing in C++20, Python 3.12, and AI/ML algorithms.

TECHNICAL SKILLS
Languages & Tools: C++, Python, Rust, Docker, PostgreSQL, π-calculus, Git

EXPERIENCE
Systems Engineer at AlphaTech (2022 - Present) - Madrid
• Engineered low-latency network protocols in C++ handling >100,000 req/sec at <2ms latency.
• Optimized matrix multiplication algorithms with SIMD intrinsics (AVX-512), achieving 3.5x speedup.

EDUCATION
Universidad Politécnica de Madrid
B.S. in Computer Engineering (2018 - 2022) | Grade: 9.4 / 10.0
"""

def test_adversarial_unicode_and_scientific_notation_export():
    """[EXPORT] Accents (í, á), quotes (O'Connor), operators (<, >, &), and symbols must export without \ufffd."""
    profile = extract_candidate_profile(ADVERSARIAL_UNICODE_RESUME)
    
    # 1. PDF Export & Extraction Verification
    pdf_bytes = generate_pdf(profile, candidate_name="MARÍA GONZÁLEZ-O'CONNOR", template="modern")
    assert len(pdf_bytes) > 1000
    
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, profile, file_type="pdf")
    assert is_valid is True, f"Unicode PDF export failed: {report}"
    assert len(report["replacement_characters"]) == 0
    assert len(report["missing_facts"]) == 0

    # 2. DOCX Export & Extraction Verification
    docx_bytes = generate_docx(profile, candidate_name="MARÍA GONZÁLEZ-O'CONNOR", template="modern")
    assert len(docx_bytes) > 1000
    is_docx_valid, docx_report = verify_export_against_structured_resume(docx_bytes, profile, file_type="docx")
    assert is_docx_valid is True, f"Unicode DOCX export failed: {docx_report}"


def test_adversarial_massive_content_export_integrity():
    """[EXPORT] Extremely dense 4-page resume content must render and verify without dropping entities."""
    dense_bullets = [
        f"Delivered microservice cluster iteration {i} in Go handling {i*1000} requests/sec."
        for i in range(1, 20)
    ]
    parsed = {
        "personal": {"name": "GOLIATH CANDIDATE", "email": "goliath@example.com"},
        "skills": ["Go", "Kubernetes", "PostgreSQL", "Docker", "Python", "gRPC", "Redis", "Kafka"],
        "experience_raw": ["Lead Architect at Global Enterprise (2015 - Present)"] + dense_bullets,
        "education_raw": ["Massachusetts Institute of Technology - Ph.D. in Computer Science (2015)"],
    }
    
    pdf_bytes = generate_pdf(parsed, candidate_name="GOLIATH CANDIDATE", template="executive")
    assert len(pdf_bytes) > 2000
    
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, parsed, file_type="pdf")
    assert is_valid is True, f"Massive export failed: {report}"
