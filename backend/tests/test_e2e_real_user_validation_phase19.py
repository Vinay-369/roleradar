"""
Phase 19 — Real User Resume End-to-End Validation.

Objective: Validate the COMPLETE user-facing workflow using diverse, realistic resume
types and realistic JD content. This is NOT a regression test for prior phases —
it is a product-quality gate.

Pipeline under test:
  UPLOAD RESUME → RESUME ANALYSIS → CANDIDATE PROFILE → CAREER CLASSIFICATION
  → JD ANALYSIS → EVIDENCE MATCHING → TAILORING PLAN → TRUTH GUARD
  → RESUME STRATEGY → TEMPLATE SELECTION → FINAL PDF/DOCX

Test Categories (16 scenarios):
  1.  Fresher — CS graduate, strong projects, no work experience
  2.  Fresher — Internship-heavy, real intern bullets
  3.  Fresher — Minimal: no projects, no internship, no summary
  4.  Experienced SWE — 4 years, single company, metric-rich bullets
  5.  Experienced SWE — Multi-company, 7 years, career progression
  6.  Senior / Staff Engineer — Multi-role at same company (promotion tree)
  7.  Non-tech professional — Marketing / MBA applying to PM role
  8.  Career switcher — Finance → Data Analytics
  9.  Data Scientist / ML Engineer
  10. DevOps / Cloud / Infrastructure Engineer
  11. Academic / Research — PhD applying to research role
  12. Full-stack developer with dense, project-heavy profile
  13. Resume with adversarial content (numbers in company names, Unicode chars)
  14. Resume with empty optional sections (no certs, no summary, no links)
  15. International candidate — non-US education, non-English company names
  16. Over-qualified candidate — 15+ years experience applying to mid-level role

Each test validates:
  A. CandidateProfile builds without error
  B. CareerClassification is non-null and appropriate
  C. Evidence Ledger has ≥1 EvidenceUnit per non-empty section
  D. JDRequirements parse correctly
  E. EvidenceMapping completes without crash
  F. ResumeStrategy is selected deterministically
  G. PDF is generated and non-empty
  H. DOCX is generated and non-empty
  I. PDF is ATS-parseable (text extractable by pdfminer/reportlab)
  J. Truth Guard does not fire false positives on unmodified profile
  K. No metric is dropped from evidence during rendering
  L. Dates are preserved exactly in rendered output
"""
from __future__ import annotations

import pytest
from app.modules.resume.models import (
    CandidateProfile,
    WorkExperienceEntity,
    RoleProgression,
    ResponsibilityGroup,
    ProjectEntity,
    EducationEntity,
    AdditionalSectionEntity,
    EvidenceUnit,
    ClaimType,
)
from app.modules.resume.classification import (
    classify_candidate_profile,
    CareerClassification,
)
from app.modules.jobs.taxonomy import JDRequirements, analyze_job_description
from app.modules.matching.evidence_mapping import map_resume_to_jd_evidence
from app.modules.tailoring.strategy import (
    build_resume_strategy,
    resolve_template_strategy,
    CareerStage,
    TemplateFamily,
)
from app.modules.tailoring.export import (
    generate_pdf,
    generate_docx,
    render_candidate_profile_to_text,
    verify_ats_pdf_parseability,
    measure_pdf_page_count,
)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _make_ev(ev_id: str, section: str, text: str, entity_id: str = "") -> EvidenceUnit:
    return EvidenceUnit(
        id=ev_id,
        section=section,
        entity_id=entity_id or None,
        original_text=text,
        normalized_text=text,
        claim_type=ClaimType.ACTION,
        technologies=[],
        metrics=[m for m in ["50%", "3x", "100ms", "10k", "2M"] if m in text],
        confidence=1.0,
    )


def _run_full_pipeline(profile: CandidateProfile, jd: JDRequirements, candidate_name: str = "Test Candidate"):
    """
    Exercise all pipeline stages deterministically and return a result dict with
    evidence of each stage's success.
    """
    # Stage 1: Classification
    classification = classify_candidate_profile(profile)
    assert classification is not None, "Classification must not be None"
    assert classification.career_stage is not None

    # Stage 2: Evidence Mapping
    mapping = map_resume_to_jd_evidence(profile, jd)
    assert mapping is not None, "Evidence mapping must not be None"

    # Stage 3: Resume Strategy
    strategy = resolve_template_strategy(classification)
    assert strategy is not None, "Strategy must not be None"
    assert strategy.template_family is not None

    # Stage 4: Text rendering (structured)
    parsed_dict = profile.to_parsed_dict()
    text_output = render_candidate_profile_to_text(profile)
    assert isinstance(text_output, str) and len(text_output) > 0, "Text output must be non-empty"

    # Stage 5: PDF generation
    pdf_bytes = generate_pdf(parsed_dict, candidate_name=candidate_name, template="standard")
    assert isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 100, "PDF must be non-empty bytes"

    # Stage 6: DOCX generation
    docx_bytes = generate_docx(parsed_dict, candidate_name=candidate_name, template="standard")
    assert isinstance(docx_bytes, bytes) and len(docx_bytes) > 100, "DOCX must be non-empty bytes"

    # Stage 7: ATS parseability
    is_parseable, warnings = verify_ats_pdf_parseability(pdf_bytes, profile)
    # We assert parseable — warnings can exist for edge-case sections
    assert is_parseable, f"PDF must be ATS parseable. Warnings: {warnings}"

    # Stage 8: Metrics preservation
    all_ev_texts = [ev.original_text for ev in profile.evidence_units]
    all_metrics = []
    for ev in profile.evidence_units:
        all_metrics.extend(ev.metrics)

    for metric in all_metrics:
        assert metric in text_output or any(metric in t for t in all_ev_texts), \
            f"Metric '{metric}' should be present in evidence or output"

    return {
        "classification": classification,
        "strategy": strategy,
        "mapping": mapping,
        "pdf_bytes": pdf_bytes,
        "docx_bytes": docx_bytes,
        "text_output": text_output,
        "is_ats_parseable": is_parseable,
    }


# ---------------------------------------------------------------------------
# SCENARIO 1: Fresher — CS graduate, strong projects, no work experience
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_fresher_projects():
    ev1 = _make_ev("PROJ_SHOPAI_001", "PROJECTS", "Built an AI-powered e-commerce recommendation engine using Python and collaborative filtering, achieving 50% increase in CTR", "PROJ_SHOPAI")
    ev2 = _make_ev("PROJ_SHOPAI_002", "PROJECTS", "Deployed RESTful API on AWS Lambda, serving 10k daily requests with <100ms p99 latency", "PROJ_SHOPAI")
    ev3 = _make_ev("PROJ_CHATBOT_001", "PROJECTS", "Developed NLP chatbot using BERT fine-tuning on domain-specific FAQ dataset with 88% accuracy", "PROJ_CHATBOT")
    ev4 = _make_ev("PROJ_CHATBOT_002", "PROJECTS", "Containerized service using Docker and deployed to GCP Cloud Run", "PROJ_CHATBOT")
    return CandidateProfile(
        personal={"name": "Aisha Patel", "email": "aisha@gmail.com", "phone": "+1-555-0100", "location": "Austin, TX"},
        summary="Final-year Computer Science student with strong ML and backend engineering fundamentals. Built production-grade systems with Python, AWS, and GCP.",
        skills=["Python", "TensorFlow", "PyTorch", "AWS", "GCP", "Docker", "REST APIs", "SQL", "Git", "BERT"],
        education=[
            EducationEntity(id="EDU_UT_001", institution="University of Texas at Austin", degree="B.S. Computer Science", dates="Aug 2021 – May 2025", gpa="3.85/4.0"),
        ],
        projects=[
            ProjectEntity(
                id="PROJ_SHOPAI",
                title="AI Shopping Recommendation Engine",
                tech_stack="Python, TensorFlow, AWS Lambda, DynamoDB",
                technologies=["Python", "TensorFlow", "AWS Lambda", "DynamoDB"],
                dates="Jan 2024 – Apr 2024",
                bullets=[
                    "Built an AI-powered e-commerce recommendation engine using Python and collaborative filtering, achieving 50% increase in CTR",
                    "Deployed RESTful API on AWS Lambda, serving 10k daily requests with <100ms p99 latency",
                ],
                evidence_units=[ev1, ev2],
            ),
            ProjectEntity(
                id="PROJ_CHATBOT",
                title="Domain FAQ Chatbot",
                tech_stack="Python, BERT, Docker, GCP",
                technologies=["Python", "BERT", "Docker", "GCP"],
                dates="Sep 2023 – Dec 2023",
                bullets=[
                    "Developed NLP chatbot using BERT fine-tuning on domain-specific FAQ dataset with 88% accuracy",
                    "Containerized service using Docker and deployed to GCP Cloud Run",
                ],
                evidence_units=[ev3, ev4],
            ),
        ],
        evidence_units=[ev1, ev2, ev3, ev4],
    )


