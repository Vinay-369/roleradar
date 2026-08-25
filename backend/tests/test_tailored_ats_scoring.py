"""
Tests validating tailored resume ATS score boosting, quality audit persistence,
and keyword density anti-stuffing behavior.
"""
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.ai_service.schemas import ChangeStatus
from app.core.ai_service.service import AIService
from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.intelligence.ats_score import compute_ats_score, _calculate_keyword_density
from app.modules.intelligence.ats_platform import evaluate_platform_compliance, ATSPlatform
from app.modules.jobs import services as jobs_services
from app.modules.tailoring import services as tailoring_services


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


class MockTailoringAIProvider:
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        import json
        return json.dumps({
            "changes": [
                {
                    "change_id": "c1",
                    "original": "Worked on backend APIs",
                    "proposed": "Architected high-throughput REST APIs with Python, FastAPI, Docker, and MongoDB, reducing latency by 45%",
                    "reason": "Aligns with target JD technical keywords and adds quantified metrics",
                    "source_evidence": "Candidate built backend APIs with Python",
                    "confidence": 0.95,
                    "status": "PENDING",
                }
            ]
        })


def test_keyword_density_does_not_falsely_penalize_high_keyword_matching():
    # A technical resume naturally containing 20+ relevant terms
    resume = (
        "Experienced Software Engineer specializing in Python, FastAPI, Docker, Kubernetes, and PostgreSQL. "
        "Built scalable microservices, REST APIs, and database architectures. "
        "Collaborated with cross-functional engineering teams using Git, CI/CD pipelines, and automated unit testing."
    )
    jd = (
        "Seeking Senior Python Developer with expertise in FastAPI, Docker, Kubernetes, microservices, and PostgreSQL. "
        "Experience with REST APIs, Git, CI/CD, and database performance optimization required."
    )

    coverage, density, over_optimized = _calculate_keyword_density(resume, jd)
    assert coverage >= 50
    assert density <= 3.5  # No single word repeated excessively
    assert over_optimized is False

    score = compute_ats_score(
        resume_text=resume,
        jd_text=jd,
        parseability_score=95,
        recruiter_impact_score=90,
        skill_match_score=90,
        role_match_score=85,
    )
    assert score.over_optimization_warning is False
    assert score.overall >= 80
    # Technical keywords category should not be penalized
    assert score.categories[0].points_awarded >= 30


def test_keyword_density_catches_actual_keyword_spamming():
    # Resume repeating "Python" 20 times in a 300-word text
    resume = ("Python " * 20) + "Developer with experience building applications and tools."
    jd = "Python Developer with experience building applications."

    coverage, density, over_optimized = _calculate_keyword_density(resume, jd)
    assert density > 3.5  # "Python" makes up a huge portion of words
    assert over_optimized is True

    score = compute_ats_score(
        resume_text=resume,
        jd_text=jd,
        parseability_score=80,
        recruiter_impact_score=60,
        skill_match_score=80,
        role_match_score=70,
    )
    assert score.over_optimization_warning is True


@pytest.mark.asyncio
async def test_finalize_tailoring_persists_quality_audit_and_boosts_metrics(db, settings):
    user, _ = await auth_services.register_user(db, settings, "audit_test@example.com", "supersecret1", "Tester", None)
    user_id = str(user["_id"])

    master_resume_text = (
        "Alex Kumar\nalex@example.com · 9876543210\n\n"
        "SKILLS\nPython, JavaScript\n\n"
        "EXPERIENCE\nWorked on backend APIs\n\n"
        "EDUCATION\nB.Tech in Computer Science\n"
    )
    from app.modules.resume import repositories as resume_repo
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="resume.pdf", file_type="pdf",
        raw_text=master_resume_text,
        parsed={
            "skills": ["Python", "JavaScript"],
            "experience_raw": ["Worked on backend APIs"],
        },
        parseability={"score": 85, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {"email": True, "phone": True}, "likely_multi_column": False, "word_count": 30},
        recruiter_impact={"score": 50, "bullets_analyzed": 1, "quantified_bullets": 0, "weak_verb_bullets": 1,
                           "quantification_rate": 0.0, "issues": ["Weak verb"]},
    )

    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    job = jobs[0]

    ai_service = AIService(settings)
    ai_service._provider = MockTailoringAIProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job["id"])
    version_id = str(version["_id"])

    # Approve the high-impact change
    await tailoring_services.set_change_status(db, user_id, version_id, "c1", ChangeStatus.APPROVED)

    finalized = await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    assert finalized["is_finalized"] is True
    assert "Architected high-throughput REST APIs with Python, FastAPI, Docker" in finalized["final_text"]
    assert "audit" in finalized
    assert "strict_ats_score" in finalized["audit"]
    assert "recruiter_impact" in finalized["audit"]
    # Recruiter impact score should improve because weak verb was replaced with strong action verb & metric
    assert finalized["audit"]["recruiter_impact"]["score"] > 50
    assert finalized["audit"]["recruiter_impact"]["weak_verb_bullets"] == 0


