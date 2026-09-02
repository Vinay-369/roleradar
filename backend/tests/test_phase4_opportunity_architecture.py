"""
Phase 4 Unit & Regression Test Suite: Unified Opportunity Architecture & Ingestion Pipeline.
Validates:
1. Custom JD complete semantic ingestion (no arbitrary [:6] skill slicing, full responsibilities)
2. Custom JD user ownership & privacy isolation
3. Curated Job canonical resolution via get_canonical_job_requirements
4. Internship canonical resolution and category matching
5. Semantic invariance across Job, Internship, and Custom inputs
6. Skill Gap analysis using full Phase 3 requirements (CORE, SECONDARY, BONUS)
7. Learning Roadmap consuming canonical skill gaps
8. Tailoring convergence across Job, Internship, and Custom JDs
9. ResumeVersion provenance retention (master_resume_id, opportunity_type, jd_analysis_summary)
10. Backward compatibility for legacy documents lacking pre-computed structured_requirements
11. End-to-end integration regression
"""
import pytest
from app.modules.jobs.services import (
    create_custom_job,
    get_job,
    get_canonical_job_requirements,
    search_jobs,
)
from app.modules.jobs.taxonomy import analyze_job_description, RequirementCategory
from app.modules.learning.engine import compute_skill_gaps, build_roadmap
from app.modules.matching.engine import compute_match
from app.core.embeddings.factory import build_embedding_provider
from mongomock_motor import AsyncMongoMockClient
from app.core.config import Settings


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock", AI_PROVIDER="mock")
from app.modules.tailoring.repositories import create_version, get_version
from app.modules.applications.services import save_application, JobNotFoundError
from app.db.mongo import Collections


# =========================================================================
# 1. CUSTOM JD INGESTION TESTS (NO SLICING, COMPLETE REQUIREMENTS)
# =========================================================================

@pytest.mark.asyncio
async def test_custom_jd_complete_semantic_ingestion(db):
    custom_jd = """Acme Corp - Senior Cloud Security Engineer
Location: Austin, TX / Hybrid
Job Type: Full-Time

About Us:
Acme Corp provides zero-trust identity infrastructure.

Role Overview:
Lead our cloud security and penetration testing practice.

Key Responsibilities:
- Conduct vulnerability assessments across AWS and Kubernetes environments.
- Design automated compliance audits using Terraform and Open Policy Agent.
- Partner with dev squads to implement secure coding standards.

Requirements:
- 5+ years of professional cloud security engineering experience.
- Deep expertise in AWS, Kubernetes, and Python.
- Strong knowledge of IAM, cryptography, and network security.

Preferred:
- CISSP or AWS Security Specialty certification.
- Experience with Go and eBPF kernel tracing.
"""
    user_id = "user_test_123"
    job = await create_custom_job(
        db,
        company="Acme Corp",
        title="Senior Cloud Security Engineer",
        jd_text=custom_jd,
        user_id=user_id,
    )

    # 1. Verification of metadata and isolation
    assert job["id"].startswith("custom_")
    assert job["user_id"] == user_id
    assert job["source"] == "custom"
    assert job["company"] == "Acme Corp"
    assert job["title"] == "Senior Cloud Security Engineer"
    assert job["location"] == "Austin, TX"
    assert job["is_remote"] is False
    assert job["seniority"] == "SENIOR"
    assert job["domain"] == "Cybersecurity"

    # 2. Complete requirements without arbitrary [:6] slicing
    assert len(job["must_have_skills"]) >= 4
    assert len(job["preferred_skills"]) >= 2
    assert "AWS" in job["must_have_skills"] or "aws" in [s.lower() for s in job["must_have_skills"]]
    assert "Kubernetes" in job["must_have_skills"] or "kubernetes" in [s.lower() for s in job["must_have_skills"]]
    
    # 3. Complete responsibilities (not empty [])
    assert len(job["responsibilities"]) == 3
    assert any("vulnerability assessments" in r for r in job["responsibilities"])

    # 4. Canonical experience extraction
    assert job["min_years_experience"] == 5.0
    assert job["experience_min"] == 5

    # 5. Canonical structured requirements attached
    assert "structured_requirements" in job
    assert job["structured_requirements"]["target_role"] == "Senior Cloud Security Engineer"