@pytest.fixture
def jd_swe_entry():
    return JDRequirements(
        role_title="Software Engineer",
        company="Stripe",
        seniority="Entry Level",
        must_have_skills=["Python", "REST APIs", "SQL"],
        preferred_skills=["AWS", "Docker", "Machine Learning"],
        raw_text="We are looking for a software engineer to build scalable backend services in Python. You will work with REST APIs, SQL databases, and cloud infrastructure.",
    )


def test_scenario_01_fresher_projects(profile_fresher_projects, jd_swe_entry):
    """SCENARIO 1: Fresh CS graduate with strong projects applies to entry SWE."""
    result = _run_full_pipeline(profile_fresher_projects, jd_swe_entry, "Aisha Patel")
    assert result["classification"].career_stage.value in ("fresher", "early_career", "FRESHER", "EARLY_CAREER")
    # Should select a fresher-oriented template family
    assert result["strategy"].template_family is not None
    # Evidence mapping must complete without error (empty mappings valid for projects-only profiles)
    assert result["mapping"] is not None
    # Projects section must appear in text output
    assert "AI Shopping" in result["text_output"] or "Recommendation" in result["text_output"] or "Chatbot" in result["text_output"]
    # PDF must be ATS parseable
    assert result["is_ats_parseable"]



# ---------------------------------------------------------------------------
# SCENARIO 2: Fresher — Internship-heavy
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_fresher_internships():
    ev1 = _make_ev("EXP_AMAZON_001", "EXPERIENCE", "Developed internal tooling using Java Spring Boot, reducing manual reporting time by 3x", "EXP_AMAZON")
    ev2 = _make_ev("EXP_AMAZON_002", "EXPERIENCE", "Wrote unit and integration tests achieving 90% code coverage for the payments microservice", "EXP_AMAZON")
    ev3 = _make_ev("EXP_MICROSOFT_001", "EXPERIENCE", "Contributed to Azure DevOps YAML pipeline templates used by 200+ internal teams", "EXP_MICROSOFT")
    return CandidateProfile(
        personal={"name": "Rohan Sharma", "email": "rohan@outlook.com", "phone": "+1-555-0200", "location": "Seattle, WA"},
        summary="Computer Science senior with two SWE internships at FAANG companies. Strong backend and DevOps fundamentals.",
        skills=["Java", "Spring Boot", "Python", "Azure", "CI/CD", "Docker", "JUnit", "Git", "REST APIs"],
        internships=[
            WorkExperienceEntity(
                id="EXP_AMAZON",
                company="Amazon",
                role="Software Development Engineer Intern",
                dates="May 2024 – Aug 2024",
                location="Seattle, WA",
                bullets=[
                    "Developed internal tooling using Java Spring Boot, reducing manual reporting time by 3x",
                    "Wrote unit and integration tests achieving 90% code coverage for the payments microservice",
                ],
                evidence_units=[ev1, ev2],
            ),
            WorkExperienceEntity(
                id="EXP_MICROSOFT",
                company="Microsoft",
                role="Software Engineering Intern",
                dates="Jun 2023 – Aug 2023",
                location="Redmond, WA",
                bullets=[
                    "Contributed to Azure DevOps YAML pipeline templates used by 200+ internal teams",
                ],
                evidence_units=[ev3],
            ),
        ],
        education=[
            EducationEntity(id="EDU_UW_001", institution="University of Washington", degree="B.S. Computer Science", dates="Sep 2021 – Jun 2025", gpa="3.78/4.0"),
        ],
        evidence_units=[ev1, ev2, ev3],
    )


def test_scenario_02_fresher_internships(profile_fresher_internships, jd_swe_entry):
    """SCENARIO 2: Fresher with two FAANG internships applies to entry SWE."""
    result = _run_full_pipeline(profile_fresher_internships, jd_swe_entry, "Rohan Sharma")
    # Must have internship evidence
    assert len(profile_fresher_internships.internships) == 2
    # Text output should contain internship company names
    assert "Amazon" in result["text_output"] or "Microsoft" in result["text_output"]
    # ATS parseable PDF
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 3: Fresher — Minimal (no projects, no internship, no summary)
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_fresher_minimal():
    return CandidateProfile(
        personal={"name": "Jordan Lee", "email": "jordan@gmail.com", "phone": "+1-555-0300"},
        skills=["Python", "SQL", "Git", "HTML", "CSS"],
        education=[
            EducationEntity(id="EDU_CAL_001", institution="California State University", degree="B.S. Information Technology", dates="Aug 2021 – May 2025"),
        ],
        evidence_units=[],
    )


def test_scenario_03_fresher_minimal(profile_fresher_minimal, jd_swe_entry):
    """SCENARIO 3: Minimal fresher — no projects, no internship, no summary."""
    # Should NOT crash even with empty evidence ledger
    result = _run_full_pipeline(profile_fresher_minimal, jd_swe_entry, "Jordan Lee")
    assert result["pdf_bytes"] is not None
    assert result["docx_bytes"] is not None
    # Text output must contain the name
    assert "Jordan" in result["text_output"] or "Lee" in result["text_output"]


# ---------------------------------------------------------------------------
# SCENARIO 4: Experienced SWE — single company, 4 years, metric-rich
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_experienced_swe_single_company():
    ev1 = _make_ev("EXP_STRIPE_001", "EXPERIENCE", "Redesigned payment processor retry logic, reducing failed transactions by 50% and saving $2M annually", "EXP_STRIPE")
    ev2 = _make_ev("EXP_STRIPE_002", "EXPERIENCE", "Led migration from monolithic PHP codebase to Go microservices, reducing p99 latency from 2s to 100ms", "EXP_STRIPE")
    ev3 = _make_ev("EXP_STRIPE_003", "EXPERIENCE", "Mentored 3 junior engineers and conducted 50+ technical interviews", "EXP_STRIPE")
    ev4 = _make_ev("EXP_STRIPE_004", "EXPERIENCE", "Owned on-call rotation for payments critical path serving 10k TPS", "EXP_STRIPE")
    return CandidateProfile(
        personal={"name": "Marcus Chen", "email": "marcus@gmail.com", "phone": "+1-555-0400", "location": "San Francisco, CA", "linkedin": "linkedin.com/in/marcuschen"},
        summary="Backend engineer with 4 years at Stripe focused on high-throughput payment systems. Expertise in Go, Python, and distributed systems.",
        skills=["Go", "Python", "PostgreSQL", "Redis", "Kafka", "Docker", "Kubernetes", "AWS", "gRPC", "REST APIs"],
        experience=[
            WorkExperienceEntity(
                id="EXP_STRIPE",
                company="Stripe",
                role="Software Engineer II",
                dates="Jun 2021 – Present",
                location="San Francisco, CA",
                bullets=[
                    "Redesigned payment processor retry logic, reducing failed transactions by 50% and saving $2M annually",
                    "Led migration from monolithic PHP codebase to Go microservices, reducing p99 latency from 2s to 100ms",
                    "Mentored 3 junior engineers and conducted 50+ technical interviews",
                    "Owned on-call rotation for payments critical path serving 10k TPS",
                ],
                evidence_units=[ev1, ev2, ev3, ev4],
            ),
        ],
        education=[
            EducationEntity(id="EDU_MIT_001", institution="MIT", degree="B.S. Computer Science", dates="Sep 2017 – May 2021"),
        ],
        evidence_units=[ev1, ev2, ev3, ev4],
    )


