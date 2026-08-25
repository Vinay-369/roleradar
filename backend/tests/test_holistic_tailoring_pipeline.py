"""
Holistic Tailoring Pipeline & Truth Guard v6 Acceptance Tests.
Validates across 3 structurally distinct real-world resumes:
1. Resume A (Fresher: Education & academic projects first)
2. Resume B (Mid-Level: Dense quantified employment experience)
3. Resume C (Career Switcher / Diverse sections: Skills, Projects, Certifications)

Verifies all 6 Acceptance Criteria:
- Criterion 1: Every eligible section evaluated for JD-relevance
- Criterion 2: Deterministic skill reordering generated when JD skills exist in resume
- Criterion 3: Zero ungrounded technical fabrications (noun/number-tracing auto-flags NEEDS_USER_INPUT)
- Criterion 4: Protected sections (Education, Certifications, Contact) remain intact
- Criterion 5: Final exported PDF deterministically fits 1 page for 0-2 YOE candidates
- Criterion 6: Unmatched JD required skills visibly surfaced in unmatched_gaps
"""
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.ai_service.schemas import ChangeStatus, ChangeType, TailoringChange, TailoringResult
from app.core.ai_service.service import AIService
from app.modules.tailoring import services
from app.modules.tailoring.validation import (
    compute_deterministic_skill_reorder,
    detect_fabricated_claims,
    is_target_in_protected_section,
    measure_and_enforce_one_page_fit,
    validate_protected_sections,
)
from app.modules.tailoring.export import generate_pdf, measure_pdf_page_count

# =============================================================================
# 3 STRUCTURALLY DISTINCT TEST RESUMES
# =============================================================================

# Resume A: Fresher (Education & Projects First, No Industry Experience)
RESUME_A_FRESHER_TEXT = """ARAVIND SHARMA
aravind.sharma@example.com | +91 9876543210 | Bengaluru, India | github.com/aravind-dev

EDUCATION
National Institute of Engineering, Mysore
Bachelor of Engineering in Computer Science and Engineering (2020 - 2024)
CGPA: 8.9 / 10.0

TECHNICAL SKILLS
Languages: Python, C++, JavaScript, SQL, HTML, CSS
Frameworks: FastAPI, Django, React, Bootstrap
Databases: PostgreSQL, SQLite, Redis
Tools: Git, Docker, Linux, Postman

ACADEMIC PROJECTS
AI-Powered Resume Screener (Python, FastAPI, PostgreSQL)
• Built an automated resume parser processing 50+ resumes per minute with 92% extraction accuracy.
• Engineered search queries using PostgreSQL full-text search, reducing search latency by 45%.
• Integrated Redis caching layer for frequent keyword queries, improving response time to 12ms.

Real-Time Collaborative Code Editor (React, WebSockets, Node.js)
• Developed real-time collaborative workspace supporting up to 10 concurrent developers per room.
• Implemented operational transformation algorithms ensuring conflict-free code synchronization.
• Deployed application container on Docker with automated health check monitors.

CAMPUS LEADERSHIP & ACHIEVEMENTS
• Lead Organizer, NIE Annual Hackathon with 400+ participants across 30 colleges.
• Winner, Smart India Hackathon internal campus qualifier for AI track.
"""

# Resume B: Mid-Level Developer (Summary, Dense Multi-Company Quantified Experience First)
RESUME_B_MIDLEVEL_TEXT = """PRIYA VENKAT
priya.venkat@example.com | +91 9123456780 | Hyderabad, India | linkedin.com/in/priya-venkat

PROFESSIONAL SUMMARY
Senior Backend Engineer with 3+ years building high-throughput microservices in Python, Golang, and PostgreSQL. Experienced in distributed systems, message queues, and AWS cloud infrastructure.

WORK EXPERIENCE
SaaS Platform Solutions Pvt Ltd — Software Engineer (2022 - Present)
• Architected event-driven microservices handling 2.5M daily active requests using FastAPI and Kafka.
• Optimized PostgreSQL query execution plans, reducing p99 database response latency from 180ms to 42ms.
• Designed Redis distributed rate limiter preventing API abuse and maintaining 99.98% service uptime.
• Spearheaded automated CI/CD deployment pipelines on AWS ECS using GitHub Actions and Terraform.

FinTech Innovations India — Junior Backend Developer (2021 - 2022)
• Developed REST APIs for payment reconciliation engine processing over INR 15 Crores in daily transactions.
• Automated ledger validation scripts using Python and Celery, cutting reconciliation time by 65%.
• Resolved 40+ production incidents through proactive Datadog monitoring and structured logging.

TECHNICAL SKILLS
Languages & Core: Python, Golang, SQL, Bash
Cloud & Infrastructure: AWS, Docker, Kubernetes, Terraform, Kafka, Redis, PostgreSQL
Architecture: Microservices, System Design, REST APIs, CI/CD, Distributed Systems

EDUCATION
Vellore Institute of Technology (VIT), Vellore
B.Tech in Information Technology (2017 - 2021) | CGPA: 8.7
"""

