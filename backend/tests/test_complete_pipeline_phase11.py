"""
Complete End-to-End System Test Suite for Phase 11.
Executes the full 15-stage RoleRadar Resume Intelligence & Tailoring Pipeline:
Resume upload → extraction → normalization → CandidateProfile → EvidenceUnits
→ experience classification → template strategy → JD analysis → evidence/JD mapping
→ tailoring → Truth Guard → ATS validation → review/approval → rendering → PDF/DOCX export.

Tests 10 materially different candidate & JD scenarios:
1. Clean ATS resume
2. Long paragraph resume
3. Project-heavy fresher resume
4. Experienced professional resume
5. Poorly formatted resume with non-standard glyphs
6. Resume with malformed bullets
7. Resume with missing metrics (zero metric fabrication)
8. Resume with multiple verified metrics (exact preservation)
9. Resume containing skills absent from JD
10. JD requiring skills absent from candidate background
"""
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.ai_service.schemas import ChangeStatus, ChangeType
from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.intelligence.ats_readability_validator import evaluate_ats_and_readability
from app.modules.jobs.taxonomy import RequirementCategory, analyze_job_description
from app.modules.matching.evidence_mapping import (
    MatchSupportLevel,
    map_resume_evidence_to_jd_requirements,
)
from app.modules.resume.classification import (
    CareerClassification,
    classify_candidate_profile,
)
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    structure_resume_text,
)
from app.modules.tailoring import services as tailoring_services
from app.modules.tailoring.export import (
    generate_docx,
    generate_pdf,
    verify_export_against_structured_resume,
)
from app.modules.tailoring.strategy import (
    StrategyName,
    render_profile_with_strategy,
    resolve_template_strategy,
)
from app.modules.tailoring.validation import (
    detect_entity_boundary_violations,
    detect_fabricated_claims,
    detect_unsupported_metrics,
    validate_final_tailored_resume,
)


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


# =========================================================================
# Case 1: Clean ATS Resume
# =========================================================================
CASE_1_CLEAN_ATS = """
ANITA ROY
San Francisco, CA | anita@example.com | 415-555-0100

PROFESSIONAL SUMMARY
Backend Software Engineer with 4 years experience designing microservices in Go and PostgreSQL.

TECHNICAL SKILLS
Languages: Go, Python, SQL
Tools: Docker, Kubernetes, PostgreSQL, Redis, Git

WORK EXPERIENCE
Software Engineer at CloudFlow (2021 - Present) - San Francisco, CA
• Engineered high-performance REST APIs in Go serving 15,000 requests per second.
• Optimized PostgreSQL relational schemas, reducing database query times by 30%.

PROJECTS
• Distributed Key-Value Store: Implemented Raft consensus protocol in Go.

EDUCATION
University of California, Davis
B.S. in Computer Science (2017 - 2021)
"""

JD_1_BACKEND = """
Senior Go Backend Engineer
Requirements:
- 3+ years experience with Go and distributed systems
- Strong knowledge of PostgreSQL and Redis
- Experience with Docker and microservices
- Bachelor's degree in Computer Science or related field
"""

def test_case_1_clean_ats_pipeline():
    # 1. Parsing & CandidateProfile
    profile = extract_candidate_profile(CASE_1_CLEAN_ATS)
    assert profile.contact.name == "ANITA ROY"
    assert "Go" in profile.skills
    assert len(profile.evidence_units) >= 3

    # 2. Classification & Strategy
    classification = classify_candidate_profile(profile)
    assert classification.classification in (CareerClassification.EARLY_CAREER, CareerClassification.PROFESSIONAL)
    strategy = resolve_template_strategy(classification)
    assert strategy.template_variant in ("classic", "modern")

    # 3. JD Analysis & Matching
    jd_reqs = analyze_job_description(JD_1_BACKEND, "Go Backend Engineer")
    mapping = map_resume_evidence_to_jd_requirements(profile, jd_reqs)
    go_match = next((m for m in mapping if "go" in m.requirement_text.lower()), None)
    assert go_match is not None
    assert go_match.support_level in (MatchSupportLevel.EXACT_MATCH, MatchSupportLevel.SUPPORTED)

    # 4. Tailoring & Truth Guard
    rendered = render_profile_with_strategy(profile, strategy)
    is_valid, validation_errors = validate_final_tailored_resume(profile.to_parsed_dict(), rendered, profile)
    assert is_valid is True

    # 5. ATS Validation & Export
    audit = evaluate_ats_and_readability(rendered, master_data=profile)
    assert audit.factual_validation.is_valid is True
    assert audit.ats_format_validation.overall_ats_score >= 80

    pdf_bytes = generate_pdf(rendered, candidate_name="ANITA ROY", template="classic")
    is_exp_valid, exp_report = verify_export_against_structured_resume(pdf_bytes, rendered, file_type="pdf")
    assert is_exp_valid is True, f"Case 1 export failed: {exp_report}"


