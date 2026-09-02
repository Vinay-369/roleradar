"""
Phase 3 Unit & Regression Test Suite: Generalized JD Reconstruction & Analysis Layer.
Validates:
1. Required vs preferred headings
2. Compound headings with slashes, ampersands, and hyphens
3. Unknown headings & preamble preservation (never defaulting to MUST_HAVE)
4. Header self-ingestion prevention (headings never becoming candidate requirements)
5. Company overview & role overview isolation
6. Boilerplate, benefits, and EEO legal isolation
7. Responsibility preservation
8. Multi-word intervening qualifier experience extraction
9. Experience false-positive prevention (company history tenure ignored)
10. Seniority false-positive prevention (collaborator titles ignored)
11. Domain classification with weighted multi-signal evidence
12. Education & certification extraction
13. Location, work mode, and employment type extraction
14. JobRequirement provenance tracking
15. Downstream evidence mapping compatibility
16. Capco stress test end-to-end fidelity
"""
import pytest
from app.modules.jobs.taxonomy import (
    RequirementCategory,
    JobRequirement,
    StructuredJobRequirements,
    analyze_job_description,
)
from app.modules.matching.evidence_mapping import (
    EvidenceMatchStatus,
    map_resume_to_jd_evidence,
)
from app.modules.resume.models import CandidateProfile, EvidenceUnit


# =========================================================================
# 1. HEADINGS & COMPOUND SECTION RECONSTRUCTION TESTS
# =========================================================================

def test_required_vs_preferred_headings():
    jd = """
    Software Engineer
    Must-Have:
    - 3+ years experience with Java and Spring Boot.
    
    Nice-to-Have / Preferred:
    - Hands-on experience with Kubernetes and AWS.
    """
    reqs = analyze_job_description(jd)
    assert len(reqs.requirements) == 2
    assert reqs.requirements[0].category == RequirementCategory.MUST_HAVE
    assert reqs.requirements[1].category == RequirementCategory.PREFERRED
    assert "Java" in reqs.must_have_skills or "java" in [s.lower() for s in reqs.must_have_skills]
    assert "Kubernetes" in reqs.preferred_skills or "kubernetes" in [s.lower() for s in reqs.preferred_skills]
    assert "Kubernetes" not in reqs.must_have_skills


def test_compound_headings_with_slashes_and_ampersands():
    jd = """
    Full Stack Developer
    
    Requirements & Core Qualifications:
    - Proficiency in TypeScript and React.
    
    Preferred & Bonus Points:
    - Experience with GraphQL and Redis.
    """
    reqs = analyze_job_description(jd)
    assert len(reqs.requirements) == 2
    assert reqs.requirements[0].category == RequirementCategory.MUST_HAVE
    assert reqs.requirements[1].category == RequirementCategory.PREFERRED
    assert "React" in reqs.must_have_skills or "react" in [s.lower() for s in reqs.must_have_skills]
    assert "Redis" in reqs.preferred_skills or "redis" in [s.lower() for s in reqs.preferred_skills]


def test_unknown_and_preamble_heading_handling():
    jd = """
    Our Team Culture:
    We value innovation, high standards, and continuous learning.
    
    What We Are Looking For:
    - Strong knowledge of Python and PostgreSQL.
    """
    reqs = analyze_job_description(jd)
    # Preamble text should not become MUST_HAVE candidate requirement items
    assert not any("We value innovation" in r.text for r in reqs.requirements if r.category == RequirementCategory.MUST_HAVE and r.skills_detected)
    assert any("Python" in r.skills_detected for r in reqs.requirements)


def test_header_self_ingestion_prevention():
    jd = """
    Backend Engineer
    
    Must-Have:
    - 4+ years of Python.
    
    Nice-to-Have / Preferred:
    - Knowledge of Kafka.
    """
    reqs = analyze_job_description(jd)
    req_texts = [r.text.strip().lower() for r in reqs.requirements]
    assert "must-have:" not in req_texts
    assert "must-have" not in req_texts
    assert "nice-to-have / preferred:" not in req_texts
    assert "nice-to-have / preferred" not in req_texts


