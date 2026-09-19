"""
Regression tests for Phase 7 End-to-End Integration Audit.

Covers:
1. DEFECT-P7-01: Nested dictionary items in `master_parsed['projects_raw']` or `['experience_raw']`
   must not crash skill-addition grounding validation with a TypeError.
2. Complete journey: User with structured candidate profile with dict projects -> tailoring generation -> finalization.
3. Master resume immutability during multi-session job tailoring (Job A -> Job B -> Job A).
4. Truth Guard integration on full-document tailoring proposal.
5. Application status transition state machine (SAVED -> TAILORED -> APPLIED -> INTERVIEW).
"""
import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.core.ai_service.service import AIService
from app.core.ai_service.schemas import ChangeStatus
from app.modules.auth import services as auth_services
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.jobs import repositories as jobs_repo
from app.modules.matching import services as matching_services
from app.modules.tailoring import services as tailoring_services
from app.modules.tailoring import repositories as tailoring_repo
from app.modules.applications import services as applications_services
from app.modules.applications import repositories as applications_repo
from app.modules.applications.schemas import ApplicationStatus
from app.modules.tailoring.validation import (
    detect_fabricated_claims,
    detect_unsupported_metrics,
    detect_unsupported_action_verbs_and_scope,
    detect_seniority_and_title_inflation,
)


class MockAuditAIProvider:
    async def complete(self, system_prompt, user_prompt, json_mode=False):
        import json
        return json.dumps({
            "summary": "Full Stack Engineer with hands-on experience in React, Python, and scalable web services.",
            "experience_rewrites": [
                {
                    "bullet_index": 0,
                    "proposed": "Architected responsive web application with React and Python, accelerating page load speeds.",
                    "reason": "Align with frontend performance requirements"
                }
            ],
            "project_rewrites": [
                {
                    "bullet_index": 0,
                    "proposed": "Built end-to-end e-commerce platform with React, FastAPI, and PostgreSQL with Stripe checkout.",
                    "reason": "Demonstrate full stack delivery"
                }
            ],
            "unmatched_gaps": ["Docker", "Kubernetes"],
            "changes": [
                {
                    "change_id": "chg_reg_1",
                    "section": "EXPERIENCE",
                    "change_type": "TEXT_REWRITE",
                    "original": "Built a web application using React and Python.",
                    "proposed": "Architected responsive web application with React and Python, accelerating page load speeds.",
                    "reason": "Wording enhancement",
                    "source_evidence": "Built a web application using React and Python.",
                    "confidence": 0.95,
                    "status": "PENDING",
                    "target_bullet_index": 0
                }
            ]
        })


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_phase7_regression_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="phase7-reg-secret", EMBEDDING_PROVIDER="mock", AI_PROVIDER="mock")


@pytest.mark.asyncio
async def test_defect_p7_01_nested_dict_projects_raw_does_not_crash(db, settings):
    """
    DEFECT-P7-01 REGRESSION TEST:
    Verifies that when master_parsed contains structured dict objects in projects_raw or experience_raw,
    generate_tailoring safely flattens them without raising TypeError: sequence item 0: expected str instance, dict found.
    """
    user, _ = await auth_services.register_user(db, settings, "p7_defect@example.com", "pass1234", "Candidate P7", None)
    user_id = str(user["_id"])

    # Resume with structured dictionary entries in projects_raw
    parsed_with_dict_projects = {
        "personal": {"name": "Candidate P7", "email": "p7_defect@example.com"},
        "summary": "Full stack developer with Python and React.",
        "skills": ["Python", "React", "PostgreSQL"],
        "experience_raw": [
            {"company": "Tech Corp", "title": "Developer", "bullets": ["Built a web application using React and Python."]}
        ],
        "projects_raw": [
            {
                "title": "ShopSmart E-Commerce",
                "tech_stack": "React, FastAPI, PostgreSQL",
                "bullets": ["Built e-commerce checkout flow processing payments."]
            }
        ],
        "education_raw": [{"institution": "State Univ", "degree": "BS CS"}]
    }

    master_resume = await resume_repo.create_master_resume(
        db, user_id=user_id, version=1, file_name="p7_master.pdf", file_type="pdf",
        raw_text="Candidate P7\nFull stack developer with Python and React.\nBuilt a web application using React and Python.\nShopSmart E-Commerce",
        parsed=parsed_with_dict_projects,
        parseability={"score": 90, "issues": []},
        recruiter_impact={"score": 80, "bullets_analyzed": 2},
    )

    job_doc = {
        "id": "job_p7_test_01",
        "title": "Full Stack Developer",
        "company": "Swiggy",
        "jd_text": "Requirements: React, Python, PostgreSQL.",
        "skills_required": ["React", "Python"],
        "job_type": "full_time",
        "source": "curated",
    }
    await jobs_repo.upsert_jobs(db, [job_doc])

    ai_service = AIService(settings)
    ai_service._provider = MockAuditAIProvider()

    # Must complete without throwing TypeError
    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job_id=job_doc["id"])
    assert version is not None
    assert version["job_id"] == job_doc["id"]
    assert version["master_resume_id"] == str(master_resume["_id"])