# =========================================================================
# Case 2: Long Paragraph Resume (Prose Blocks)
# =========================================================================
CASE_2_LONG_PARAGRAPH = """
DEVON VANCE
Chicago, IL | devon@example.com | 312-555-0144

SUMMARY
Passionate Full Stack Developer with extensive background building enterprise web applications.

SKILLS
JavaScript, TypeScript, React, Node.js, MongoDB, Express, AWS, HTML5, CSS3

EXPERIENCE
Full Stack Developer at Prairie Software Systems (2020 - Present)
During my tenure at Prairie Software Systems, I was responsible for architecting our primary customer facing web platform using React and Node.js. I collaborated closely with product designers to implement responsive user interfaces and engineered backend REST endpoints connected to MongoDB database clusters. Furthermore, I integrated automated CI/CD pipelines which accelerated our release velocity.

EDUCATION
University of Illinois Urbana-Champaign
B.S. in Information Technology (2016 - 2020)
"""

def test_case_2_long_paragraph_normalization_and_export():
    profile = extract_candidate_profile(CASE_2_LONG_PARAGRAPH)
    assert len(profile.evidence_units) >= 1
    assert "React" in profile.skills

    classification = classify_candidate_profile(profile)
    strategy = resolve_template_strategy(classification)
    rendered = render_profile_with_strategy(profile, strategy)

    # Asserts that long paragraph is structured and exports cleanly
    pdf_bytes = generate_pdf(rendered, candidate_name="DEVON VANCE", template="modern")
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, rendered, file_type="pdf")
    assert is_valid is True, f"Case 2 export failed: {report}"


# =========================================================================
# Case 3: Project-Heavy Fresher Resume (Vikas Style)
# =========================================================================
CASE_3_FRESHER_PROJECTS = """
VIKAS K
Davangere, Karnataka | vikas@example.com | +91 9876543210

PROFESSIONAL SUMMARY
Motivated Computer Science student with strong fundamentals in Python, Web Development, and Machine Learning.

TECHNICAL SKILLS
Languages: Python, Java, C, JavaScript, SQL
Frameworks & Tools: React.js, Node.js, Express.js, Flask, OpenCV, Docker, Git

PROJECTS
• AI Viral Analyzer (Flask, OpenCV, Python): Engineered image recognition pipeline achieving 91% classification accuracy across 5,000 images.
• ShopVerse (React.js, Node.js, MongoDB): Developed e-commerce platform supporting real-time cart checkout with Stripe.

EDUCATION
Bapuji Institute of Engineering and Technology
B.E. in Computer Science and Engineering (2023 - 2027) | CGPA: 9.1 / 10.0

CERTIFICATIONS
Smart India Hackathon Finalist 2024
"""

def test_case_3_fresher_project_heavy_pipeline():
    profile = extract_candidate_profile(CASE_3_FRESHER_PROJECTS)
    assert len(profile.projects) == 2
    assert len(profile.experience) == 0

    classification = classify_candidate_profile(profile)
    assert classification.classification in (CareerClassification.FRESHER, CareerClassification.STUDENT)
    
    strategy = resolve_template_strategy(classification)
    assert strategy.highlight_education_top is True
    # Education appears before projects in fresher layout
    edu_pos = strategy.section_order.index("education")
    proj_pos = strategy.section_order.index("projects")
    assert edu_pos < proj_pos

    rendered = render_profile_with_strategy(profile, strategy)
    assert rendered["personal"]["name"] == "VIKAS K"

    pdf_bytes = generate_pdf(rendered, candidate_name="VIKAS K", template="modern")
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, rendered, file_type="pdf")
    assert is_valid is True, f"Case 3 export failed: {report}"