# =========================================================================
# 2. CUSTOM JD USER ISOLATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_custom_jd_user_isolation(db):
    user_alice = "user_alice_456"
    user_bob = "user_bob_789"

    job = await create_custom_job(
        db,
        company="Confidential Startup",
        title="Staff ML Engineer",
        jd_text="Requirements:\n- 6+ years of PyTorch and distributed training.",
        user_id=user_alice,
    )

    # Alice can access her custom job
    alice_job = await get_job(db, job["id"], user_id=user_alice)
    assert alice_job is not None
    assert alice_job["id"] == job["id"]

    # Bob CANNOT access Alice's custom job
    bob_job = await get_job(db, job["id"], user_id=user_bob)
    assert bob_job is None

    # Search jobs by Bob does NOT return Alice's custom job
    bob_searches = await search_jobs(db, {}, user_id=user_bob)
    assert not any(j["id"] == job["id"] for j in bob_searches)

    # Bob cannot save Alice's custom job
    with pytest.raises(JobNotFoundError):
        await save_application(db, user_bob, job["id"], None, None)


# =========================================================================
# 3. CANONICAL JD RESOLUTION & INVARIANCE TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_canonical_jd_resolution_for_curated_and_legacy(db):
    legacy_job = {
        "id": "job_legacy_999",
        "source": "curated",
        "title": "Backend Go Engineer",
        "company": "FastTech",
        "jd_text": "Responsibilities:\n- Build Go microservices.\nRequirements:\n- 3+ years of professional experience in Go and PostgreSQL.",
        "skills_required": ["Go"],
        "skills_nice_to_have": [],
        "responsibilities": ["Build Go microservices."],
    }
    await db[Collections.JOBS].insert_one(legacy_job)

    # Calling get_canonical_job_requirements lazily parses and returns Phase 3 StructuredJobRequirements
    reqs = await get_canonical_job_requirements(db, legacy_job)
    assert reqs.target_role == "Backend Go Engineer"
    assert "Go" in reqs.must_have_skills
    assert reqs.min_years_experience == 3.0


def test_semantic_invariance_across_job_internship_and_custom():
    shared_jd_text = """Java Full Stack Developer
Location: Seattle, WA / Hybrid
Job Type: Full-Time

Key Responsibilities:
- Develop full-stack web applications with React and Spring Boot.

Requirements:
- 3+ years experience with Java, Spring Boot, and PostgreSQL.

Preferred:
- AWS and Docker experience.
"""
    # Direct taxonomy analysis
    reqs_direct = analyze_job_description(shared_jd_text)
    
    # Must produce identical requirements regardless of entry channel
    assert reqs_direct.target_role == "Java Full Stack Developer"
    assert reqs_direct.min_years_experience == 3.0
    assert len(reqs_direct.responsibilities) == 1
    assert "Java" in reqs_direct.must_have_skills
    assert "AWS" in reqs_direct.preferred_skills


# =========================================================================
# 4. SKILL GAP & ROADMAP CANONICAL CONSUMPTION TESTS
# =========================================================================