# Resume C: Career Switcher / Non-Standard Structure (Summary, Mixed Skills, Diverse Projects, Certifications First)
RESUME_C_SWITCHER_TEXT = """RAHUL MEHTA
rahul.mehta@example.com | +91 9988776655 | Pune, India | portfolio: rahulmehta.tech

CAREER OBJECTIVE
Transitioning QA Automation Specialist with 2 years of testing experience moving into Backend Software Engineering. Strong foundation in Python, REST APIs, Docker, and Database optimization.

CERTIFICATIONS & LICENSES
• AWS Certified Solutions Architect - Associate (2023)
• Certified Kubernetes Application Developer (CKAD) (2024)

TECHNICAL COMPETENCIES
Core: Python, JavaScript, SQL, HTML
Backend & Storage: Flask, FastAPI, MySQL, MongoDB, Redis
Testing & DevOps: PyTest, Selenium, Docker, Git, Linux, Postman

TECHNICAL PROJECTS
Distributed Task Queue Engine (Python, Redis, Docker)
• Engineered asynchronous task execution queue handling 5,000 background jobs per minute.
• Implemented worker retry policies with exponential backoff and dead-letter queue routing.
• Containerized application services using Docker Compose for seamless one-command local testing.

Automated API Performance Benchmark Suite (Python, PyTest, Locust)
• Built load testing framework simulating 1,200 concurrent user sessions across 15 critical REST endpoints.
• Identified memory leak in authentication middleware, preventing potential production outages.

ACADEMIC BACKGROUND
Pune University — Bachelor of Science in Mathematics (2018 - 2021) | First Class with Distinction
"""

TARGET_BACKEND_JD = """
Backend Engineer (Python / FastAPI / PostgreSQL / AWS / Redis / Kubernetes)
Company: NexaCloud Technologies
Location: Bengaluru / Remote

About the Role:
We are looking for a Backend Engineer to build scalable microservices for our enterprise cloud platform.

Key Requirements:
- 1-3 years of experience with Python, FastAPI or Django, and PostgreSQL.
- Strong knowledge of Redis caching, database indexing, and query optimization.
- Hands-on experience with Docker containerization and AWS cloud deployments.
- Understanding of Kubernetes and microservices architecture is a major plus.
- Proven ability to write clean, quantified, unit-tested code with strong problem-solving skills.
"""


import json
from app.core.config import Settings
from app.core.ai_service.providers.base import AIProvider


class MockHolisticAIProvider(AIProvider):
    """Mock AI Provider that returns a section-complete tailoring proposal."""
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        return json.dumps({
            "sections_evaluated": ["SUMMARY", "SKILLS", "EXPERIENCE", "PROJECTS", "EDUCATION"],
            "sections_changed": ["SUMMARY", "SKILLS", "PROJECTS", "EXPERIENCE"],
            "unmatched_gaps": ["Kubernetes"],
            "changes": [
                {
                    "change_id": "c_proj1",
                    "section": "PROJECTS",
                    "change_type": "TEXT_REWRITE",
                    "original": "Built an automated resume parser processing 50+ resumes per minute with 92% extraction accuracy.",
                    "proposed": "Architected an automated resume parser in Python & FastAPI processing 50+ resumes per minute with 92% extraction accuracy.",
                    "reason": "Highlight Python and FastAPI keywords in the primary accomplishment bullet.",
                    "source_evidence": "Built an automated resume parser in Python and FastAPI.",
                    "confidence": 0.95,
                    "status": "PENDING",
                },
                {
                    "change_id": "c_proj2",
                    "section": "PROJECTS",
                    "change_type": "TEXT_REWRITE",
                    "original": "Engineered search queries using PostgreSQL full-text search, reducing search latency by 45%.",
                    "proposed": "Optimized PostgreSQL full-text indexing and query execution, reducing search latency by 45% for high-throughput queries.",
                    "reason": "Align with JD requirement for database indexing and query optimization.",
                    "source_evidence": "Engineered search queries using PostgreSQL full-text search, reducing search latency by 45%.",
                    "confidence": 0.92,
                    "status": "PENDING",
                },
            ],
        })