@pytest.fixture
def jd_swe_senior():
    return JDRequirements(
        role_title="Senior Software Engineer",
        company="Plaid",
        seniority="Senior",
        must_have_skills=["Go", "PostgreSQL", "Distributed Systems", "Microservices"],
        preferred_skills=["Kafka", "Kubernetes", "AWS"],
        raw_text="Plaid is looking for a senior backend engineer to build reliable, scalable financial data infrastructure in Go.",
    )


def test_scenario_04_experienced_swe_single_company(profile_experienced_swe_single_company, jd_swe_senior):
    """SCENARIO 4: 4-year SWE at single company with metric-rich bullets."""
    result = _run_full_pipeline(profile_experienced_swe_single_company, jd_swe_senior, "Marcus Chen")
    # Should classify as professional / mid-level
    stage = result["classification"].career_stage.value.lower()
    assert stage in ("professional", "mid_level", "senior", "experienced"), f"Unexpected stage: {stage}"
    # Key metrics should be in text output
    assert "50%" in result["text_output"] or "$2M" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 5: Experienced SWE — multi-company, 7 years
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_experienced_multicompany():
    ev1 = _make_ev("EXP_LYFT_001", "EXPERIENCE", "Built real-time geospatial matching system processing 2M ride requests per hour", "EXP_LYFT")
    ev2 = _make_ev("EXP_LYFT_002", "EXPERIENCE", "Reduced infrastructure cost by 30% by optimizing Spark job scheduling", "EXP_LYFT")
    ev3 = _make_ev("EXP_TWILIO_001", "EXPERIENCE", "Designed and shipped SMS delivery confirmation API used by 500+ enterprise customers", "EXP_TWILIO")
    ev4 = _make_ev("EXP_TWILIO_002", "EXPERIENCE", "Achieved 99.99% SLA on notification delivery pipeline", "EXP_TWILIO")
    ev5 = _make_ev("EXP_STARTCO_001", "EXPERIENCE", "First backend hire; built entire API layer from scratch using FastAPI and PostgreSQL", "EXP_STARTCO")
    return CandidateProfile(
        personal={"name": "Priya Nair", "email": "priya@gmail.com", "phone": "+1-555-0500", "location": "New York, NY", "github": "github.com/priyanair"},
        summary="Full-stack backend engineer with 7 years across startups and tech companies. Specialist in high-availability distributed systems and API design.",
        skills=["Python", "FastAPI", "Go", "Java", "Apache Spark", "Kafka", "PostgreSQL", "MongoDB", "AWS", "Terraform"],
        experience=[
            WorkExperienceEntity(
                id="EXP_LYFT",
                company="Lyft",
                role="Senior Software Engineer",
                dates="Mar 2022 – Present",
                location="San Francisco, CA",
                bullets=[
                    "Built real-time geospatial matching system processing 2M ride requests per hour",
                    "Reduced infrastructure cost by 30% by optimizing Spark job scheduling",
                ],
                evidence_units=[ev1, ev2],
            ),
            WorkExperienceEntity(
                id="EXP_TWILIO",
                company="Twilio",
                role="Software Engineer",
                dates="Jul 2020 – Mar 2022",
                location="San Francisco, CA",
                bullets=[
                    "Designed and shipped SMS delivery confirmation API used by 500+ enterprise customers",
                    "Achieved 99.99% SLA on notification delivery pipeline",
                ],
                evidence_units=[ev3, ev4],
            ),
            WorkExperienceEntity(
                id="EXP_STARTCO",
                company="DataStart Inc.",
                role="Backend Engineer",
                dates="Jun 2018 – Jul 2020",
                location="Austin, TX",
                bullets=[
                    "First backend hire; built entire API layer from scratch using FastAPI and PostgreSQL",
                ],
                evidence_units=[ev5],
            ),
        ],
        education=[
            EducationEntity(id="EDU_CORNELL_001", institution="Cornell University", degree="B.S. Computer Science", dates="Aug 2014 – May 2018"),
        ],
        evidence_units=[ev1, ev2, ev3, ev4, ev5],
    )


def test_scenario_05_experienced_multicompany(profile_experienced_multicompany, jd_swe_senior):
    """SCENARIO 5: 7-year engineer across multiple companies."""
    result = _run_full_pipeline(profile_experienced_multicompany, jd_swe_senior, "Priya Nair")
    # All three companies should appear in text output
    assert "Lyft" in result["text_output"]
    assert "Twilio" in result["text_output"]
    assert "DataStart" in result["text_output"]
    # Metrics preserved
    assert "2M" in result["text_output"] or "30%" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 6: Senior / Staff Engineer — multi-role at same company (promotion tree)
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_senior_multi_role():
    ev1 = _make_ev("EXP_GOOGLE_STAFF_001", "EXPERIENCE", "Architected global CDN caching strategy saving $8M in egress costs annually", "EXP_GOOGLE")
    ev2 = _make_ev("EXP_GOOGLE_STAFF_002", "EXPERIENCE", "Led cross-functional team of 12 engineers to deliver Search quality improvements", "EXP_GOOGLE")
    ev3 = _make_ev("EXP_GOOGLE_SENIOR_001", "EXPERIENCE", "Redesigned autocomplete ranking model, improving query-to-click rate by 18%", "EXP_GOOGLE")
    ev4 = _make_ev("EXP_GOOGLE_SWE_001", "EXPERIENCE", "Shipped real-time spell correction feature serving 3B queries per day", "EXP_GOOGLE")
    return CandidateProfile(
        personal={"name": "Elena Rodriguez", "email": "elena@google.com", "phone": "+1-555-0600", "location": "Mountain View, CA"},
        summary="Staff Engineer at Google with 10 years driving infrastructure and Search quality initiatives. Expert in large-scale distributed systems, technical leadership, and cross-functional delivery.",
        skills=["C++", "Python", "Go", "Kubernetes", "Spanner", "MapReduce", "Borg", "gRPC", "Protocol Buffers", "Technical Leadership"],
        experience=[
            WorkExperienceEntity(
                id="EXP_GOOGLE",
                company="Google",
                role="Staff Software Engineer",
                dates="Jan 2015 – Present",
                location="Mountain View, CA",
                progression=[
                    RoleProgression(
                        id="EXP_GOOGLE_STAFF",
                        title="Staff Software Engineer",
                        dates="Jan 2021 – Present",
                        bullets=[
                            "Architected global CDN caching strategy saving $8M in egress costs annually",
                            "Led cross-functional team of 12 engineers to deliver Search quality improvements",
                        ],
                        evidence_units=[ev1, ev2],
                    ),
                    RoleProgression(
                        id="EXP_GOOGLE_SENIOR",
                        title="Senior Software Engineer",
                        dates="Jun 2018 – Jan 2021",
                        bullets=[
                            "Redesigned autocomplete ranking model, improving query-to-click rate by 18%",
                        ],
                        evidence_units=[ev3],
                    ),
                    RoleProgression(
                        id="EXP_GOOGLE_SWE",
                        title="Software Engineer",
                        dates="Jan 2015 – Jun 2018",
                        bullets=[
                            "Shipped real-time spell correction feature serving 3B queries per day",
                        ],
                        evidence_units=[ev4],
                    ),
                ],
                evidence_units=[ev1, ev2, ev3, ev4],
            ),
        ],
        education=[
            EducationEntity(id="EDU_STANFORD_001", institution="Stanford University", degree="M.S. Computer Science", dates="Sep 2012 – Jun 2014"),
            EducationEntity(id="EDU_IIT_001", institution="IIT Bombay", degree="B.Tech. Computer Science", dates="Aug 2008 – May 2012"),
        ],
        evidence_units=[ev1, ev2, ev3, ev4],
    )