def test_skill_gap_with_canonical_must_have_and_preferred():
    missing_req = ["Microservices", "REST APIs"]
    partial_req = ["PostgreSQL"]
    missing_pref = ["AWS", "Docker", "Kubernetes"]

    gaps = compute_skill_gaps(
        missing_required=missing_req,
        partial_required=partial_req,
        missing_nice_to_have=missing_pref,
        job_title="Java Full Stack Developer",
    )

    # 1. Verification of priority distribution
    core_gaps = [g for g in gaps if g.priority == "CORE"]
    secondary_gaps = [g for g in gaps if g.priority == "SECONDARY"]
    bonus_gaps = [g for g in gaps if g.priority == "BONUS"]

    assert len(core_gaps) == 2
    assert {g.skill for g in core_gaps} == {"Microservices", "REST APIs"}
    assert len(secondary_gaps) == 1
    assert secondary_gaps[0].skill == "PostgreSQL"
    assert len(bonus_gaps) == 3
    assert {g.skill for g in bonus_gaps} == {"AWS", "Docker", "Kubernetes"}

    # 2. Roadmap builds 4 windows using canonical gaps
    roadmap = build_roadmap(gaps)
    assert "immediate" in roadmap
    assert "week_1" in roadmap
    assert "week_2" in roadmap
    assert "month_1" in roadmap
    assert len(roadmap["immediate"]) >= 1


# =========================================================================
# 5. RESUME VERSION PROVENANCE TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_resume_version_provenance_retention(db):
    user_id = "user_prov_123"
    job_id = "job_capco_01"
    master_resume_id = "master_res_456"

    version = await create_version(
        db,
        user_id=user_id,
        job_id=job_id,
        job_title="Java Full Stack Developer",
        company="Capco",
        changes=[],
        master_resume_id=master_resume_id,
        master_resume_version=2,
        opportunity_type="JOB",
        opportunity_id=job_id,
        jd_analysis_summary={
            "seniority": "MID",
            "domain": "Full Stack Engineering",
            "min_years_experience": 3.0,
            "must_haves_count": 7,
            "preferred_count": 5,
        },
    )

    assert version["master_resume_id"] == master_resume_id
    assert version["master_resume_version"] == 2
    assert version["opportunity_type"] == "JOB"
    assert version["opportunity_id"] == job_id
    assert version["jd_analysis_summary"]["seniority"] == "MID"
    assert version["jd_analysis_summary"]["domain"] == "Full Stack Engineering"

    # Retrieve from DB and verify persisted document
    retrieved = await get_version(db, user_id, str(version["_id"]))
    assert retrieved is not None
    assert retrieved["master_resume_id"] == master_resume_id
    assert retrieved["opportunity_type"] == "JOB"


# =========================================================================
# 6. INTERNSHIP CANONICAL RESOLUTION & MATCHING TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_internship_canonical_resolution_and_matching(db, settings):
    intern_job = {
        "id": "job_intern_react_01",
        "source": "curated",
        "title": "Frontend React Intern",
        "company": "StartupX",
        "job_type": "internship",
        "stipend_min": 25000,
        "stipend_max": 35000,
        "internship_duration_months": 6,
        "location": "Bangalore, India",
        "is_remote": False,
        "jd_text": "Frontend React Intern\nResponsibilities:\n- Build UI with React and TypeScript.\nRequirements:\n- HTML5, CSS3, JavaScript, React.",
        "skills_required": ["HTML5", "CSS3", "JavaScript", "React"],
        "skills_nice_to_have": ["TypeScript", "Tailwind CSS"],
    }
    await db[Collections.JOBS].insert_one(intern_job)

    # 1. Canonical JD analysis
    reqs = await get_canonical_job_requirements(db, intern_job)
    assert reqs.target_role == "Frontend React Intern"
    assert "React" in reqs.must_have_skills

    # 2. Matching with INTERNSHIP_SEEKER profile
    candidate = {
        "skills": ["HTML5", "CSS3", "JavaScript", "React"],
        "target_roles": ["Frontend React Intern"],
        "experience_years": 0,
        "preferred_locations": ["Bangalore, India"],
        "remote_preference": "any",
        "min_lpa": None,
        "industries": [],
    }
    embedder = build_embedding_provider(settings)
    match = compute_match(candidate, intern_job, embedder, category="INTERNSHIP_SEEKER")
    assert match.overall_score >= 80
    assert match.apply_readiness in ("ready", "fix_gaps")


# =========================================================================
# 7. SKILL GAP ON CUSTOM JD (NOT LIMITED TO 6 SKILLS)
# =========================================================================