@pytest.mark.asyncio
async def test_get_ats_score_with_version_id_produces_different_results(db, settings):
    """
    Regression test proving that GET /intelligence/ats/{job_id} with version_id=None (Master)
    vs version_id=<tailored_version> produces DIFFERENT, improved results based on the tailored text.
    """
    from fastapi import HTTPException
    from app.modules.intelligence.routes import get_ats_score
    from app.modules.resume import repositories as resume_repo
    from app.modules.jobs import repositories as jobs_repo

    user, _ = await auth_services.register_user(db, settings, "regression_diff@example.com", "supersecret1", "Tester", None)
    user_id = str(user["_id"])

    master_text = (
        "Tester Name\ntester@example.com · 9876543210\n\n"
        "SKILLS\nHTML, CSS\n\n"
        "EXPERIENCE\n"
        "Software Engineer at Acme Corp\n"
        "• Worked on backend APIs\n\n"
        "EDUCATION\nB.Sc in CS, 2022\n"
    )
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="master.pdf", file_type="pdf",
        raw_text=master_text,
        parsed={"skills": ["HTML", "CSS"], "experience_raw": ["Worked on backend APIs"]},
        parseability={"score": 75, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {"email": True, "phone": True}, "likely_multi_column": False, "word_count": 25},
        recruiter_impact={"score": 40, "bullets_analyzed": 1, "quantified_bullets": 0, "weak_verb_bullets": 1,
                           "quantification_rate": 0.0, "issues": ["Weak verb"]},
    )

    await jobs_services.ensure_seed_loaded(db)
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    job = jobs[0]

    ai_service = AIService(settings)
    ai_service._provider = MockTailoringAIProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job["id"])
    version_id = str(version["_id"])

    # 1. Calling with unfinalized version_id raises 400
    with pytest.raises(HTTPException) as exc_info:
        await get_ats_score(job_id=job["id"], version_id=version_id, current_user=user, db=db, settings=settings)
    assert exc_info.value.status_code == 400

    # 2. Calling with nonexistent version_id raises 404
    with pytest.raises(HTTPException) as exc_info:
        await get_ats_score(job_id=job["id"], version_id="000000000000000000000000", current_user=user, db=db, settings=settings)
    assert exc_info.value.status_code == 404

    # 3. Approve change and finalize
    await tailoring_services.set_change_status(db, user_id, version_id, "c1", ChangeStatus.APPROVED)
    await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    # 4. Score with version_id=None (Master) vs version_id (Tailored)
    master_ats = await get_ats_score(job_id=job["id"], version_id=None, current_user=user, db=db, settings=settings)
    tailored_ats = await get_ats_score(job_id=job["id"], version_id=version_id, current_user=user, db=db, settings=settings)

    # Proves they produce DIFFERENT results
    assert master_ats.overall != tailored_ats.overall
    assert tailored_ats.readability > master_ats.readability
    assert tailored_ats.keyword_coverage >= master_ats.keyword_coverage


@pytest.mark.asyncio
async def test_tailoring_validation_prevents_silent_metric_loss():
    """
    Given a bullet with a quantified metric (e.g. 'reduced latency by 45%'),
    if the AI proposes a replacement that completely omits the metric,
    the post-replacement validation must reject the destructive splice,
    flag the loss with an explicit validation_error, and ensure final_text
    never silently loses the quantified bullet.
    """
    from app.modules.tailoring.services import _validate_and_apply_change

    resume_text = (
        "EXPERIENCE\n"
        "• Architected distributed caching layer, reducing latency by 45% across 10 microservices\n"
    )
    original = "Architected distributed caching layer, reducing latency by 45% across 10 microservices"
    bad_proposed = "Architected distributed caching layer with Python and Redis"

    new_text, ok, err = _validate_and_apply_change(resume_text, original, bad_proposed, change_id="c_metric_loss")

    assert ok is False
    assert err is not None
    assert "quantified metric" in err
    assert "dropped from original bullet" in err
    # resume_text was NOT corrupted
    assert new_text == resume_text