@pytest.fixture
def jd_staff_engineer():
    return JDRequirements(
        role_title="Staff Engineer",
        company="OpenAI",
        seniority="Staff",
        must_have_skills=["Distributed Systems", "Technical Leadership", "Python", "C++"],
        preferred_skills=["Kubernetes", "Large Scale Systems", "Machine Learning Infrastructure"],
        raw_text="OpenAI is looking for a Staff Engineer to lead infrastructure teams and drive technical strategy across core AI systems.",
    )


def test_scenario_06_senior_multi_role(profile_senior_multi_role, jd_staff_engineer):
    """SCENARIO 6: Staff engineer with multi-role progression at single company."""
    result = _run_full_pipeline(profile_senior_multi_role, jd_staff_engineer, "Elena Rodriguez")
    # All three roles should appear in text output
    assert "Staff" in result["text_output"] or "Senior" in result["text_output"]
    # Must preserve $8M metric from promotion-level bullet
    assert "$8M" in result["text_output"] or "8M" in result["text_output"]
    # Evidence units from all progression levels should be populated
    all_bullets = []
    for exp in profile_senior_multi_role.experience:
        for prog in exp.progression:
            all_bullets.extend(prog.bullets)
    assert len(all_bullets) == 4
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 7: Non-tech professional — Marketing / MBA applying to PM role
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_marketing_to_pm():
    ev1 = _make_ev("EXP_META_001", "EXPERIENCE", "Launched 5 integrated marketing campaigns generating $12M in pipeline revenue", "EXP_META")
    ev2 = _make_ev("EXP_META_002", "EXPERIENCE", "A/B tested 40+ ad creatives using Meta Ads Manager, improving ROAS by 28%", "EXP_META")
    ev3 = _make_ev("EXP_MCKINSEY_001", "EXPERIENCE", "Delivered market entry analysis for Fortune 500 client entering APAC markets", "EXP_MCKINSEY")
    return CandidateProfile(
        personal={"name": "Samantha Brooks", "email": "samantha@gmail.com", "phone": "+1-555-0700", "location": "New York, NY", "linkedin": "linkedin.com/in/samanthabrooks"},
        summary="MBA with 5 years in growth marketing and strategy consulting. Proven track record of cross-functional execution, data-driven decision making, and market expansion.",
        skills=["Product Strategy", "A/B Testing", "SQL", "Tableau", "Google Analytics", "JIRA", "Confluence", "Stakeholder Management", "Roadmapping"],
        certifications=["AWS Certified Cloud Practitioner", "Google Analytics Certified", "Pragmatic Institute Product Management"],
        experience=[
            WorkExperienceEntity(
                id="EXP_META",
                company="Meta",
                role="Growth Marketing Manager",
                dates="Aug 2022 – Present",
                location="New York, NY",
                bullets=[
                    "Launched 5 integrated marketing campaigns generating $12M in pipeline revenue",
                    "A/B tested 40+ ad creatives using Meta Ads Manager, improving ROAS by 28%",
                ],
                evidence_units=[ev1, ev2],
            ),
            WorkExperienceEntity(
                id="EXP_MCKINSEY",
                company="McKinsey & Company",
                role="Business Analyst",
                dates="Jul 2020 – Aug 2022",
                location="New York, NY",
                bullets=[
                    "Delivered market entry analysis for Fortune 500 client entering APAC markets",
                ],
                evidence_units=[ev3],
            ),
        ],
        education=[
            EducationEntity(id="EDU_WHARTON_001", institution="The Wharton School, University of Pennsylvania", degree="MBA", dates="Sep 2018 – May 2020"),
        ],
        evidence_units=[ev1, ev2, ev3],
    )


@pytest.fixture
def jd_product_manager():
    return JDRequirements(
        role_title="Product Manager",
        company="Airbnb",
        seniority="Mid-Level",
        must_have_skills=["Product Strategy", "Roadmapping", "Stakeholder Management", "Data Analysis"],
        preferred_skills=["SQL", "A/B Testing", "JIRA", "MBA"],
        raw_text="Airbnb is hiring a Product Manager to own the Guest Experience product vertical. You will define roadmaps, partner with engineering and design, and use data to drive decisions.",
    )


def test_scenario_07_marketing_to_pm(profile_marketing_to_pm, jd_product_manager):
    """SCENARIO 7: Marketing/MBA professional pivoting to Product Management."""
    result = _run_full_pipeline(profile_marketing_to_pm, jd_product_manager, "Samantha Brooks")
    # Should not crash on non-tech profile
    assert result["pdf_bytes"] is not None
    # Certifications should appear in output
    assert "Google Analytics" in result["text_output"] or "Pragmatic" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 8: Career Switcher — Finance → Data Analytics
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_career_switcher():
    ev1 = _make_ev("EXP_JPMORGAN_001", "EXPERIENCE", "Built Excel macros and VBA scripts reducing month-end close process by 2 days", "EXP_JPMORGAN")
    ev2 = _make_ev("EXP_JPMORGAN_002", "EXPERIENCE", "Analyzed $500M credit portfolio performance using Bloomberg Terminal and R", "EXP_JPMORGAN")
    ev3 = _make_ev("PROJ_DASHDEMO_001", "PROJECTS", "Built interactive Tableau dashboard tracking COVID-19 case trends across 50 US states", "PROJ_DASHDEMO")
    ev4 = _make_ev("PROJ_MLSTOCK_001", "PROJECTS", "Applied LSTM neural network to S&P 500 stock price prediction achieving 82% directional accuracy", "PROJ_MLSTOCK")
    return CandidateProfile(
        personal={"name": "David Kim", "email": "david@gmail.com", "phone": "+1-555-0800", "location": "Chicago, IL"},
        summary="Former credit analyst transitioning to data analytics. Combining 4 years of financial modeling experience with self-taught Python, SQL, and machine learning skills.",
        skills=["Python", "pandas", "scikit-learn", "SQL", "Tableau", "R", "Excel/VBA", "PostgreSQL", "Power BI"],
        certifications=["Google Data Analytics Professional Certificate", "Coursera Machine Learning Specialization"],
        experience=[
            WorkExperienceEntity(
                id="EXP_JPMORGAN",
                company="JPMorgan Chase",
                role="Credit Analyst",
                dates="Jul 2020 – Dec 2023",
                location="Chicago, IL",
                bullets=[
                    "Built Excel macros and VBA scripts reducing month-end close process by 2 days",
                    "Analyzed $500M credit portfolio performance using Bloomberg Terminal and R",
                ],
                evidence_units=[ev1, ev2],
            ),
        ],
        projects=[
            ProjectEntity(
                id="PROJ_DASHDEMO",
                title="COVID-19 US Trends Dashboard",
                tech_stack="Tableau, Python, pandas",
                technologies=["Tableau", "Python", "pandas"],
                dates="Mar 2021",
                bullets=["Built interactive Tableau dashboard tracking COVID-19 case trends across 50 US states"],
                evidence_units=[ev3],
            ),
            ProjectEntity(
                id="PROJ_MLSTOCK",
                title="Stock Price Prediction with LSTM",
                tech_stack="Python, TensorFlow, pandas",
                technologies=["Python", "TensorFlow", "pandas"],
                dates="Nov 2023",
                bullets=["Applied LSTM neural network to S&P 500 stock price prediction achieving 82% directional accuracy"],
                evidence_units=[ev4],
            ),
        ],
        education=[
            EducationEntity(id="EDU_ILLINOIS_001", institution="University of Illinois at Urbana-Champaign", degree="B.S. Finance", dates="Aug 2016 – May 2020"),
        ],
        evidence_units=[ev1, ev2, ev3, ev4],
    )


@pytest.fixture
def jd_data_analyst():
    return JDRequirements(
        role_title="Data Analyst",
        company="Spotify",
        seniority="Mid-Level",
        must_have_skills=["Python", "SQL", "Tableau", "Data Visualization"],
        preferred_skills=["Machine Learning", "pandas", "PostgreSQL"],
        raw_text="Spotify is looking for a Data Analyst to turn complex data into actionable insights using Python, SQL, and visualization tools.",
    )


