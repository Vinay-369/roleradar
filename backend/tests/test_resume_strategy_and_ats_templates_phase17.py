"""
Tests for Phase 17: Resume Strategy & ATS Template Selection Engine.
Verifies:
1. Fresher / Project-heavy candidate -> ATS_FRESHER, Education/Projects prioritized, 1 page.
2. Fresher / Internship-heavy candidate -> ATS_FRESHER / EARLY_CAREER.
3. Experienced professional -> ATS_PROFESSIONAL, Experience dominant.
4. Senior engineer -> ATS_SENIOR, Architecture/Ownership prioritized, 2 pages.
5. Engineering lead -> ATS_SENIOR, Leadership & Team velocity prioritized.
6. Manager / Director -> ATS_SENIOR, Executive & Organizational scale.
7. Academic / Research -> Publications & Research prioritized.
8. Career switcher -> Transferable skills & Projects prioritized.
9. Uncertain classification fallback -> ATS_CLASSIC_FALLBACK.
10. Sparse profile -> ContentDensity.LOW, 1 page budget.
11. Dense profile -> ContentDensity.HIGH, 2 page budget.
12. Property Invariants:
    - Never invents candidate skills or evidence.
    - Excludes empty sections from section ordering.
    - Unsupported JD skills are excluded from skill priority.
    - Never modifies metrics, dates, or moves claims.
"""
import pytest

from app.modules.jobs.taxonomy import analyze_jd_requirements
from app.modules.matching.evidence_mapping import map_resume_to_jd_evidence
from app.modules.resume.classification import (
    CareerClassification,
    CareerClassificationResult,
    classify_candidate_profile,
)
from app.modules.resume.models import CandidateProfile
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.export import render_candidate_profile_to_text
from app.modules.tailoring.strategy import (
    CareerStage,
    ContentDensity,
    ResumeStrategy,
    TemplateFamily,
    build_resume_strategy,
    calculate_content_density,
    compute_bullet_budgets,
    compute_project_priorities,
    compute_skill_priorities,
    resolve_template_strategy,
    select_template_family,
)


def test_01_fresher_project_heavy():
    """Verify Fresher with multiple projects selects ATS_FRESHER and prioritizes Education/Projects."""
    resume_text = """
    AARAV SHARMA
    aarav.sharma@email.com | +91 9876543210 | New Delhi, India

    EDUCATION
    B.Tech in Computer Science, IIT Delhi (2020 - 2024)
    GPA: 8.9 / 10.0

    TECHNICAL SKILLS
    Python, C++, Java, React, FastAPI, Docker

    PROJECTS
    Distributed Key-Value Store (C++, gRPC) (2023)
    • Implemented Raft consensus protocol across 5 cluster nodes.
    • Achieved 15k requests/sec with under 8ms p99 latency.

    AI Resume Parser (Python, FastAPI) (2024)
    • Built NLP parsing pipeline handling 50 concurrent requests.
    """
    profile = extract_candidate_profile(resume_text)
    analysis = classify_candidate_profile(profile)
    
    strategy = build_resume_strategy(profile, analysis)
    assert strategy.template_family == TemplateFamily.ATS_FRESHER
    assert strategy.page_budget == 1
    assert strategy.project_emphasis is True
    assert strategy.highlight_education_top is True
    
    # Check section order
    assert strategy.section_order.index("education") < strategy.section_order.index("projects")
    assert "experience" not in strategy.section_order  # Empty experience must be excluded


def test_02_fresher_internship_heavy():
    """Verify Early Career / Intern candidate prioritizes practical experience and education."""
    resume_text = """
    PRIYA PATEL
    priya.patel@email.com | (555) 234-5678 | San Jose, CA

    EDUCATION
    B.S. in Software Engineering, San Jose State University (2020 - 2024)

    TECHNICAL SKILLS
    Java, Spring Boot, React, TypeScript, PostgreSQL

    EXPERIENCE
    Software Engineering Intern at CloudBase Inc (June 2023 - August 2023)
    • Built internal dashboard in React and TypeScript reducing onboarding time by 30%.
    • Automated unit tests achieving 94% test coverage.
    """
    profile = extract_candidate_profile(resume_text)
    analysis = classify_candidate_profile(profile)
    
    strategy = build_resume_strategy(profile, analysis)
    assert strategy.template_family in (TemplateFamily.ATS_FRESHER, TemplateFamily.ATS_PROFESSIONAL)
    assert strategy.page_budget == 1
    assert "experience" in strategy.section_order
    assert "projects" not in strategy.section_order  # No projects in resume