@pytest.mark.asyncio
async def test_tailoring_validation_prevents_section_header_corruption():
    """
    If a change accidentally replaces or wipes a standard section header,
    validation must reject it and keep the original structure intact.
    """
    from app.modules.tailoring.services import _validate_and_apply_change

    resume_text = (
        "SKILLS\nPython, Docker\n\n"
        "EXPERIENCE\n• Built backend service\n\n"
        "EDUCATION\nB.Tech in Computer Science\n"
    )
    original = "EXPERIENCE\n• Built backend service"
    bad_proposed = "• Built backend service with Golang"  # Wiping EXPERIENCE header

    new_text, ok, err = _validate_and_apply_change(resume_text, original, bad_proposed, change_id="c_header_wipe")

    assert ok is False
    assert err is not None
    assert "section header" in err
    assert new_text == resume_text


@pytest.mark.asyncio
async def test_finalize_computes_and_persists_tailored_scores_feedback_loop(db, settings):
    """
    Test verifying that finalize_tailoring() calculates tailored_scores
    against final_text and persists them on the version document alongside
    master resume scores, calculating score delta and warning status.
    """
    user, _ = await auth_services.register_user(db, settings, "loop_test@example.com", "supersecret1", "Tester", None)
    user_id = str(user["_id"])

    master_text = (
        "Alex Kumar\nalex@example.com · 9876543210\n\n"
        "SKILLS\nJavaScript, CSS\n\n"
        "EXPERIENCE\n"
        "Software Engineer at Acme Corp\n"
        "• Worked on backend APIs\n\n"
        "EDUCATION\nB.Tech in Computer Science\n"
    )
    from app.modules.resume import repositories as resume_repo
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="master.pdf", file_type="pdf",
        raw_text=master_text,
        parsed={"skills": ["JavaScript", "CSS"], "experience_raw": ["Worked on backend APIs"]},
        parseability={"score": 80, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {"email": True, "phone": True}, "likely_multi_column": False, "word_count": 25},
        recruiter_impact={"score": 45, "bullets_analyzed": 1, "quantified_bullets": 0, "weak_verb_bullets": 1,
                           "quantification_rate": 0.0, "issues": ["Weak verb"]},
    )

    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    job = jobs[0]

    ai_service = AIService(settings)
    ai_service._provider = MockTailoringAIProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job["id"])
    version_id = str(version["_id"])

    # Approve change and finalize
    await tailoring_services.set_change_status(db, user_id, version_id, "c1", ChangeStatus.APPROVED)
    finalized = await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    assert finalized["is_finalized"] is True
    assert "tailored_scores" in finalized
    tailored_scores = finalized["tailored_scores"]
    assert tailored_scores is not None

    # Assert scores were computed against final_text
    assert "overall" in tailored_scores
    assert "readability" in tailored_scores
    assert "master_overall" in tailored_scores
    assert "score_delta" in tailored_scores
    assert tailored_scores["overall"] > 0
    assert tailored_scores["readability"] == 100  # Strong action verb + 45% metric in final_text
    assert tailored_scores["recruiter_impact"] > 45  # Boosted over master resume's 45