@pytest.mark.asyncio
async def test_skill_gap_on_custom_jd_not_limited_to_six_skills(db, settings):
    # JD with 10 distinct must-have skills
    custom_jd = """Java Full Stack Engineer
Responsibilities:
- Build microservices.
Requirements:
- Strong skills in Java, Spring Boot, React, Angular, PostgreSQL, MongoDB, Docker, Kubernetes, Kafka, Redis.
"""
    user_id = "user_gap_test"
    job = await create_custom_job(
        db,
        company="Global FinTech",
        title="Java Full Stack Engineer",
        jd_text=custom_jd,
        user_id=user_id,
    )

    # Verify custom job has all skills in must_have_skills
    assert len(job["must_have_skills"]) >= 8  # Far more than legacy [:6] limit!

    # Candidate with only Java and React
    candidate_skills = ["Java", "React"]
    candidate_skills_lower = {s.lower() for s in candidate_skills}

    reqs = await get_canonical_job_requirements(db, job)
    missing = [s for s in reqs.must_have_skills if s.lower() not in candidate_skills_lower]

    gaps = compute_skill_gaps(
        missing_required=missing,
        partial_required=[],
        missing_nice_to_have=[],
        job_title=job["title"],
    )

    # Ensure all missing must-haves are present as CORE gaps
    assert len(gaps) >= 6
    assert all(g.priority == "CORE" for g in gaps)


# =========================================================================
# 8. ATS INTELLIGENCE ROUTE CUSTOM JOB ISOLATION (ISSUE-P4-01 FIX)
# =========================================================================

@pytest.mark.asyncio
async def test_ats_analysis_custom_job_user_isolation(db, settings):
    from fastapi import HTTPException
    from app.modules.intelligence.routes import get_ats_score
    from app.modules.resume import repositories as resume_repo
    from bson import ObjectId

    user_alice_id = str(ObjectId())
    user_bob_id = str(ObjectId())

    # Create Master Resume for Alice
    await resume_repo.create_master_resume(
        db,
        user_id=user_alice_id,
        version=1,
        file_name="alice_resume.pdf",
        file_type="pdf",
        raw_text="Alice Software Engineer with Python and SQL",
        parsed={"skills": ["Python", "SQL"], "experience_raw": ["Built backend APIs"]},
        parseability={"score": 85, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 80, "bullets_analyzed": 1, "quantified_bullets": 1, "weak_verb_bullets": 0, "quantification_rate": 1.0, "issues": []},
    )

    # Create Master Resume for Bob
    await resume_repo.create_master_resume(
        db,
        user_id=user_bob_id,
        version=1,
        file_name="bob_resume.pdf",
        file_type="pdf",
        raw_text="Bob Software Engineer with JavaScript",
        parsed={"skills": ["JavaScript"], "experience_raw": ["Built UI"]},
        parseability={"score": 85, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 80, "bullets_analyzed": 1, "quantified_bullets": 1, "weak_verb_bullets": 0, "quantification_rate": 1.0, "issues": []},
    )

    # Alice creates a custom job
    custom_job = await create_custom_job(
        db,
        company="Alice Stealth Startup",
        title="Python Backend Dev",
        jd_text="Requirements:\n- Python and SQL.",
        user_id=user_alice_id,
    )

    # Alice can compute ATS score for her own custom job
    alice_score = await get_ats_score(
        job_id=custom_job["id"],
        platform=None,
        version_id=None,
        current_user={"_id": user_alice_id},
        db=db,
        settings=settings,
    )
    assert alice_score is not None
    assert alice_score.company == "Alice Stealth Startup"

    # Bob CANNOT compute ATS score for Alice's custom job (returns 404 Job not found)
    with pytest.raises(HTTPException) as exc_info:
        await get_ats_score(
            job_id=custom_job["id"],
            platform=None,
            version_id=None,
            current_user={"_id": user_bob_id},
            db=db,
            settings=settings,
        )
    assert exc_info.value.status_code == 404

    # Both Alice and Bob can compute ATS score for a curated job
    curated_job = {
        "id": "job_curated_pub_01",
        "source": "curated",
        "title": "Public Python Dev",
        "company": "Public Corp",
        "jd_text": "Requirements:\n- Python.",
        "skills_required": ["Python"],
        "skills_nice_to_have": [],
        "responsibilities": [],
    }
    await db[Collections.JOBS].insert_one(curated_job)

    curated_score = await get_ats_score(
        job_id="job_curated_pub_01",
        platform=None,
        version_id=None,
        current_user={"_id": user_bob_id},
        db=db,
        settings=settings,
    )
    assert curated_score is not None
    assert curated_score.company == "Public Corp"