def test_03_experienced_professional():
    """Verify experienced professional selects ATS_PROFESSIONAL with experience dominance."""
    resume_text = """
    MICHAEL CHANG
    m.chang@email.com | Austin, TX

    SUMMARY
    Software Engineer with 4+ years of experience building scalable backend services in Go and AWS.

    EXPERIENCE
    Backend Engineer at Apex Systems (2021 - Present)
    • Designed asynchronous event pipeline in Go handling 120k messages/sec.
    • Migrated monolithic authentication service to gRPC microservices.

    Software Developer at CoreLogic (2019 - 2021)
    • Developed RESTful API endpoints in Python and FastAPI.
    • Integrated Redis caching layer saving $15k monthly.

    TECHNICAL SKILLS
    Go, Python, AWS, Docker, Kubernetes, Kafka, Redis, PostgreSQL

    EDUCATION
    B.S. in Computer Science, UT Austin (2015 - 2019)
    """
    profile = extract_candidate_profile(resume_text)
    analysis = classify_candidate_profile(profile)
    
    strategy = build_resume_strategy(profile, analysis)
    assert strategy.template_family == TemplateFamily.ATS_PROFESSIONAL
    assert strategy.experience_emphasis is True
    assert strategy.section_order.index("experience") < strategy.section_order.index("education")
    assert strategy.experience_strategy == "EXPERIENCE_DOMINANT"


def test_04_senior_engineer():
    """Verify senior engineer selects ATS_SENIOR with 2-page budget."""
    resume_text = """
    VIKRAM MALHOTRA
    vikram.m@email.com | Seattle, WA

    PROFESSIONAL SUMMARY
    Senior Software Architect with 8+ years designing fault-tolerant cloud platforms.

    EXPERIENCE
    Staff Software Engineer at DataCloud Corp (2020 - Present)
    • Led architectural redesign of core distributed storage engine handling 2PB data.
    • Reduced database infrastructure spend by 35% ($1.2M annually).

    Senior Backend Engineer at StreamTech (2016 - 2020)
    • Architected real-time video transcoding pipeline in C++ serving 5M viewers.

    TECHNICAL SKILLS
    Go, C++, Rust, Python, AWS, GCP, Kubernetes, Kafka, Cassandra

    EDUCATION
    M.S. in Computer Science, University of Washington (2014 - 2016)
    B.S. in Computer Engineering, UIUC (2010 - 2014)
    """
    profile = extract_candidate_profile(resume_text)
    analysis = classify_candidate_profile(profile)
    
    strategy = build_resume_strategy(profile, analysis)
    assert strategy.template_family == TemplateFamily.ATS_SENIOR
    assert strategy.career_stage in (CareerStage.SENIOR, CareerStage.SENIOR_PROFESSIONAL)
    assert strategy.page_budget == 2
    assert "senior_leadership_profile" in strategy.reason_codes


def test_05_engineering_lead_and_manager():
    """Verify engineering manager selects ATS_SENIOR with executive summary and leadership emphasis."""
    resume_text = """
    RACHEL ADAMS
    rachel.adams@email.com | Boston, MA

    EXECUTIVE SUMMARY
    Engineering Director with 10+ years scaling high-performing engineering teams and managing $8M budgets.

    EXPERIENCE
    Engineering Manager at CloudPeak Systems (2020 - Present)
    • Managed 3 engineering teams totaling 28 software engineers and 3 managers.
    • Improved delivery velocity by 45% through trunk-based development.

    Lead Architect at FinServe Solutions (2015 - 2020)
    • Led team of 10 engineers building payment settlement engine processing $500M daily.

    CORE COMPETENCIES
    Technical Leadership, Organizational Scaling, Budget Management ($8M+), Agile Transformation

    EDUCATION
    B.S. in Computer Science & Economics, MIT (2011 - 2015)
    """
    profile = extract_candidate_profile(resume_text)
    analysis = classify_candidate_profile(profile)
    
    strategy = build_resume_strategy(profile, analysis)
    assert strategy.template_family == TemplateFamily.ATS_SENIOR
    assert strategy.summary_strategy == "EXECUTIVE"
    assert strategy.page_budget == 2