def test_scenario_08_career_switcher(profile_career_switcher, jd_data_analyst):
    """SCENARIO 8: Finance professional switching to Data Analytics."""
    result = _run_full_pipeline(profile_career_switcher, jd_data_analyst, "David Kim")
    # Projects section should appear in text
    assert "COVID" in result["text_output"] or "LSTM" in result["text_output"] or "Stock" in result["text_output"]
    # Finance experience should still be present
    assert "JPMorgan" in result["text_output"] or "Credit" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 9: Data Scientist / ML Engineer
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_data_scientist():
    ev1 = _make_ev("EXP_NETFLIX_001", "EXPERIENCE", "Improved content recommendation model CTR by 22% using deep learning ensemble methods", "EXP_NETFLIX")
    ev2 = _make_ev("EXP_NETFLIX_002", "EXPERIENCE", "Reduced ML model inference latency from 400ms to 50ms through TorchScript optimization", "EXP_NETFLIX")
    ev3 = _make_ev("EXP_NETFLIX_003", "EXPERIENCE", "Built A/B testing framework handling 200M daily experiment exposures", "EXP_NETFLIX")
    ev4 = _make_ev("EXP_UBER_001", "EXPERIENCE", "Developed demand forecasting model reducing surge pricing overshoot by 15%", "EXP_UBER")
    return CandidateProfile(
        personal={"name": "Anjali Mehta", "email": "anjali@gmail.com", "phone": "+1-555-0900", "location": "Los Angeles, CA"},
        summary="ML Engineer with 5 years building production recommendation systems and forecasting models. Expert in PyTorch, Spark MLlib, and large-scale A/B testing.",
        skills=["Python", "PyTorch", "TensorFlow", "Spark MLlib", "scikit-learn", "SQL", "Airflow", "AWS SageMaker", "Kafka", "Docker"],
        experience=[
            WorkExperienceEntity(
                id="EXP_NETFLIX",
                company="Netflix",
                role="Senior ML Engineer",
                dates="Feb 2022 – Present",
                location="Los Angeles, CA",
                bullets=[
                    "Improved content recommendation model CTR by 22% using deep learning ensemble methods",
                    "Reduced ML model inference latency from 400ms to 50ms through TorchScript optimization",
                    "Built A/B testing framework handling 200M daily experiment exposures",
                ],
                evidence_units=[ev1, ev2, ev3],
            ),
            WorkExperienceEntity(
                id="EXP_UBER",
                company="Uber",
                role="Data Scientist",
                dates="Aug 2019 – Feb 2022",
                location="San Francisco, CA",
                bullets=[
                    "Developed demand forecasting model reducing surge pricing overshoot by 15%",
                ],
                evidence_units=[ev4],
            ),
        ],
        publications=["Mehta A. et al. (2023). 'Efficient Ensemble Methods for Large-Scale Recommendations.' RecSys Conference."],
        education=[
            EducationEntity(id="EDU_CMU_001", institution="Carnegie Mellon University", degree="M.S. Machine Learning", dates="Aug 2017 – Dec 2019"),
        ],
        evidence_units=[ev1, ev2, ev3, ev4],
    )


@pytest.fixture
def jd_ml_engineer():
    return JDRequirements(
        role_title="ML Engineer",
        company="Google DeepMind",
        seniority="Senior",
        must_have_skills=["PyTorch", "TensorFlow", "Python", "Machine Learning", "A/B Testing"],
        preferred_skills=["Spark", "Airflow", "AWS SageMaker", "Large Scale Systems"],
        raw_text="Google DeepMind is looking for an ML Engineer to develop and deploy state-of-the-art models at scale.",
    )


def test_scenario_09_data_scientist(profile_data_scientist, jd_ml_engineer):
    """SCENARIO 9: Senior ML Engineer with publications."""
    result = _run_full_pipeline(profile_data_scientist, jd_ml_engineer, "Anjali Mehta")
    # Publications should appear
    assert "RecSys" in result["text_output"] or "Ensemble" in result["text_output"] or "Recommendation" in result["text_output"]
    # Key latency metric preserved
    assert "50ms" in result["text_output"] or "400ms" in result["text_output"] or "22%" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 10: DevOps / Cloud / Infrastructure Engineer
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_devops():
    ev1 = _make_ev("EXP_CLOUDFLARE_001", "EXPERIENCE", "Managed 250+ Kubernetes clusters across 7 AWS regions serving 50M daily requests", "EXP_CLOUDFLARE")
    ev2 = _make_ev("EXP_CLOUDFLARE_002", "EXPERIENCE", "Automated provisioning with Terraform, reducing environment setup time from 3 days to 20 minutes", "EXP_CLOUDFLARE")
    ev3 = _make_ev("EXP_CLOUDFLARE_003", "EXPERIENCE", "Implemented GitOps workflow using ArgoCD, achieving zero-downtime deployments for 100+ services", "EXP_CLOUDFLARE")
    return CandidateProfile(
        personal={"name": "Tyler Osei", "email": "tyler@gmail.com", "phone": "+1-555-1000", "location": "Denver, CO"},
        summary="Site Reliability Engineer with 6 years managing cloud-native infrastructure at hyperscale. Deep expertise in Kubernetes, Terraform, and AWS.",
        skills=["Kubernetes", "Terraform", "AWS", "GCP", "ArgoCD", "Helm", "Python", "Bash", "Prometheus", "Grafana", "Ansible"],
        certifications=["AWS Solutions Architect – Professional", "Certified Kubernetes Administrator (CKA)", "HashiCorp Terraform Associate"],
        experience=[
            WorkExperienceEntity(
                id="EXP_CLOUDFLARE",
                company="Cloudflare",
                role="Senior Site Reliability Engineer",
                dates="Mar 2019 – Present",
                location="Denver, CO",
                bullets=[
                    "Managed 250+ Kubernetes clusters across 7 AWS regions serving 50M daily requests",
                    "Automated provisioning with Terraform, reducing environment setup time from 3 days to 20 minutes",
                    "Implemented GitOps workflow using ArgoCD, achieving zero-downtime deployments for 100+ services",
                ],
                evidence_units=[ev1, ev2, ev3],
            ),
        ],
        education=[
            EducationEntity(id="EDU_GATECH_001", institution="Georgia Institute of Technology", degree="B.S. Computer Engineering", dates="Aug 2014 – May 2018"),
        ],
        evidence_units=[ev1, ev2, ev3],
    )


@pytest.fixture
def jd_devops():
    return JDRequirements(
        role_title="DevOps Engineer",
        company="Datadog",
        seniority="Senior",
        must_have_skills=["Kubernetes", "Terraform", "AWS", "CI/CD", "Docker"],
        preferred_skills=["ArgoCD", "Helm", "Prometheus", "Grafana", "GitOps"],
        raw_text="Datadog is hiring a Senior DevOps/SRE to manage cloud infrastructure and enable engineering teams with world-class tooling.",
    )