# =========================================================================
# 2. CONTEXT & BOILERPLATE ISOLATION TESTS
# =========================================================================

def test_company_and_role_overview_isolation():
    jd = """
    Stripe - Staff Backend Engineer
    
    About Stripe:
    Stripe builds financial infrastructure for the internet. Millions of businesses rely on Stripe.
    
    Role Overview:
    We are seeking a Staff Backend Engineer to lead our global payout ledger architecture.
    
    Key Responsibilities:
    - Architect distributed database transaction systems.
    
    Requirements:
    - 8+ years of distributed backend systems experience.
    """
    reqs = analyze_job_description(jd)
    assert reqs.company == "Stripe"
    assert reqs.company_overview is not None
    assert "financial infrastructure" in reqs.company_overview
    assert reqs.role_overview is not None
    assert "global payout ledger" in reqs.role_overview
    
    # Overview sentences must not become candidate requirement items
    assert not any("financial infrastructure" in r.text for r in reqs.requirements)
    assert not any("global payout ledger" in r.text for r in reqs.requirements)
    assert len(reqs.responsibilities) == 1
    assert len(reqs.requirements) == 2  # 1 resp + 1 req


def test_boilerplate_benefits_and_eeo_isolation():
    jd = """
    Software Engineer
    
    Requirements:
    - 2+ years of Go programming.
    
    Benefits & Perks:
    - 401(k) matching up to 6%.
    - Unlimited paid time off and comprehensive medical coverage.
    
    Equal Opportunity Employer:
    We are an equal opportunity employer and do not discriminate based on race, color, or religion.
    """
    reqs = analyze_job_description(jd)
    assert len(reqs.requirements) == 1
    assert "Go" in reqs.must_have_skills or "go" in [s.lower() for s in reqs.must_have_skills]
    assert not any("401(k)" in r.text for r in reqs.requirements)
    assert not any("equal opportunity" in r.text.lower() for r in reqs.requirements)


# =========================================================================
# 3. EXPERIENCE EXTRACTION TESTS
# =========================================================================

def test_multi_word_intervening_qualifier_experience_extraction():
    test_cases = [
        ("3+ years of professional software development experience in Java", 3.0, None),
        ("5+ years of hands-on Java experience", 5.0, None),
        ("2-4 years relevant experience", 2.0, 4.0),
        ("7 years of professional experience", 7.0, None),
        ("minimum 4 years experience", 4.0, None),
        ("12+ years of software development and engineering management experience", 12.0, None),
    ]
    for text, expected_min, expected_max in test_cases:
        jd = f"Software Engineer\nRequirements:\n- {text}"
        reqs = analyze_job_description(jd)
        assert reqs.min_years_experience == expected_min, f"Failed for '{text}': got {reqs.min_years_experience}, expected {expected_min}"
        if expected_max:
            assert reqs.max_years_experience == expected_max


def test_experience_false_positive_prevention_on_company_history():
    jd = """
    Cloud Solutions Architect
    
    About Us:
    Our company has 25 years of experience delivering IT modernization across North America.
    
    Requirements:
    - 5+ years of AWS cloud infrastructure experience.
    """
    reqs = analyze_job_description(jd)
    assert reqs.min_years_experience == 5.0  # Must be 5, NOT 25!


# =========================================================================
# 4. SENIORITY & DOMAIN CLASSIFICATION TESTS
# =========================================================================

def test_seniority_false_positive_prevention_on_collaborators():
    jd = """
    Java Full Stack Developer
    
    Role Overview:
    You will collaborate closely with senior architects, director of engineering, and QA leads.
    
    Requirements:
    - 3+ years experience with Java and React.
    """
    reqs = analyze_job_description(jd)
    assert reqs.seniority == "MID"  # Must NOT become SENIOR merely because architects are mentioned


def test_seniority_explicit_title_anchoring():
    jd_sr = "Senior Software Engineer\nRequirements:\n- 5+ years of Python"
    assert analyze_job_description(jd_sr).seniority == "SENIOR"
    
    jd_jr = "Junior Software Engineer\nRequirements:\n- 1 year of Python"
    assert analyze_job_description(jd_jr).seniority == "ENTRY"