def test_06_academic_and_research():
    """Verify academic researcher prioritizes publications and research."""
    resume_text = """
    DR. JONATHAN REID
    jonathan.reid@email.com | Cambridge, MA

    RESEARCH SUMMARY
    Postdoctoral Researcher in machine learning interpretability and deep neural networks.

    EDUCATION
    Ph.D. in Computer Science, Harvard University (2018 - 2023)
    B.S. in Mathematics & Computer Science, MIT (2014 - 2018)

    PUBLICATIONS
    • Reid, J., et al. "Adaptive Sparse Pruning for Large Language Models." NeurIPS 2023.
    • Reid, J., et al. "Convergence Guarantees in Stochastic Optimization." ICML 2022.

    TECHNICAL SKILLS
    PyTorch, JAX, Python, C++, CUDA, LaTeX
    """
    profile = extract_candidate_profile(resume_text)
    analysis = classify_candidate_profile(profile)
    
    strategy = build_resume_strategy(profile, analysis)
    assert strategy.highlight_education_top is True
    assert "publications" in strategy.section_order
    assert strategy.section_order.index("publications") < strategy.section_order.index("skills")


def test_07_career_switcher():
    """Verify career switcher prioritizes transferable skills and projects over past non-technical roles."""
    resume_text = """
    DEVON MILLER
    devon.miller@email.com | Denver, CO

    SUMMARY
    Senior Financial Auditor transitioned to Data Analyst with strong Python and SQL modeling skills.

    PROJECTS
    Automated Financial Fraud Detection Pipeline (Python, Pandas) (2023)
    • Built ML classification model identifying anomalous ledger transactions with 91% accuracy.

    EXPERIENCE
    Senior Auditor at KPMG (2019 - 2023)
    • Conducted financial audits for 14 enterprise clients managing $200M portfolios.

    TECHNICAL SKILLS
    Python, SQL, Tableau, PowerBI, Excel VBA

    EDUCATION
    B.S. in Accounting, Colorado State University (2015 - 2019)
    """
    profile = extract_candidate_profile(resume_text)
    # Verify classification of career switcher
    analysis = CareerClassificationResult(
        classification=CareerClassification.CAREER_SWITCHER,
        years_of_experience=4.0,
    )
    
    strategy = build_resume_strategy(profile, analysis)
    assert strategy.project_emphasis is True
    assert strategy.section_order.index("projects") < strategy.section_order.index("experience")


def test_08_uncertain_classification_fallback():
    """Verify unclassifiable profile falls back to ATS_CLASSIC_FALLBACK cleanly."""
    sparse_profile = CandidateProfile(
        personal={"name": "Unknown Candidate", "email": "candidate@email.com"},
        summary="Looking for opportunities.",
        skills=["Communication", "Organization"],
        education=[{"id": "edu_1", "degree": "High School Diploma", "institution": "City High"}],
    )
    analysis = CareerClassificationResult(
        classification=CareerClassification.OTHER,
        confidence=0.50,
        is_ambiguous=True,
    )
    strategy = build_resume_strategy(sparse_profile, analysis)
    assert strategy.template_family == TemplateFamily.ATS_CLASSIC_FALLBACK
    assert strategy.confidence <= 0.75
    assert "uncertain_classification_fallback" in strategy.reason_codes