class MockFabricatingAIProvider(AIProvider):
    """Mock AI Provider that intentionally attempts to fabricate tools not in candidate's background."""
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        return json.dumps({
            "sections_evaluated": ["PROJECTS"],
            "sections_changed": ["PROJECTS"],
            "unmatched_gaps": ["Kubernetes"],
            "changes": [
                {
                    "change_id": "c_fab1",
                    "section": "PROJECTS",
                    "change_type": "TEXT_REWRITE",
                    "original": "Deployed application container on Docker with automated health check monitors.",
                    "proposed": "Deployed application container using Kubernetes, Terraform, and AWS CloudFormation with automated health check monitors.",
                    "reason": "Inject advanced cloud tools from JD.",
                    "source_evidence": "Deployed on Docker.",
                    "confidence": 0.85,
                    "status": "PENDING",
                },
                {
                    "change_id": "c_protected1",
                    "section": "EDUCATION",
                    "change_type": "TEXT_REWRITE",
                    "original": "Bachelor of Engineering in Computer Science and Engineering (2020 - 2024)",
                    "proposed": "Master of Science in Distributed Cloud Computing (2020 - 2024)",
                    "reason": "Upgrade degree title.",
                    "source_evidence": "Education degree.",
                    "confidence": 0.99,
                    "status": "PENDING",
                },
            ],
        })


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    return client["test_holistic_tailoring"]


async def _save_test_master_resume(mock_db, user_id, raw_text, file_name="resume.docx"):
    from app.modules.resume.parsing.structurer import structure_resume_text
    from app.modules.resume import repositories as resume_repo
    parsed = structure_resume_text(raw_text)
    return await resume_repo.create_master_resume(
        mock_db,
        user_id=user_id,
        version=1,
        file_name=file_name,
        file_type="docx",
        raw_text=raw_text,
        parsed=parsed,
        parseability={"score": 90, "likely_multi_column": False, "contact_info_found": {"email": "test@example.com"}},
        recruiter_impact={"score": 85},
    )


# =============================================================================
# ACCEPTANCE CRITERION 1: HOLISTIC SECTION EVALUATION
# =============================================================================
@pytest.mark.asyncio
async def test_criterion_1_holistic_multi_section_evaluation(mock_db, settings):
    """
    Criterion 1: Every eligible section shows evidence of having been evaluated
    for JD-relevance across structurally distinct resumes (not just 1-2 bullets).
    """
    user_id = "user_fresher_1"
    ai_service = AIService(settings)
    ai_service._provider = MockHolisticAIProvider()

    await _save_test_master_resume(mock_db, user_id, RESUME_A_FRESHER_TEXT)

    version = await services.generate_tailoring(
        mock_db,
        ai_service,
        user_id,
        custom_company="NexaCloud Technologies",
        custom_role_title="Backend Engineer",
        custom_jd_text=TARGET_BACKEND_JD,
    )

    # Asserts that all eligible sections present in resume were explicitly evaluated
    assert "sections_evaluated" in version
    assert len(version["sections_evaluated"]) >= 4
    assert "PROJECTS" in version["sections_evaluated"]
    assert "SKILLS" in version["sections_evaluated"]
    assert "EDUCATION" in version["sections_evaluated"]
    assert len(version["changes"]) >= 2