def test_domain_classification_with_competing_signals():
    # Full Stack role with secondary cloud preferred requirement
    jd_fullstack = """
    Java Full Stack Developer
    
    Responsibilities:
    - Build full-stack web applications with React, Java Spring Boot, and PostgreSQL.
    
    Requirements:
    - Hands-on frontend and backend web development.
    
    Preferred:
    - Cloud infrastructure familiarity (AWS, Docker).
    """
    reqs = analyze_job_description(jd_fullstack)
    assert reqs.domain == "Full Stack Engineering"


def test_domain_classification_cloud_engineer():
    jd_cloud = """
    Site Reliability Engineer - Cloud Infrastructure
    
    Responsibilities:
    - Manage Kubernetes clusters and Terraform infrastructure on AWS.
    
    Requirements:
    - 5+ years of DevOps and cloud infrastructure engineering.
    """
    reqs = analyze_job_description(jd_cloud)
    assert reqs.domain == "Cloud & Infrastructure"


# =========================================================================
# 5. METADATA, EDUCATION & CERTIFICATION EXTRACTION
# =========================================================================

def test_location_work_mode_and_employment_type():
    jd = """
    Staff Backend Engineer
    Location: Seattle, WA / Hybrid
    Employment Type: Full-Time
    
    Requirements:
    - 6+ years of Go.
    """
    reqs = analyze_job_description(jd)
    assert reqs.location == "Seattle, WA"
    assert reqs.work_mode == "Hybrid"
    assert reqs.employment_type == "Full-Time"


def test_education_and_certification_extraction():
    jd = """
    Machine Learning Engineer
    
    Requirements:
    - Master's or Ph.D. in Computer Science or Artificial Intelligence.
    - AWS Certified Solutions Architect is preferred.
    - 3+ years of Python and PyTorch.
    """
    reqs = analyze_job_description(jd)
    assert len(reqs.education_requirements) >= 1
    assert any("Master's" in e or "Ph.D." in e for e in reqs.education_requirements)
    assert len(reqs.certifications) >= 1
    assert any("AWS Certified" in c for c in reqs.certifications)


# =========================================================================
# 6. PROVENANCE & DOWNSTREAM EVIDENCE MAPPING TESTS
# =========================================================================

def test_job_requirement_provenance_retention():
    jd = """
    Security Engineer
    
    Key Responsibilities:
    - Conduct penetration testing across cloud workloads.
    
    Requirements:
    - 4+ years in cybersecurity operations.
    """
    reqs = analyze_job_description(jd)
    for r in reqs.requirements:
        assert r.source_section in ("RESPONSIBILITIES", "REQUIREMENTS_MUST_HAVE", "MUST_HAVE", "RESPONSIBILITY")
        assert r.source_heading is not None
        assert r.raw_text is not None
        assert r.normalized_text is not None


def test_downstream_evidence_mapping_with_preferred_and_must_have():
    jd = """
    Full Stack Developer
    
    Requirements:
    - Strong skills in Python and SQL.
    
    Preferred:
    - Experience with Rust and Solana.
    """
    reqs = analyze_job_description(jd)
    
    profile = CandidateProfile(
        name="Test Candidate",
        skills=["Python", "SQL"],
        evidence_units=[
            EvidenceUnit(
                id="EV_01",
                section="EXPERIENCE",
                entity_id="exp_1",
                original_text="Built Python APIs with SQL databases",
                text_snippet="Built Python APIs with SQL databases",
                normalized_text="built python apis with sql databases",
                technologies=["Python", "SQL"],
            )
        ]
    )
    
    mapping = map_resume_to_jd_evidence(profile, reqs)
    
    # Must-haves matched
    assert mapping.exact_matches_count >= 1
    
    # Missing preferred skills should be recorded under missing_preferred, NOT missing_must_haves
    assert not any("Rust" in mh or "Solana" in mh for mh in mapping.missing_must_haves)


# =========================================================================
# 7. CAPCO STRESS TEST END-TO-END FIDELITY
# =========================================================================