@pytest.mark.asyncio
async def test_finalize_warns_visibly_when_tailored_resume_scores_lower_than_master(db, settings):
    """
    Acceptance Criteria 3: If a tailored version somehow scores LOWER than
    the original master resume (e.g. key technical skills were removed),
    finalize_tailoring() must detect the score drop and attach an explicit
    score_warning on tailored_scores — it must NEVER happen silently.
    """
    import json
    user, _ = await auth_services.register_user(db, settings, "warn_drop@example.com", "supersecret1", "Tester", None)
    user_id = str(user["_id"])

    # High scoring master resume with all key skills
    master_text = (
        "Senior Engineer\neng@example.com · 9876543210\n\n"
        "SKILLS\nPython, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, AWS, CI/CD, React\n\n"
        "EXPERIENCE\n"
        "Tech Lead at Acme Corp\n"
        "• Architected distributed microservices platform processing 10M daily transactions\n"
        "• Scaled cloud infrastructure reducing server cost by 40%\n\n"
        "EDUCATION\nB.Tech in Computer Science\n"
    )
    from app.modules.resume import repositories as resume_repo
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="master.pdf", file_type="pdf",
        raw_text=master_text,
        parsed={
            "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "Redis", "AWS", "CI/CD", "React"],
            "experience_raw": [
                "Architected distributed microservices platform processing 10M daily transactions",
                "Scaled cloud infrastructure reducing server cost by 40%",
            ],
        },
        parseability={"score": 95, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {"email": True, "phone": True}, "likely_multi_column": False, "word_count": 50},
        recruiter_impact={"score": 90, "bullets_analyzed": 2, "quantified_bullets": 2, "weak_verb_bullets": 0,
                           "quantification_rate": 1.0, "issues": []},
    )

    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    job = jobs[0]

    # Mock provider proposing a degradation (replacing comprehensive skills with generic text)
    class DegradingTailoringProvider:
        async def complete(
            self,
            system_prompt: str,
            user_prompt: str,
            json_mode: bool = False,
            model_override: str | None = None,
        ) -> str:
            return json.dumps({
                "changes": [
                    {
                        "change_id": "c_degrade",
                        "original": "SKILLS\nPython, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, AWS, CI/CD, React",
                        "proposed": "SKILLS\nBasic Computer Skills",
                        "reason": "Simplify skills",
                        "source_evidence": "Candidate master resume",
                        "confidence": 0.5,
                        "status": "PENDING",
                    }
                ]
            })

    ai_service = AIService(settings)
    ai_service._provider = DegradingTailoringProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job["id"])
    version_id = str(version["_id"])

    # User approves this degrading change
    await tailoring_services.set_change_status(db, user_id, version_id, "c_degrade", ChangeStatus.APPROVED)
    finalized = await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    assert finalized["is_finalized"] is True
    tailored_scores = finalized.get("tailored_scores")
    assert tailored_scores is not None

    # Score delta is negative and warning is explicitly populated
    assert tailored_scores["overall"] < tailored_scores["master_overall"]
    assert tailored_scores["score_delta"] < 0
    assert tailored_scores["score_warning"] == "This tailored version scores lower than your original resume for this job. Review before exporting."


@pytest.mark.asyncio
async def test_finalize_prevents_corrupted_edits_from_entering_final_text(db, settings):
    """
    Acceptance Criteria 3: If an approved change would corrupt structure or drop
    quantified metrics, finalize_tailoring() refuses to apply the bad splice,
    flags the error on the change, and keeps final_text safe.
    """
    import json
    user, _ = await auth_services.register_user(db, settings, "corrupt_test@example.com", "supersecret1", "Tester", None)
    user_id = str(user["_id"])

    master_text = (
        "Alex Kumar\nalex@example.com · 9876543210\n\n"
        "SKILLS\nPython, FastAPI\n\n"
        "EXPERIENCE\n"
        "Software Engineer at Acme Corp\n"
        "• Scaled cloud infrastructure, reducing cloud bill by 35% across 8 regions\n\n"
        "EDUCATION\nB.Tech in Computer Science\n"
    )
    from app.modules.resume import repositories as resume_repo
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="master.pdf", file_type="pdf",
        raw_text=master_text,
        parsed={"skills": ["Python", "FastAPI"], "experience_raw": ["Scaled cloud infrastructure, reducing cloud bill by 35% across 8 regions"]},
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {"email": True, "phone": True}, "likely_multi_column": False, "word_count": 30},
        recruiter_impact={"score": 85, "bullets_analyzed": 1, "quantified_bullets": 1, "weak_verb_bullets": 0,
                           "quantification_rate": 1.0, "issues": []},
    )

    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    job = jobs[0]

    # Proposes an edit that strips the 35% metric
    class MetricStrippingProvider:
        async def complete(
            self,
            system_prompt: str,
            user_prompt: str,
            json_mode: bool = False,
            model_override: str | None = None,
        ) -> str:
            return json.dumps({
                "changes": [
                    {
                        "change_id": "c_strip_metric",
                        "original": "Scaled cloud infrastructure, reducing cloud bill by 35% across 8 regions",
                        "proposed": "Scaled cloud infrastructure using Docker and Terraform",
                        "reason": "Add tools",
                        "source_evidence": "Resume experience",
                        "confidence": 0.8,
                        "status": "PENDING",
                    }
                ]
            })

    ai_service = AIService(settings)
    ai_service._provider = MetricStrippingProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job["id"])
    version_id = str(version["_id"])

    await tailoring_services.set_change_status(db, user_id, version_id, "c_strip_metric", ChangeStatus.APPROVED)
    finalized = await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    # final_text preserved the metric and rejected the destructive splice
    assert "reducing cloud bill by 35%" in finalized["final_text"]
    change = finalized["changes"][0]
    assert change["applied_safely"] is False
    assert "quantified metric" in change["validation_error"]