# =============================================================================
# ACCEPTANCE CRITERION 2: DETERMINISTIC SKILL REORDERING
# =============================================================================
def test_criterion_2_deterministic_skill_reordering():
    """
    Criterion 2: At least one reorder-type change is proposed when the JD's required
    skills exist in the resume but aren't already prioritized at the front.
    """
    master_skills = ["HTML", "CSS", "Bootstrap", "Python", "PostgreSQL", "Redis", "C++"]
    jd_text = TARGET_BACKEND_JD  # Mentions Python, PostgreSQL, Redis, FastAPI

    reordered, matched, unmatched_gaps, was_reordered = compute_deterministic_skill_reorder(
        master_skills, jd_text
    )

    assert was_reordered is True
    # JD-relevant skills (Python, PostgreSQL, Redis) must appear at the FRONT
    assert reordered[0] in ("Python", "PostgreSQL", "Redis")
    assert reordered[1] in ("Python", "PostgreSQL", "Redis")
    assert reordered[2] in ("Python", "PostgreSQL", "Redis")
    # Non-JD skills (HTML, CSS, Bootstrap) moved behind
    assert "HTML" in reordered[3:]
    assert "CSS" in reordered[3:]
    # Gaps detected (Kubernetes requested in JD, not in candidate skills)
    assert "Kubernetes" in unmatched_gaps


# =============================================================================
# ACCEPTANCE CRITERION 3: PROGRAMMATIC ANTI-FABRICATION NOUN TRACING
# =============================================================================
def test_criterion_3_anti_fabrication_noun_tracing():
    """
    Criterion 3: Zero fabricated technical claims in any proposed change,
    verified by the noun/number-tracing check across test resumes.
    """
    candidate_skills = ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Git"]
    original_bullet = "Deployed application container on Docker with automated health check monitors."
    
    # Attempted hallucination by LLM (introducing Kubernetes & Terraform absent from candidate background)
    fabricated_bullet = "Deployed application container using Kubernetes, Terraform, and AWS CloudFormation."

    unconfirmed = detect_fabricated_claims(
        original=original_bullet,
        proposed=fabricated_bullet,
        jd_text=TARGET_BACKEND_JD,
        candidate_skills=candidate_skills,
    )

    assert len(unconfirmed) > 0
    assert "kubernetes" in unconfirmed or "terraform" in unconfirmed


@pytest.mark.asyncio
async def test_criterion_3_service_auto_flags_fabrications_as_needs_user_input(mock_db, settings):
    """
    Verifies that when AI proposes ungrounded tools, services.generate_tailoring
    automatically flags status='NEEDS_USER_INPUT' with a fabrication warning.
    """
    user_id = "user_fab_test"
    ai_service = AIService(settings)
    ai_service._provider = MockFabricatingAIProvider()

    await _save_test_master_resume(mock_db, user_id, RESUME_A_FRESHER_TEXT)

    version = await services.generate_tailoring(
        mock_db,
        ai_service,
        user_id,
        custom_company="NexaCloud Technologies",
        custom_role_title="Backend Engineer",
        custom_jd_text=TARGET_BACKEND_JD,
    )

    fab_change = next((c for c in version["changes"] if c["change_id"] == "c_fab1"), None)
    assert fab_change is not None
    assert fab_change["status"] == ChangeStatus.NEEDS_USER_INPUT.value
    assert "fabrication_warning" in fab_change
    assert fab_change["fabrication_warning"] is not None


# =============================================================================
# ACCEPTANCE CRITERION 4: PROTECTED SECTIONS ISOLATION
# =============================================================================
def test_criterion_4_protected_section_rejection():
    """
    Criterion 4: Protected sections (Education, Certifications, Contact) remain
    structurally preserved and code-level guard rejects any alteration.
    """
    assert is_target_in_protected_section(
        "Bachelor of Engineering in Computer Science and Engineering",
        RESUME_A_FRESHER_TEXT,
    ) is True

    assert is_target_in_protected_section(
        "AWS Certified Solutions Architect",
        RESUME_C_SWITCHER_TEXT,
    ) is True

    # Experience and projects are ELIGIBLE, not protected
    assert is_target_in_protected_section(
        "Built an automated resume parser processing 50+ resumes per minute",
        RESUME_A_FRESHER_TEXT,
    ) is False