CAPCO_JD_STRESS_TEXT = """Capco - Java Full Stack Developer
Location: Bangalore, India / Hybrid
Job Type: Full-Time

About Capco:
Capco, a Wipro company, is a global technology and management consultancy specializing in driving digital transformation in the financial services industry. We make a difference for our clients by combining innovative thinking with bespoke technical delivery.

Role Overview:
We are looking for an experienced Java Full Stack Developer to join our growing Digital Engineering practice. In this role, you will design, develop, and deploy enterprise-grade, mission-critical web applications for leading global financial institutions. You will work within high-performing Agile teams collaborating with architects, product owners, and QA engineers.

Key Responsibilities:
- Design, build, test, and deploy scalable full-stack applications using Java, Spring Boot microservices, and modern frontend frameworks (React or Angular).
- Develop robust RESTful APIs and event-driven microservices architecture ensuring high performance, security, and low latency.
- Design database schemas and write optimized queries for relational (PostgreSQL, Oracle, MySQL) and NoSQL (MongoDB) databases.
- Collaborate in an Agile/Scrum cross-functional team, participating in sprint planning, code reviews, and pair programming.
- Implement CI/CD automation pipelines using Docker, Kubernetes, Jenkins, and Git.
- Ensure rigorous test coverage with unit testing (JUnit, Mockito), integration testing, and automated end-to-end tests.
- Troubleshoot, debug, and optimize complex software systems in production environments.

Requirements & Qualifications:
Must-Have:
- Bachelor's or Master's degree in Computer Science, Software Engineering, or related field.
- 3+ years of professional software development experience in Java (Java 8/11/17) and Spring Boot framework.
- Strong hands-on experience building RESTful web services and microservices.
- Proficiency in frontend technologies: HTML5, CSS3, JavaScript (ES6+), TypeScript, and React or Angular.
- Strong knowledge of SQL databases (PostgreSQL/MySQL/Oracle) and data modeling.
- Solid understanding of Object-Oriented Design Principles (OOP), Data Structures, and Algorithms.
- Experience with Git version control, unit testing frameworks (JUnit, Mockito), and Agile methodologies.

Nice-to-Have / Preferred:
- Experience with cloud platforms (AWS, Azure, or GCP) and containerization (Docker, Kubernetes).
- Familiarity with messaging queues (Kafka, RabbitMQ).
- Knowledge of financial services domain, banking systems, or capital markets.
- Experience with CI/CD tools (Jenkins, GitHub Actions, GitLab CI).
- Understanding of reactive programming, Redis caching, or GraphQL.
"""

def test_capco_stress_test_fidelity():
    reqs = analyze_job_description(CAPCO_JD_STRESS_TEXT)
    
    assert reqs.target_role == "Java Full Stack Developer"
    assert reqs.company == "Capco"
    assert reqs.location == "Bangalore, India"
    assert reqs.work_mode == "Hybrid"
    assert reqs.employment_type == "Full-Time"
    assert reqs.seniority == "MID"
    assert reqs.domain == "Full Stack Engineering"
    assert reqs.min_years_experience == 3.0
    
    # Responsibilities count
    assert len(reqs.responsibilities) == 7
    
    # Skills separation
    assert len(reqs.must_have_skills) >= 15
    assert len(reqs.preferred_skills) >= 5
    assert "Java" in reqs.must_have_skills or "java" in [s.lower() for s in reqs.must_have_skills]
    assert "Spring Boot" in reqs.must_have_skills or "spring boot" in [s.lower() for s in reqs.must_have_skills]
    assert "AWS" in reqs.preferred_skills or "aws" in [s.lower() for s in reqs.preferred_skills]
    assert "Kafka" in reqs.preferred_skills or "kafka" in [s.lower() for s in reqs.preferred_skills] or "RabbitMQ" in reqs.preferred_skills
    
    # Zero boilerplate requirements
    assert not any("About Capco" in r.text for r in reqs.requirements)
    assert not any("Role Overview" in r.text for r in reqs.requirements)
    assert not any("Must-Have:" in r.text for r in reqs.requirements)
    assert not any("Nice-to-Have / Preferred:" in r.text for r in reqs.requirements)
    
    # Total requirements count = 7 responsibilities + 7 must-haves + 5 preferreds = 19
    assert len(reqs.requirements) == 19