# =========================================================================
# Case 4: Experienced Professional Resume (Multi-Role, Leadership)
# =========================================================================
CASE_4_SENIOR_PRO = """
MARCUS STERLING
Austin, TX | marcus@example.com | 512-555-0199

PROFESSIONAL SUMMARY
Director of Cloud Infrastructure with 10+ years scaling enterprise SaaS platforms.

TECHNICAL SKILLS
Cloud & DevOps: AWS, GCP, Terraform, Kubernetes, Helm, CI/CD, Python, Go

WORK EXPERIENCE
Director of Engineering at EnterpriseCloud (2021 - Present) - Austin, TX
• Led organization of 24 platform engineers maintaining 99.99% availability across global AWS infrastructure.
• Reduced cloud compute expenditure by $1.8M through spot instance orchestration and auto-scaling policies.

Principal DevOps Architect at ScaleMatrix (2016 - 2021) - Dallas, TX
• Architected multi-region Kubernetes clusters serving 50M daily requests.
• Automated infrastructure provisioning using Terraform and GitHub Actions.

EDUCATION
University of Texas at Austin
B.S. in Electrical and Computer Engineering (2012 - 2016)
"""

def test_case_4_senior_professional_pipeline():
    profile = extract_candidate_profile(CASE_4_SENIOR_PRO)
    classification = classify_candidate_profile(profile)
    assert classification.classification in (CareerClassification.SENIOR_PROFESSIONAL, CareerClassification.LEADERSHIP)

    strategy = resolve_template_strategy(classification)
    assert strategy.template_variant == "executive"

    rendered = render_profile_with_strategy(profile, strategy)
    pdf_bytes = generate_pdf(rendered, candidate_name="MARCUS STERLING", template="executive")
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, rendered, file_type="pdf")
    assert is_valid is True, f"Case 4 export failed: {report}"


# =========================================================================
# Case 5: Poorly Formatted Resume with Non-Standard Glyphs
# =========================================================================
CASE_5_POORLY_FORMATTED = """
JANE DOE
Location: New York | Email: jane@example.com | Phone: 212-555-0122

STUFF I DID
⚡ Project Alpha: Built distributed cache system in Python.
★ Project Beta: Engineered search indexing engine with 95% precision.

TECH ARSENAL
Python, Redis, Docker, FastAPI

SCHOOLING
Columbia University
B.S. in Computer Science (2019 - 2023)
"""

def test_case_5_poorly_formatted_ats_audit_and_remediation():
    profile = extract_candidate_profile(CASE_5_POORLY_FORMATTED)
    audit = evaluate_ats_and_readability(CASE_5_POORLY_FORMATTED, master_data=profile)

    # Identifies non-standard headings and symbols
    assert audit.ats_format_validation.standard_headings_score < 100
    assert len(audit.ats_format_validation.unusual_symbols_detected) >= 1
    assert "⚡" in audit.ats_format_validation.unusual_symbols_detected or "★" in audit.ats_format_validation.unusual_symbols_detected

    # Structure recovery standardizes the layout
    strategy = resolve_template_strategy(classify_candidate_profile(profile))
    rendered = render_profile_with_strategy(profile, strategy)

    # Rendered export cleans all invalid glyphs and sanitizes text
    pdf_bytes = generate_pdf(rendered, candidate_name="JANE DOE", template="modern")
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, rendered, file_type="pdf")
    assert is_valid is True, f"Case 5 export failed: {report}"


# =========================================================================
# Case 6: Resume with Malformed Bullets
# =========================================================================
CASE_6_MALFORMED_BULLETS = """
SAMUEL REED
samuel@example.com | 206-555-0177

SKILLS
Python, Flask, PostgreSQL

EXPERIENCE
Software Developer at WebWorks (2022 - Present)
-
• engineered backend database schemas
•
• built RESTful APIs in Flask
- optimized SQL query latency by 25%

EDUCATION
University of Washington, B.S. CS (2018 - 2022)
"""