def test_09_sparse_vs_dense_profile_density():
    """Verify density computation on sparse vs dense profiles."""
    from app.modules.resume.models import EvidenceUnit
    sparse_profile = CandidateProfile(
        personal={"name": "Sparse Person"},
        skills=["HTML", "CSS"],
        education=[{"id": "edu_1", "degree": "B.A.", "institution": "College"}],
    )
    assert calculate_content_density(sparse_profile) == ContentDensity.LOW

    dense_profile = CandidateProfile(
        personal={"name": "Dense Architect"},
        skills=["Python", "Go", "AWS", "K8s", "Docker", "Postgres", "Redis", "Kafka", "Terraform", "Java"],
        experience=[
            {"id": "exp_1", "company": "Corp A", "role": "Principal", "bullets": ["A", "B", "C", "D"]},
            {"id": "exp_2", "company": "Corp B", "role": "Senior", "bullets": ["E", "F", "G", "H"]},
            {"id": "exp_3", "company": "Corp C", "role": "Engineer", "bullets": ["I", "J", "K", "L"]},
        ],
        projects=[{"id": "p1", "title": "P1"}, {"id": "p2", "title": "P2"}, {"id": "p3", "title": "P3"}],
        education=[{"id": "edu_1", "degree": "M.S.", "institution": "University"}, {"id": "edu_2", "degree": "B.S.", "institution": "College"}],
        certifications=["AWS Pro", "CKA", "CISSP"],
        evidence_units=[
            EvidenceUnit(id=f"ev_{i}", section="experience", text=f"Claim {i}", original_text=f"Claim {i}", normalized_text=f"Claim {i}")
            for i in range(20)
        ],
    )
    assert calculate_content_density(dense_profile, years_of_experience=10.0) == ContentDensity.HIGH


def test_10_property_invariants_skill_prioritization_never_invents_unsupported_skills():
    """Verify skill prioritization strictly ignores JD skills that candidate does not possess."""
    candidate_skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
    
    jd = analyze_jd_requirements("""
    Senior Distributed Engineer
    Requirements:
    • Rust, Solidity, Web3, Kubernetes, AWS, GraphQL
    • Python, FastAPI, Docker
    """)
    
    prioritized = compute_skill_priorities(candidate_skills, jd)
    
    # Candidate skills in JD must be prioritized first
    assert prioritized[0] in ("Python", "FastAPI", "Docker")
    
    # CRITICAL INVARIANT: Unsupported JD skills (Rust, Solidity, Web3, Kubernetes, AWS, GraphQL) must NOT appear
    for unsupported in ["Rust", "Solidity", "Web3", "Kubernetes", "AWS", "GraphQL"]:
        assert unsupported not in prioritized
        assert unsupported.lower() not in [s.lower() for s in prioritized]


def test_11_property_invariants_empty_sections_excluded():
    """Verify empty sections are never included in strategy.section_order."""
    profile = CandidateProfile(
        personal={"name": "Simple Candidate", "email": "simple@email.com"},
        summary="Software engineer",
        skills=["Python"],
        education=[{"id": "edu_1", "degree": "B.S. CS", "institution": "University"}],
        # No experience, no projects, no certs, no achievements, no publications
    )
    strategy = build_resume_strategy(profile)
    
    assert "summary" in strategy.section_order
    assert "skills" in strategy.section_order
    assert "education" in strategy.section_order
    assert "experience" not in strategy.section_order
    assert "projects" not in strategy.section_order
    assert "certifications" not in strategy.section_order
    assert "achievements" not in strategy.section_order
    assert "publications" not in strategy.section_order
    assert "research" not in strategy.section_order


def test_12_structured_renderer_consumes_resume_strategy():
    """Verify structured text renderer consumes ResumeStrategy ordering without altering evidence."""
    resume_text = """
    ALEX VANCE
    alex.vance@email.com | Seattle, WA

    EDUCATION
    B.S. in Computer Science, UW (2020 - 2024)

    TECHNICAL SKILLS
    Python, C++, PyTorch

    PROJECTS
    Robotics Vision Pipeline
    • Achieved 60fps real-time object tracking with 94% accuracy.
    """
    profile = extract_candidate_profile(resume_text)
    strategy = build_resume_strategy(profile)
    
    rendered = render_candidate_profile_to_text(profile, strategy)
    
    # Verify rendered text exists and contains candidate name, education, and project
    assert "ALEX VANCE" in rendered
    assert "EDUCATION" in rendered
    assert "Robotics Vision Pipeline" in rendered
    assert "60fps" in rendered
    assert "94%" in rendered