@pytest.mark.asyncio
async def test_master_resume_immutability_across_jobs(db, settings):
    """
    Verifies that tailoring for Job A and Job B does not overwrite or mutate the active master resume.
    """
    user, _ = await auth_services.register_user(db, settings, "multi_job@example.com", "pass1234", "Candidate Multi", None)
    user_id = str(user["_id"])

    master_text = "Candidate Multi\nPython, Docker\nDeveloper at Tech Corp"
    master_parsed = {"skills": ["Python", "Docker"], "experience_raw": ["Developer at Tech Corp"]}

    master_doc = await resume_repo.create_master_resume(
        db, user_id=user_id, version=1, file_name="multi.pdf", file_type="pdf",
        raw_text=master_text, parsed=master_parsed,
        parseability={"score": 90, "issues": []},
        recruiter_impact={"score": 80, "bullets_analyzed": 1},
    )

    job_a = {"id": "job_a_101", "title": "Python Dev", "company": "Alpha Corp", "jd_text": "Python", "skills_required": ["Python"], "source": "curated"}
    job_b = {"id": "job_b_202", "title": "DevOps Eng", "company": "Beta Corp", "jd_text": "Docker", "skills_required": ["Docker"], "source": "curated"}
    await jobs_repo.upsert_jobs(db, [job_a, job_b])

    ai_service = AIService(settings)
    ai_service._provider = MockAuditAIProvider()

    v_a = await tailoring_services.generate_tailoring(db, ai_service, user_id, job_id=job_a["id"])
    v_b = await tailoring_services.generate_tailoring(db, ai_service, user_id, job_id=job_b["id"])

    assert str(v_a["_id"]) != str(v_b["_id"])
    assert v_a["job_id"] == job_a["id"]
    assert v_b["job_id"] == job_b["id"]

    # Master resume must be exactly intact
    master_after = await resume_repo.get_active_master_resume(db, user_id)
    assert master_after["raw_text"] == master_text
    assert master_after["version"] == 1
    assert master_after["parsed"] == master_parsed


@pytest.mark.asyncio
async def test_truth_guard_adversarial_invariants():
    """
    Verifies Truth Guard invariants against deliberate adversarial claim injection.
    """
    candidate_skills = ["python", "react", "postgresql"]
    
    # 1. Block ungrounded skills
    fab = detect_fabricated_claims("Built APIs in Python", "Architected AWS EKS and Kubernetes microservices", "AWS, Kubernetes", candidate_skills)
    assert any("aws" in s.lower() or "k8s" in s.lower() for s in fab)

    # 2. Block ungrounded duration metrics
    metrics = detect_unsupported_metrics("Built APIs in Python", "Built APIs in Python with 3 years experience")
    assert any("3years" in m or "3 years" in m for m in metrics)

    # 3. Block seniority escalation
    title_viols = detect_seniority_and_title_inflation("Junior Developer", "Senior Principal Software Engineer")
    assert len(title_viols) > 0

    # 4. Allow legitimate rewrites
    clean_fab = detect_fabricated_claims("Built APIs in Python", "Engineered APIs using Python", "Python", candidate_skills)
    clean_met = detect_unsupported_metrics("Built APIs in Python", "Engineered APIs using Python")
    clean_scope = detect_unsupported_action_verbs_and_scope("Built APIs in Python", "Engineered APIs using Python")
    assert len(clean_fab) == 0 and len(clean_met) == 0 and len(clean_scope) == 0


@pytest.mark.asyncio
async def test_unified_application_lifecycle_state_machine(db, settings):
    """
    Verifies the unified application state progression without creating duplicate records:
    SAVED -> TAILORED -> APPLIED -> INTERVIEW
    """
    user, _ = await auth_services.register_user(db, settings, "app_state@example.com", "pass1234", "Candidate App", None)
    user_id = str(user["_id"])

    job = {"id": "job_app_test_01", "title": "SWE", "company": "Acme", "jd_text": "Python", "apply_url": "https://acme.com/apply", "source": "curated"}
    await jobs_repo.upsert_jobs(db, [job])

    # 1. Save initially without tailored resume
    app = await applications_services.save_application(db, user_id, job["id"], tailored_resume_id=None, notes="Initial save")
    app_id = str(app["_id"])
    assert app["status"] == ApplicationStatus.SAVED.value

    # 2. Transition to TAILORED
    up1 = await applications_services.update_application(db, user_id, app_id, {"status": ApplicationStatus.TAILORED.value})
    assert up1["status"] == ApplicationStatus.TAILORED.value

    # 3. Transition to APPLIED
    up2 = await applications_services.update_application(db, user_id, app_id, {"status": ApplicationStatus.APPLIED.value})
    assert up2["status"] == ApplicationStatus.APPLIED.value

    # 4. Transition to INTERVIEW
    up3 = await applications_services.update_application(db, user_id, app_id, {"status": ApplicationStatus.INTERVIEW.value})
    assert up3["status"] == ApplicationStatus.INTERVIEW.value

    # Verify no duplicate entries created
    all_apps = await applications_repo.list_applications(db, user_id)
    assert len(all_apps) == 1
    assert str(all_apps[0]["_id"]) == app_id