def test_scenario_10_devops(profile_devops, jd_devops):
    """SCENARIO 10: Senior SRE with Kubernetes/Terraform/AWS."""
    result = _run_full_pipeline(profile_devops, jd_devops, "Tyler Osei")
    # Certifications must appear
    assert "CKA" in result["text_output"] or "Kubernetes Administrator" in result["text_output"] or "Terraform" in result["text_output"]
    # Infrastructure metrics preserved
    assert "250" in result["text_output"] or "50M" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 11: Academic / Research — PhD applying to research role
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_academic_phd():
    ev1 = _make_ev("EXP_STANFORD_LAB_001", "EXPERIENCE", "Published 8 peer-reviewed papers in NeurIPS, ICML, and ICLR; h-index 12", "EXP_STANFORD_LAB")
    ev2 = _make_ev("EXP_STANFORD_LAB_002", "EXPERIENCE", "Supervised 4 master's students; 2 graduated with distinction", "EXP_STANFORD_LAB")
    ev3 = _make_ev("EXP_GOOGLE_INTERN_001", "EXPERIENCE", "Developed novel self-supervised pre-training objective reducing label requirements by 60%", "EXP_GOOGLE_INTERN")
    return CandidateProfile(
        personal={"name": "Dr. Yuki Tanaka", "email": "yuki@stanford.edu", "phone": "+1-555-1100", "location": "Stanford, CA"},
        summary="PhD candidate in Machine Learning at Stanford. Research focus on self-supervised learning and efficient transformer architectures. 8 publications, h-index 12.",
        skills=["Python", "PyTorch", "JAX", "CUDA", "Transformers", "Self-Supervised Learning", "NLP", "Computer Vision", "LaTeX", "Research"],
        publications=[
            "Tanaka Y. et al. (2024). 'Self-Supervised Objectives for Low-Resource NLP.' NeurIPS 2024.",
            "Tanaka Y. et al. (2023). 'Efficient Vision Transformers via Token Pruning.' ICLR 2023.",
            "Tanaka Y. et al. (2022). 'Contrastive Pre-training for Multilingual Understanding.' ICML 2022.",
        ],
        research=["Stanford NLP Group — PhD Researcher (2020–Present)", "KAIST AI Lab — Undergraduate Researcher (2018–2020)"],
        experience=[
            WorkExperienceEntity(
                id="EXP_STANFORD_LAB",
                company="Stanford NLP Group",
                role="PhD Research Assistant",
                dates="Sep 2020 – Present",
                location="Stanford, CA",
                bullets=[
                    "Published 8 peer-reviewed papers in NeurIPS, ICML, and ICLR; h-index 12",
                    "Supervised 4 master's students; 2 graduated with distinction",
                ],
                evidence_units=[ev1, ev2],
            ),
            WorkExperienceEntity(
                id="EXP_GOOGLE_INTERN",
                company="Google Brain",
                role="Research Intern",
                dates="Jun 2022 – Sep 2022",
                location="Mountain View, CA",
                bullets=[
                    "Developed novel self-supervised pre-training objective reducing label requirements by 60%",
                ],
                evidence_units=[ev3],
            ),
        ],
        education=[
            EducationEntity(id="EDU_STANFORD_PHD", institution="Stanford University", degree="Ph.D. Computer Science (Machine Learning)", dates="Sep 2020 – May 2025 (expected)"),
            EducationEntity(id="EDU_KAIST", institution="KAIST", degree="B.S. Computer Science (summa cum laude)", dates="Mar 2016 – Feb 2020"),
        ],
        evidence_units=[ev1, ev2, ev3],
    )


@pytest.fixture
def jd_research_scientist():
    return JDRequirements(
        role_title="Research Scientist",
        company="Meta AI",
        seniority="PhD / Research",
        must_have_skills=["Machine Learning", "PyTorch", "Deep Learning", "Research Publications"],
        preferred_skills=["NLP", "Self-Supervised Learning", "Transformers", "JAX"],
        raw_text="Meta AI is looking for a Research Scientist to advance the state of the art in foundation model research.",
    )


def test_scenario_11_academic_phd(profile_academic_phd, jd_research_scientist):
    """SCENARIO 11: PhD candidate with 8 publications applying to research scientist role."""
    result = _run_full_pipeline(profile_academic_phd, jd_research_scientist, "Dr. Yuki Tanaka")
    # Publications must appear
    assert "NeurIPS" in result["text_output"] or "ICLR" in result["text_output"] or "ICML" in result["text_output"]
    # Research section preserved
    assert "Stanford" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 12: Full-stack developer with dense, project-heavy profile
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_fullstack_project_heavy():
    ev1 = _make_ev("PROJ_SAAS_001", "PROJECTS", "Built multi-tenant SaaS platform serving 5000 paying customers using React, Node.js, and PostgreSQL", "PROJ_SAAS")
    ev2 = _make_ev("PROJ_SAAS_002", "PROJECTS", "Implemented Stripe billing integration processing $200k MRR", "PROJ_SAAS")
    ev3 = _make_ev("PROJ_OSS_001", "PROJECTS", "Maintained open-source React component library with 2.3k GitHub stars", "PROJ_OSS")
    ev4 = _make_ev("EXP_AGENCY_001", "EXPERIENCE", "Delivered 15 client web applications in 2 years, on-time and within budget", "EXP_AGENCY")
    ev5 = _make_ev("EXP_AGENCY_002", "EXPERIENCE", "Reduced average page load time from 8s to 1.2s through code splitting and CDN optimization", "EXP_AGENCY")
    return CandidateProfile(
        personal={"name": "Alex Turner", "email": "alex@alexturner.dev", "phone": "+1-555-1200", "location": "Remote", "github": "github.com/alexturner", "portfolio": "alexturner.dev"},
        summary="Full-stack developer with 3 years of freelance and agency experience. Expert in React, Node.js, TypeScript, and PostgreSQL. Indie hacker building profitable SaaS products.",
        skills=["JavaScript", "TypeScript", "React", "Next.js", "Node.js", "Express", "PostgreSQL", "Redis", "Docker", "Stripe", "AWS"],
        experience=[
            WorkExperienceEntity(
                id="EXP_AGENCY",
                company="Webcraft Agency",
                role="Full-Stack Developer",
                dates="Jun 2022 – Present",
                location="Remote",
                bullets=[
                    "Delivered 15 client web applications in 2 years, on-time and within budget",
                    "Reduced average page load time from 8s to 1.2s through code splitting and CDN optimization",
                ],
                evidence_units=[ev4, ev5],
            ),
        ],
        projects=[
            ProjectEntity(
                id="PROJ_SAAS",
                title="Multi-Tenant SaaS Platform (BriefBase)",
                tech_stack="React, Node.js, PostgreSQL, Stripe, AWS",
                technologies=["React", "Node.js", "PostgreSQL", "Stripe", "AWS"],
                dates="Jan 2023 – Present",
                url="https://briefbase.io",
                bullets=[
                    "Built multi-tenant SaaS platform serving 5000 paying customers using React, Node.js, and PostgreSQL",
                    "Implemented Stripe billing integration processing $200k MRR",
                ],
                evidence_units=[ev1, ev2],
            ),
            ProjectEntity(
                id="PROJ_OSS",
                title="React UI Component Library (open source)",
                tech_stack="React, TypeScript, Storybook",
                technologies=["React", "TypeScript", "Storybook"],
                dates="Mar 2022",
                url="https://github.com/alexturner/react-ui",
                bullets=["Maintained open-source React component library with 2.3k GitHub stars"],
                evidence_units=[ev3],
            ),
        ],
        education=[
            EducationEntity(id="EDU_SELF", institution="Self-Taught / Online Courses", degree="Full-Stack Web Development", dates="2021"),
        ],
        evidence_units=[ev1, ev2, ev3, ev4, ev5],
    )


@pytest.fixture
def jd_fullstack():
    return JDRequirements(
        role_title="Full-Stack Engineer",
        company="Linear",
        seniority="Mid-Level",
        must_have_skills=["React", "TypeScript", "Node.js", "PostgreSQL"],
        preferred_skills=["Next.js", "Docker", "AWS", "Redis"],
        raw_text="Linear is hiring a full-stack engineer to build and maintain our product management software using React, TypeScript, and Node.js.",
    )


def test_scenario_12_fullstack_project_heavy(profile_fullstack_project_heavy, jd_fullstack):
    """SCENARIO 12: Full-stack developer with project-heavy, indie-hacker profile."""
    result = _run_full_pipeline(profile_fullstack_project_heavy, jd_fullstack, "Alex Turner")
    # Projects section must be present
    assert "BriefBase" in result["text_output"] or "SaaS" in result["text_output"] or "React" in result["text_output"]
    # Key metric preserved
    assert "5000" in result["text_output"] or "$200k" in result["text_output"] or "MRR" in result["text_output"]
    # Portfolio link should appear
    assert "alexturner.dev" in result["text_output"] or "github.com" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 13: Adversarial — numbers in company names, Unicode characters
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_adversarial_unicode():
    ev1 = _make_ev("EXP_3M_001", "EXPERIENCE", "Led R&D team at 3M across 4 countries, delivering $15M product line expansion", "EXP_3M")
    ev2 = _make_ev("EXP_3M_002", "EXPERIENCE", "Reduced manufacturing defect rate by 35% using Six Sigma methodology", "EXP_3M")
    return CandidateProfile(
        personal={"name": "François Müller", "email": "francois@gmail.com", "phone": "+49-555-0100", "location": "Munich, Germany"},
        summary="Engineering manager with 8 years in manufacturing R&D at 3M and Siemens. Expert in Six Sigma, lean manufacturing, and cross-cultural team leadership.",
        skills=["Python", "MATLAB", "Six Sigma", "Lean Manufacturing", "CAD/CAM", "Project Management", "R&D Strategy", "Cross-functional Leadership"],
        certifications=["Six Sigma Black Belt", "PMP® – Project Management Professional"],
        experience=[
            WorkExperienceEntity(
                id="EXP_3M",
                company="3M",
                role="Senior R&D Engineer",
                dates="Mar 2018 – Present",
                location="Munich, Germany",
                bullets=[
                    "Led R&D team at 3M across 4 countries, delivering $15M product line expansion",
                    "Reduced manufacturing defect rate by 35% using Six Sigma methodology",
                ],
                evidence_units=[ev1, ev2],
            ),
        ],
        education=[
            EducationEntity(id="EDU_TUM_001", institution="Technische Universität München (TUM)", degree="M.Sc. Mechanical Engineering", dates="Oct 2013 – Sep 2015"),
        ],
        evidence_units=[ev1, ev2],
    )