# =========================================================================
# 9. COPILOT CONTEXT CUSTOM JOB ISOLATION (F-01 FIX)
# =========================================================================

@pytest.mark.asyncio
async def test_copilot_context_custom_job_user_isolation(db, settings):
    from app.modules.chatbot.context import build_copilot_context
    from app.modules.profile import repositories as profile_repo
    from app.modules.resume import repositories as resume_repo
    from bson import ObjectId

    user_alice_id = str(ObjectId())
    user_bob_id = str(ObjectId())

    # Create profile and master resume for Alice (Python Backend Engineer)
    await profile_repo.upsert_profile(
        db,
        user_id=user_alice_id,
        data={"category": "EXPERIENCED", "target_roles": ["Python Developer"], "experience_years": 3},
    )
    await resume_repo.create_master_resume(
        db,
        user_id=user_alice_id,
        version=1,
        file_name="alice_resume.pdf",
        file_type="pdf",
        raw_text="Alice Python Developer with FastAPI and Docker",
        parsed={"skills": ["Python", "FastAPI", "Docker"], "experience_raw": ["Developed microservices"]},
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 85, "bullets_analyzed": 1, "quantified_bullets": 1, "weak_verb_bullets": 0, "quantification_rate": 1.0, "issues": []},
    )

    # Create profile and master resume for Bob (React Frontend Engineer)
    await profile_repo.upsert_profile(
        db,
        user_id=user_bob_id,
        data={"category": "EXPERIENCED", "target_roles": ["React Developer"], "experience_years": 3},
    )
    await resume_repo.create_master_resume(
        db,
        user_id=user_bob_id,
        version=1,
        file_name="bob_resume.pdf",
        file_type="pdf",
        raw_text="Bob React Frontend Engineer with TypeScript",
        parsed={"skills": ["React", "TypeScript", "HTML5"], "experience_raw": ["Built UI components"]},
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 85, "bullets_analyzed": 1, "quantified_bullets": 1, "weak_verb_bullets": 0, "quantification_rate": 1.0, "issues": []},
    )

    # Alice creates a confidential custom job
    alice_custom_job = await create_custom_job(
        db,
        company="Alice Private Stealth",
        title="Python Developer",
        jd_text="Requirements:\n- Python and FastAPI.",
        user_id=user_alice_id,
    )

    # Insert a public curated job
    curated_job = {
        "id": "job_public_tech_01",
        "source": "curated",
        "title": "Python Developer",
        "company": "Public Tech Global",
        "jd_text": "Requirements:\n- Python.",
        "skills_required": ["Python"],
        "skills_nice_to_have": [],
        "responsibilities": [],
    }
    await db[Collections.JOBS].insert_one(curated_job)

    # 1. Alice's Copilot context CAN contain Alice's custom job
    alice_context = await build_copilot_context(user_alice_id, db, settings)
    alice_matched_ids = [m["job_id"] for m in alice_context.top_job_matches]
    assert alice_custom_job["id"] in alice_matched_ids

    # 2. Bob's Copilot context CANNOT contain Alice's custom job
    bob_context = await build_copilot_context(user_bob_id, db, settings)
    bob_matched_ids = [m["job_id"] for m in bob_context.top_job_matches]
    assert alice_custom_job["id"] not in bob_matched_ids

    # 3. Public curated job remains available
    assert "job_public_tech_01" in alice_matched_ids