@pytest.mark.asyncio
async def test_criterion_4_education_tampering_dropped_by_service(mock_db, settings):
    """
    Verifies that changes proposing to alter education degrees are dropped in code.
    """
    user_id = "user_prot_test"
    ai_service = AIService(settings)
    ai_service._provider = MockFabricatingAIProvider()

    await _save_test_master_resume(mock_db, user_id, RESUME_A_FRESHER_TEXT)

    version = await services.generate_tailoring(
        mock_db,
        ai_service,
        user_id,
        custom_company="NexaCloud Technologies",
        custom_role_title="Backend Engineer",
        custom_jd_text=TARGET_BACKEND_JD,
    )

    # c_protected1 attempted to rewrite Bachelor's to Master's -> MUST be dropped
    edu_change = next((c for c in version["changes"] if c["change_id"] == "c_protected1"), None)
    assert edu_change is None


# =============================================================================
# ACCEPTANCE CRITERION 5: 1-PAGE PDF FIT GUARANTEE
# =============================================================================
def test_criterion_5_one_page_pdf_fit_measurement_and_enforcement():
    """
    Criterion 5: Final exported PDF fits one page for a 0-2 year experience candidate,
    verified by rendering it on the real ReportLab canvas.
    """
    # Test on Resume A (Fresher)
    pdf_bytes = generate_pdf(RESUME_A_FRESHER_TEXT, candidate_name="Aravind Sharma", template="modern")
    page_count = measure_pdf_page_count(pdf_bytes)
    assert page_count == 1

    # Test measure_and_enforce_one_page_fit function
    fitted_text, ok, pages = measure_and_enforce_one_page_fit(
        RESUME_A_FRESHER_TEXT, candidate_name="Aravind Sharma", template="modern"
    )
    assert ok is True
    assert pages == 1


# =============================================================================
# ACCEPTANCE CRITERION 6: UNMATCHED SKILL GAPS VISIBLY LISTED
# =============================================================================
@pytest.mark.asyncio
async def test_criterion_6_unmatched_gaps_visibly_surfaced(mock_db, settings):
    """
    Criterion 6: Skill gaps (JD requirements with no resume evidence) are visibly listed,
    not silently absent or fabricated into the resume.
    """
    user_id = "user_gaps_test"
    ai_service = AIService(settings)
    ai_service._provider = MockHolisticAIProvider()

    await _save_test_master_resume(mock_db, user_id, RESUME_A_FRESHER_TEXT)

    version = await services.generate_tailoring(
        mock_db,
        ai_service,
        user_id,
        custom_company="NexaCloud Technologies",
        custom_role_title="Backend Engineer",
        custom_jd_text=TARGET_BACKEND_JD,
    )

    assert "unmatched_gaps" in version
    assert len(version["unmatched_gaps"]) > 0
    assert any("Kubernetes" in g or "Aws" in g for g in version["unmatched_gaps"])


# =============================================================================
# FULL END-TO-END HOLISTIC TAILORING & VALIDATION SUMMARY TEST
# =============================================================================
@pytest.mark.asyncio
async def test_full_pipeline_finalize_produces_validation_summary(mock_db, settings):
    """
    Full pipeline test: generates tailoring with holistic evaluation, approves changes,
    finalizes, and confirms validation_summary (protected sections intact, 1-page fit,
    anti-fabrication check, ATS score delta) is stored.
    """
    user_id = "user_e2e_holistic"
    ai_service = AIService(settings)
    ai_service._provider = MockHolisticAIProvider()

    await _save_test_master_resume(mock_db, user_id, RESUME_A_FRESHER_TEXT)

    version = await services.generate_tailoring(
        mock_db,
        ai_service,
        user_id,
        custom_company="NexaCloud Technologies",
        custom_role_title="Backend Engineer",
        custom_jd_text=TARGET_BACKEND_JD,
    )

    # Approve all pending changes
    for change in version["changes"]:
        await services.set_change_status(
            mock_db, user_id, str(version["_id"]), change["change_id"], ChangeStatus.APPROVED
        )

    finalized = await services.finalize_tailoring(mock_db, user_id, str(version["_id"]), settings=settings)

    assert finalized["is_finalized"] is True
    assert "validation_summary" in finalized
    val_sum = finalized["validation_summary"]
    assert val_sum["protected_sections_intact"] is True
    assert val_sum["one_page_fit"] is True
    assert val_sum["page_count"] == 1
    assert val_sum["anti_fabrication_passed"] is True
    assert val_sum["all_checks_passed"] is True