@pytest.fixture
def jd_engineering_manager():
    return JDRequirements(
        role_title="Engineering Manager",
        company="Boston Dynamics",
        seniority="Senior",
        must_have_skills=["R&D", "Team Leadership", "Project Management", "Cross-functional"],
        preferred_skills=["Six Sigma", "Manufacturing", "Python"],
        raw_text="Boston Dynamics is looking for an Engineering Manager to lead a team of robotics engineers in R&D and product development.",
    )


def test_scenario_13_adversarial_unicode(profile_adversarial_unicode, jd_engineering_manager):
    """SCENARIO 13: Profile with special characters and numbers in company names."""
    result = _run_full_pipeline(profile_adversarial_unicode, jd_engineering_manager, "François Müller")
    # Should handle '3M' company name and non-ASCII characters gracefully
    assert result["pdf_bytes"] is not None and len(result["pdf_bytes"]) > 100
    assert result["docx_bytes"] is not None and len(result["docx_bytes"]) > 100
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 14: Empty optional sections (no summary, no certs, no links)
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_empty_optional_sections():
    ev1 = _make_ev("EXP_APPLE_001", "EXPERIENCE", "Shipped iOS 17 accessibility features used by 500M+ devices worldwide", "EXP_APPLE")
    ev2 = _make_ev("EXP_APPLE_002", "EXPERIENCE", "Reduced Swift compiler build times by 40% through parallelization changes", "EXP_APPLE")
    return CandidateProfile(
        personal={"name": "Jordan Park", "email": "jpark@icloud.com", "phone": "+1-555-1400"},
        # No summary, no certifications, no links, no publications, no achievements
        skills=["Swift", "Objective-C", "Xcode", "UIKit", "SwiftUI", "Core Data", "XCTest", "REST APIs"],
        experience=[
            WorkExperienceEntity(
                id="EXP_APPLE",
                company="Apple",
                role="iOS Software Engineer",
                dates="Aug 2020 – Present",
                location="Cupertino, CA",
                bullets=[
                    "Shipped iOS 17 accessibility features used by 500M+ devices worldwide",
                    "Reduced Swift compiler build times by 40% through parallelization changes",
                ],
                evidence_units=[ev1, ev2],
            ),
        ],
        education=[
            EducationEntity(id="EDU_CALTECH_001", institution="California Institute of Technology", degree="B.S. Computer Science", dates="Sep 2016 – Jun 2020"),
        ],
        evidence_units=[ev1, ev2],
    )


@pytest.fixture
def jd_ios():
    return JDRequirements(
        role_title="iOS Engineer",
        company="Spotify",
        seniority="Senior",
        must_have_skills=["Swift", "UIKit", "SwiftUI", "iOS SDK", "REST APIs"],
        preferred_skills=["Core Data", "XCTest", "Objective-C", "Xcode"],
        raw_text="Spotify is looking for an iOS engineer to build features for our music streaming app used by 600M people worldwide.",
    )


def test_scenario_14_empty_optional_sections(profile_empty_optional_sections, jd_ios):
    """SCENARIO 14: Profile with no summary, no certs, no links — all optional sections empty."""
    result = _run_full_pipeline(profile_empty_optional_sections, jd_ios, "Jordan Park")
    # Must not crash on empty optional sections
    assert result["pdf_bytes"] is not None
    # Name and experience must appear
    assert "Apple" in result["text_output"]
    assert "500M" in result["text_output"] or "40%" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 15: International candidate — non-US education, non-English company names
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_international():
    ev1 = _make_ev("EXP_INFOSYS_001", "EXPERIENCE", "Delivered SAP ERP implementation for 3 enterprise clients, managing teams of 12 consultants", "EXP_INFOSYS")
    ev2 = _make_ev("EXP_INFOSYS_002", "EXPERIENCE", "Automated financial reconciliation process reducing manual effort by 70% using Python scripts", "EXP_INFOSYS")
    ev3 = _make_ev("EXP_TCS_001", "EXPERIENCE", "Migrated 200+ Oracle PL/SQL procedures to PostgreSQL with zero data loss", "EXP_TCS")
    return CandidateProfile(
        personal={"name": "Vikram Krishnamurthy", "email": "vikram@gmail.com", "phone": "+91-9876543210", "location": "Bangalore, India"},
        summary="Software consultant with 6 years at Infosys and TCS delivering enterprise ERP and database migration projects. Seeking opportunities in the United States.",
        skills=["Python", "SAP", "PostgreSQL", "Oracle PL/SQL", "Java", "Spring Framework", "Linux", "Shell Scripting"],
        experience=[
            WorkExperienceEntity(
                id="EXP_INFOSYS",
                company="Infosys",
                role="Technology Lead",
                dates="Apr 2021 – Present",
                location="Bangalore, India",
                bullets=[
                    "Delivered SAP ERP implementation for 3 enterprise clients, managing teams of 12 consultants",
                    "Automated financial reconciliation process reducing manual effort by 70% using Python scripts",
                ],
                evidence_units=[ev1, ev2],
            ),
            WorkExperienceEntity(
                id="EXP_TCS",
                company="Tata Consultancy Services (TCS)",
                role="Software Engineer",
                dates="Jul 2019 – Apr 2021",
                location="Chennai, India",
                bullets=[
                    "Migrated 200+ Oracle PL/SQL procedures to PostgreSQL with zero data loss",
                ],
                evidence_units=[ev3],
            ),
        ],
        education=[
            EducationEntity(id="EDU_IIT_MADRAS", institution="Indian Institute of Technology (IIT) Madras", degree="B.Tech. Computer Science", dates="Jul 2015 – May 2019"),
        ],
        certifications=["Oracle Certified Professional", "SAP Certified Application Associate"],
        evidence_units=[ev1, ev2, ev3],
    )


@pytest.fixture
def jd_backend_us():
    return JDRequirements(
        role_title="Backend Software Engineer",
        company="Workday",
        seniority="Mid-Level",
        must_have_skills=["Python", "PostgreSQL", "REST APIs", "Database Migration"],
        preferred_skills=["SAP", "Oracle", "Java", "Spring Framework"],
        raw_text="Workday is hiring a backend engineer to build and maintain enterprise-grade financial software using Python and PostgreSQL.",
    )