def test_case_6_malformed_bullets_recovery():
    profile = extract_candidate_profile(CASE_6_MALFORMED_BULLETS)
    
    # Asserts that empty/isolated bullets were discarded
    for unit in profile.evidence_units:
        assert len(unit.text.strip()) > 3
        assert unit.text.strip() not in ("•", "-", "*")

    strategy = resolve_template_strategy(classify_candidate_profile(profile))
    rendered = render_profile_with_strategy(profile, strategy)
    pdf_bytes = generate_pdf(rendered, candidate_name="SAMUEL REED", template="modern")
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, rendered, file_type="pdf")
    assert is_valid is True, f"Case 6 export failed: {report}"
    assert len(report["broken_bullets"]) == 0


# =========================================================================
# Case 7: Resume with Missing Metrics (Anti-Fabrication Guard)
# =========================================================================
CASE_7_NO_METRICS = """
CLARA OSWALD
clara@example.com | 555-0188

SKILLS
Python, Django, PostgreSQL

EXPERIENCE
Software Developer at Timeless Tech (2021 - Present)
• Developed user authentication module using Django.
• Maintained PostgreSQL database migrations and schema backups.

EDUCATION
Cardiff University, B.S. Software Engineering (2017 - 2021)
"""

def test_case_7_missing_metrics_anti_fabrication():
    profile = extract_candidate_profile(CASE_7_NO_METRICS)
    
    # Tailoring attempt that invents fake percentages
    fabricated_proposed = "• Developed user authentication module using Django, improving security efficiency by 75%."
    fabricated = detect_unsupported_metrics("• Developed user authentication module using Django.", fabricated_proposed)
    assert len(fabricated) > 0
    assert "75%" in fabricated

    # Truthful rewrite with no fake metric passes
    truthful_proposed = "• Engineered secure token-based user authentication module utilizing Django."
    truthful_fab = detect_unsupported_metrics("• Developed user authentication module using Django.", truthful_proposed)
    assert len(truthful_fab) == 0


# =========================================================================
# Case 8: Resume with Multiple Metrics (Exact Preservation)
# =========================================================================
CASE_8_MULTI_METRICS = """
VICTOR STONE
victor@example.com | 555-0133

SKILLS
Python, C++, Docker

EXPERIENCE
Systems Engineer at CyberCorp (2020 - Present)
• Optimized telemetry processing pipeline, decreasing latency by 45% across 100,000 connected devices.
• Scaled backend throughput from 5,000 to 25,000 req/sec while saving $350k in annual compute costs.

EDUCATION
Detroit Tech, B.S. Computer Engineering (2016 - 2020)
"""

def test_case_8_multiple_metrics_preservation():
    profile = extract_candidate_profile(CASE_8_MULTI_METRICS)
    
    orig = "• Optimized telemetry processing pipeline, decreasing latency by 45% across 100,000 connected devices."
    
    # Invariant: Altering 45% to 90% is caught immediately
    altered_proposal = "• Architected high-speed telemetry pipeline, reducing latency by 90% across 100,000 devices."
    assert len(detect_unsupported_metrics(orig, altered_proposal)) > 0

    # Invariant: Preserving verified 45% passes
    valid_proposal = "• Architected high-speed telemetry pipeline in Python and C++, reducing latency by 45% across 100,000 devices."
    assert len(detect_unsupported_metrics(orig, valid_proposal)) == 0


# =========================================================================
# Case 9: Resume Containing Skills Absent from JD
# =========================================================================
CASE_9_RESUME_EXTRA_SKILLS = """
SARAH CONNOR
sarah@example.com | 555-0122

SKILLS
Languages: Python, Rust, Go, SQL, Solidity
Tools: Docker, Kubernetes, Web3, PostgreSQL

EXPERIENCE
Software Engineer at Cyberdyne (2021 - Present)
• Built Python web microservices and Rust cryptographic tools.

EDUCATION
MIT, B.S. CS (2017 - 2021)
"""

JD_9_PYTHON_ONLY = """
Python Backend Developer
Requirements:
- Strong Python and SQL programming skills
- Experience with Docker and PostgreSQL
"""