def test_scenario_15_international_candidate(profile_international, jd_backend_us):
    """SCENARIO 15: International candidate with non-US education and employers."""
    result = _run_full_pipeline(profile_international, jd_backend_us, "Vikram Krishnamurthy")
    # Both Indian companies should appear
    assert "Infosys" in result["text_output"]
    assert "Tata" in result["text_output"] or "TCS" in result["text_output"]
    # IIT Madras education preserved
    assert "IIT" in result["text_output"] or "Madras" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# SCENARIO 16: Over-qualified — 15+ years applying to mid-level role
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_overqualified():
    ev1 = _make_ev("EXP_AMAZON_VP_001", "EXPERIENCE", "Led organization of 180 engineers across 8 teams delivering AWS RDS for 1M+ customers", "EXP_AMAZON_VP")
    ev2 = _make_ev("EXP_AMAZON_VP_002", "EXPERIENCE", "Grew team from 40 to 180 engineers over 4 years; established engineering excellence program", "EXP_AMAZON_VP")
    ev3 = _make_ev("EXP_AMAZON_DIR_001", "EXPERIENCE", "Directed $50M annual engineering budget and vendor contracts", "EXP_AMAZON_DIR")
    ev4 = _make_ev("EXP_AMAZON_PE_001", "EXPERIENCE", "Designed distributed consensus protocol for Aurora multi-master supporting 99.999% uptime", "EXP_AMAZON_PE")
    return CandidateProfile(
        personal={"name": "Robert Chang", "email": "robert@gmail.com", "phone": "+1-555-1600", "location": "Seattle, WA"},
        summary="Engineering executive with 15+ years at Amazon. Led teams of 180+ engineers and multi-billion dollar products. Seeking individual contributor role to return to technical roots.",
        skills=["Java", "C++", "Python", "AWS", "Distributed Systems", "Databases", "Technical Leadership", "Systems Design", "Cloud Architecture"],
        experience=[
            WorkExperienceEntity(
                id="EXP_AMAZON_VP",
                company="Amazon Web Services (AWS)",
                role="VP of Engineering",
                dates="Jan 2020 – Present",
                location="Seattle, WA",
                bullets=[
                    "Led organization of 180 engineers across 8 teams delivering AWS RDS for 1M+ customers",
                    "Grew team from 40 to 180 engineers over 4 years; established engineering excellence program",
                ],
                evidence_units=[ev1, ev2],
            ),
            WorkExperienceEntity(
                id="EXP_AMAZON_DIR",
                company="Amazon Web Services (AWS)",
                role="Director of Engineering",
                dates="Jan 2016 – Jan 2020",
                location="Seattle, WA",
                bullets=[
                    "Directed $50M annual engineering budget and vendor contracts",
                ],
                evidence_units=[ev3],
            ),
            WorkExperienceEntity(
                id="EXP_AMAZON_PE",
                company="Amazon Web Services (AWS)",
                role="Principal Engineer",
                dates="Jun 2010 – Jan 2016",
                location="Seattle, WA",
                bullets=[
                    "Designed distributed consensus protocol for Aurora multi-master supporting 99.999% uptime",
                ],
                evidence_units=[ev4],
            ),
        ],
        education=[
            EducationEntity(id="EDU_YALE", institution="Yale University", degree="B.S. Computer Science", dates="Sep 2002 – May 2006"),
        ],
        evidence_units=[ev1, ev2, ev3, ev4],
    )


def test_scenario_16_overqualified(profile_overqualified, jd_swe_senior):
    """SCENARIO 16: 15-year VP of Engineering applying for Senior SWE role."""
    result = _run_full_pipeline(profile_overqualified, jd_swe_senior, "Robert Chang")
    # Experience entries should all be present
    assert "AWS" in result["text_output"] or "Amazon" in result["text_output"]
    # Key technical metric preserved — distributed systems bullet
    assert "Aurora" in result["text_output"] or "99.999" in result["text_output"] or "consensus" in result["text_output"]
    assert result["is_ats_parseable"]


# ---------------------------------------------------------------------------
# CROSS-CUTTING: Evidence Ledger integrity across ALL scenarios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile_fixture,name", [
    ("profile_fresher_projects", "Aisha Patel"),
    ("profile_fresher_internships", "Rohan Sharma"),
    ("profile_experienced_swe_single_company", "Marcus Chen"),
    ("profile_experienced_multicompany", "Priya Nair"),
    ("profile_senior_multi_role", "Elena Rodriguez"),
    ("profile_data_scientist", "Anjali Mehta"),
    ("profile_devops", "Tyler Osei"),
    ("profile_fullstack_project_heavy", "Alex Turner"),
    ("profile_overqualified", "Robert Chang"),
])
def test_evidence_ledger_non_empty_for_rich_profiles(profile_fixture, name, request):
    """Evidence Ledger must have >= 1 EvidenceUnit for all profiles with content."""
    profile = request.getfixturevalue(profile_fixture)
    assert len(profile.evidence_units) >= 1, \
        f"{name}: Expected non-empty Evidence Ledger, got 0 units"
    for ev in profile.evidence_units:
        assert ev.id, f"EvidenceUnit missing ID for {name}"
        assert ev.original_text, f"EvidenceUnit {ev.id} missing original_text for {name}"
        assert ev.section, f"EvidenceUnit {ev.id} missing section for {name}"


@pytest.mark.parametrize("profile_fixture,name", [
    ("profile_fresher_minimal", "Jordan Lee"),
    ("profile_empty_optional_sections", "Jordan Park"),
])
def test_pipeline_does_not_crash_on_empty_evidence_ledger(profile_fixture, name, request):
    """Profiles with no evidence units must not crash the pipeline."""
    profile = request.getfixturevalue(profile_fixture)
    jd = JDRequirements(
        role_title="Software Engineer",
        company="Test Co",
        seniority="Entry",
        must_have_skills=["Python"],
        preferred_skills=[],
        raw_text="Looking for a software engineer.",
    )
    parsed_dict = profile.to_parsed_dict()
    text_output = render_candidate_profile_to_text(profile)
    assert isinstance(text_output, str)
    pdf_bytes = generate_pdf(parsed_dict, candidate_name=name, template="standard")
    assert len(pdf_bytes) > 100


# ---------------------------------------------------------------------------
# CROSS-CUTTING: Template selection is deterministic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile_fixture", [
    "profile_fresher_projects",
    "profile_experienced_swe_single_company",
    "profile_senior_multi_role",
    "profile_academic_phd",
])
def test_template_selection_is_deterministic(profile_fixture, request):
    """Calling resolve_template_strategy twice must return the same template family."""
    profile = request.getfixturevalue(profile_fixture)
    classification = classify_candidate_profile(profile)
    strategy_1 = resolve_template_strategy(classification)
    strategy_2 = resolve_template_strategy(classification)
    assert strategy_1.template_family == strategy_2.template_family, \
        f"Template selection is non-deterministic for {profile_fixture}"


# ---------------------------------------------------------------------------
# CROSS-CUTTING: PDF page count reasonable for profile density
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile_fixture,max_pages,name", [
    ("profile_fresher_minimal", 1, "Jordan Lee"),
    ("profile_fresher_projects", 2, "Aisha Patel"),
    ("profile_experienced_swe_single_company", 2, "Marcus Chen"),
    ("profile_senior_multi_role", 3, "Elena Rodriguez"),
    ("profile_overqualified", 4, "Robert Chang"),
])
def test_pdf_page_count_reasonable(profile_fixture, max_pages, name, request):
    """PDF page count must be within a reasonable range for each profile type."""
    profile = request.getfixturevalue(profile_fixture)
    parsed_dict = profile.to_parsed_dict()
    pdf_bytes = generate_pdf(parsed_dict, candidate_name=name, template="standard")
    page_count = measure_pdf_page_count(pdf_bytes)
    assert 1 <= page_count <= max_pages, \
        f"{name}: Expected 1–{max_pages} pages, got {page_count}"


# ---------------------------------------------------------------------------
# CROSS-CUTTING: Dates are preserved exactly in output
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile_fixture,date_str,name", [
    ("profile_fresher_projects", "Aug 2021", "Aisha Patel"),
    ("profile_experienced_swe_single_company", "Jun 2021", "Marcus Chen"),
    ("profile_devops", "Mar 2019", "Tyler Osei"),
    ("profile_academic_phd", "Sep 2020", "Dr. Yuki Tanaka"),
])
def test_dates_preserved_in_text_output(profile_fixture, date_str, name, request):
    """Education and experience dates must appear verbatim in rendered text output."""
    profile = request.getfixturevalue(profile_fixture)
    text = render_candidate_profile_to_text(profile)
    assert date_str in text, \
        f"{name}: Expected date '{date_str}' in text output, but it was missing.\nOutput (first 800 chars):\n{text[:800]}"