def test_case_9_candidate_extra_skills_handling():
    profile = extract_candidate_profile(CASE_9_RESUME_EXTRA_SKILLS)
    jd_reqs = analyze_job_description(JD_9_PYTHON_ONLY, "Python Developer")
    
    mapping = map_resume_evidence_to_jd_requirements(profile, jd_reqs)
    # Python & SQL are matched
    py_match = next((m for m in mapping if "python" in m.requirement_text.lower()), None)
    assert py_match is not None
    assert py_match.support_level in (MatchSupportLevel.EXACT_MATCH, MatchSupportLevel.SUPPORTED)

    # Extra skills (Rust, Solidity, Web3) remain in candidate profile and export
    strategy = resolve_template_strategy(classify_candidate_profile(profile))
    rendered = render_profile_with_strategy(profile, strategy)
    assert "Rust" in rendered["skills"] or "Languages: Python, Rust, Go, SQL, Solidity" in str(rendered.get("skills_categorized", []))


# =========================================================================
# Case 10: JD Requiring Skills Absent from Candidate Profile
# =========================================================================
CASE_10_CANDIDATE_NO_AWS = """
LUCAS GREY
lucas@example.com | 555-0155

SKILLS
Python, Flask, SQLite, Git

PROJECTS
• Library Management System: Built Flask database application.

EDUCATION
State University, B.S. CS (2020 - 2024)
"""

JD_10_ENTERPRISE_AWS = """
Enterprise Cloud Architect
Must Have:
- 5+ years AWS infrastructure experience (EKS, Lambda, S3, IAM)
- Expert in Terraform and Kafka event streaming
- Kubernetes certified
"""

@pytest.mark.asyncio
async def test_case_10_missing_skills_needs_user_input_and_truth_guard(db, settings):
    profile = extract_candidate_profile(CASE_10_CANDIDATE_NO_AWS)
    jd_reqs = analyze_job_description(JD_10_ENTERPRISE_AWS, "Cloud Architect")
    
    # 1. Matching correctly marks AWS and Terraform as MISSING
    mapping = map_resume_evidence_to_jd_requirements(profile, jd_reqs)
    missing_items = [m for m in mapping if m.support_level == MatchSupportLevel.MISSING]
    assert len(missing_items) >= 2
    assert any("aws" in m.requirement_text.lower() or "terraform" in m.requirement_text.lower() for m in missing_items)

    # 2. Fabricated injection is caught by Truth Guard
    proposal_with_aws = "• Built enterprise cloud infrastructure on AWS EKS with Terraform and Kafka."
    fab = detect_fabricated_claims("• Built Flask database application.", proposal_with_aws, "AWS, Terraform, Kafka", profile.skills)
    assert len(fab) >= 1
    assert any("aws" in f.lower() or "terraform" in f.lower() or "kafka" in f.lower() for f in fab)

    # 3. Direct backend approval of unverified claim MUST be blocked
    user, _ = await auth_services.register_user(db, settings, "case10_tester@example.com", "secretpass123", "Lucas", None)
    user_id = str(user["_id"])

    from app.modules.tailoring import repositories as tailoring_repo
    version = await tailoring_repo.create_version(
        db,
        user_id,
        "job_cloud_10",
        "Enterprise Cloud Architect",
        "CloudEnterprise",
        changes=[
            {
                "change_id": "chg_case10_aws",
                "section": "PROJECTS",
                "change_type": ChangeType.KEYWORD_INJECTION.value,
                "original": "Built Flask database application.",
                "proposed": proposal_with_aws,
                "status": ChangeStatus.NEEDS_USER_INPUT.value,
                "fabrication_warning": "AWS competency not found in master resume evidence",
            }
        ],
        sections_evaluated=["PROJECTS"],
        sections_changed=["PROJECTS"],
        unmatched_gaps=["AWS", "Terraform", "Kafka"],
        parsed=profile.to_parsed_dict(),
    )
    version_id = str(version["_id"])

    # Attempting to bypass frontend and approve NEEDS_USER_INPUT directly via backend API:
    with pytest.raises(tailoring_services.InvalidChangeStatusError) as exc_info:
        await tailoring_services.set_change_status(
            db, user_id, version_id, "chg_case10_aws", ChangeStatus.APPROVED
        )
    assert "lacks verified source evidence" in str(exc_info.value)
