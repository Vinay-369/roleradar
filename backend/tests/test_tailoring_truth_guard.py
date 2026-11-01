"""
These tests prove the Truth Guard enforcement point: finalize_tailoring
only ever applies changes with status == APPROVED, regardless of what
the model proposed or what status it suggested. A fake AI provider is
injected in place of AIService's real provider — this sandbox has no
live Ollama/LM Studio to call, but the finalize logic being tested here
is deterministic Python and doesn't depend on model quality, only on
whether the approval gate is respected.
"""
import json

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.ai_service.service import AIService
from app.core.config import Settings
from app.modules.auth import services as auth_services
from app.modules.jobs import services as jobs_services
from app.modules.resume import services as resume_services
from app.modules.resume.models import CandidateProfile
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.tailoring import services as tailoring_services
from app.modules.tailoring.validation import (
    detect_dropped_source_skills,
    detect_sentence_fragments_and_truncation,
    detect_unsupported_summary_claims,
    detect_unsupported_action_verbs_and_scope,
    detect_unsupported_metrics,
    has_verbatim_source_evidence,
    validate_tailored_profile_truth_guard,
)


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def settings():
    return Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")


def test_truth_guard_rejects_technology_borrowed_from_another_project():
    source_text = """Jordan Lee
SKILLS
Python, Java, SQL
PROJECTS
Web Analytics Dashboard
Technologies: Python, FastAPI
Built a dashboard using Python and FastAPI.
Library Records CLI
Technologies: Java, MySQL
Created a command-line application using prepared SQL statements.
"""
    source = CandidateProfile.from_parsed_dict(
        structure_resume_text(source_text), source_text
    )
    tailored = source.model_copy(deep=True)
    target_project = tailored.projects[1]
    proposed_bullet = "Built a Python-based CLI using prepared SQL statements."
    target_project.bullets[0] = proposed_bullet
    target_project.evidence_units[0].original_text = proposed_bullet
    target_project.evidence_units[0].normalized_text = proposed_bullet
    target_evidence = next(
        evidence for evidence in tailored.evidence_units
        if evidence.entity_id == target_project.id
    )
    target_evidence.original_text = proposed_bullet
    target_evidence.normalized_text = proposed_bullet

    _, audit = validate_tailored_profile_truth_guard(source, tailored, auto_revert=False)

    assert not audit.is_valid
    assert "python" in {technology.lower() for technology in audit.unsupported_technologies}
    assert any("not evidenced for its resume entity" in violation for violation in audit.violations)


def test_project_proposal_gate_does_not_treat_global_skills_as_project_evidence():
    original = "Created a command-line application using prepared SQL statements."
    proposed = "Built a Python-based CLI using prepared SQL statements."
    warning = tailoring_services._truth_guard_warning(
        original,
        proposed,
        "The target role requests Python.",
        ["Python", "Java", "SQL"],
        source_evidence=original,
        require_verbatim_evidence=True,
        entity_source_text=(
            "Library Records CLI Java MySQL Created a command-line application "
            "using prepared SQL statements."
        ),
    )

    assert warning is not None
    assert "not evidenced for this resume entity" in warning


def test_summary_scope_and_experience_claims_need_resume_evidence():
    proposed = (
        "Software engineer with solid experience building developer tooling, "
        "data processing pipelines, and backend platforms."
    )
    source = "Final-year student with project experience building web applications and REST APIs."

    violations = detect_unsupported_summary_claims(proposed, source)

    assert any("Experience-strength claim" in item for item in violations)
    assert any("tooling" in item.lower() for item in violations)
    assert any("pipelines" in item.lower() for item in violations)
    assert any("platforms" in item.lower() for item in violations)
    assert detect_unsupported_summary_claims(
        "Candidate has solid experience building developer tooling, data pipelines, and backend platforms.",
        "Candidate has solid experience building developer tooling, data pipelines, and backend platforms.",
    ) == []


def test_approved_skill_reorder_accepts_canonical_source_abbreviations():
    source_text = "TECHNICAL SKILLS\nCore Concepts\nOOP"
    change = {
        "change_id": "skill-reorder",
        "section": "SKILLS",
        "change_type": "SKILL_REORDER",
        "status": "APPROVED",
        "after_order": ["Object-Oriented Programming"],
    }

    allowed, excluded = tailoring_services.approved_preview_change_ids(
        {"skills": ["OOP"]},
        [change],
        source_resume_text=source_text,
    )

    assert allowed == {"skill-reorder"}
    assert excluded == []


class FakeTailoringProvider:
    """Returns one legitimate change (grounded in real resume text) and
    one suspicious change with no real source_evidence — simulating a
    model attempting to fabricate a claim. Truth Guard's job is to make
    sure the second one can never reach final_text unless a human
    explicitly approves it, and even a human-approved one should only
    land if the user actually chose APPROVED."""

    async def complete(self, system_prompt, user_prompt, json_mode=False):
        return json.dumps({
            "changes": [
                {
                    "change_id": "c1",
                    "original": "Built a REST API serving 10,000 requests per day",
                    "proposed": "Engineered a high-throughput REST API handling 10,000+ daily requests",
                    "reason": "Stronger action verb, aligns with JD language",
                    "source_evidence": "Directly rephrases an existing bullet from the master resume",
                    "confidence": 0.9,
                    "status": "PENDING",
                },
                {
                    "change_id": "c2",
                    "original": "",
                    "proposed": "Expert in Kubernetes and led a 10-person infra team",
                    "reason": "JD asks for Kubernetes expertise",
                    "source_evidence": "",
                    "confidence": 0.2,
                    "status": "NEEDS_USER_INPUT",
                },
            ]
        })


async def _setup_user_with_resume_and_job(db, settings):
    user, _ = await auth_services.register_user(db, settings, "tg@example.com", "supersecret1", "T", None)
    user_id = str(user["_id"])

    resume_text = (
        "T Rao\ntrao@example.com 9876543210\n\nSkills\nPython, FastAPI\n\n"
        "Experience\nBuilt a REST API serving 10,000 requests per day\n\n"
        "Education\nB.Tech CS\n"
    )
    # ingest_resume expects real file bytes; for this unit test we bypass
    # file parsing and write the master resume doc directly, since only
    # tailoring logic is under test here.
    from app.modules.resume import repositories as resume_repo
    doc = await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="t.pdf", file_type="pdf",
        raw_text=resume_text,
        parsed={"skills": ["Python", "FastAPI"], "experience_raw": ["Built a REST API serving 10,000 requests per day"]},
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 80, "bullets_analyzed": 1, "quantified_bullets": 1, "weak_verb_bullets": 0,
                           "quantification_rate": 1.0, "issues": []},
    )

    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)
    job = jobs[0]

    return user_id, job["id"]


@pytest.mark.asyncio
async def test_identical_tailoring_proposals_are_omitted_and_noop_finalization_preserves_master(db, settings):
    from app.core.ai_service.schemas import SkillsTailoring, StructuredTailoringResult, SummaryTailoring
    from app.modules.resume import repositories as resume_repo

    user_id, _ = await _setup_user_with_resume_and_job(db, settings)

    class UnchangedTailoringService:
        async def generate_resume_rewrite(self, master_resume_json, **_kwargs):
            payload = json.loads(master_resume_json)
            summary = str(payload.get("summary") or "")
            return StructuredTailoringResult(
                summary=SummaryTailoring(
                    original=summary,
                    proposed=summary,
                    reason="Reviewed against the target JD.",
                    source_evidence=summary,
                ) if summary else None,
                skills=SkillsTailoring(ordered_skills=list(payload.get("skills") or [])),
            )

    master_before = await resume_repo.get_active_master_resume(db, user_id)
    version = await tailoring_services.generate_tailoring(
        db,
        UnchangedTailoringService(),
        user_id,
        custom_company="No-op Research Lab",
        custom_role_title="Backend Engineer",
        custom_jd_text="Research general backend role fit without adding requirements absent from the candidate resume.",
    )

    assert version["changes"] == []
    assert "No meaningful evidence-supported edits" in version["recommendation_note"]

    finalized = await tailoring_services.finalize_tailoring(
        db, user_id, str(version["_id"]), settings=settings
    )
    master_after = await resume_repo.get_master_resume_version(
        db, user_id, str(master_before["_id"]), master_before["version"]
    )

    assert finalized["is_finalized"] is True
    assert finalized["parsed"] == tailoring_services.canonical_master_parsed(master_before)
    assert master_after["raw_text"] == master_before["raw_text"]
    assert master_after["parsed"] == master_before["parsed"]


@pytest.mark.asyncio
async def test_finalize_only_applies_approved_changes(db, settings):
    user_id, job_id = await _setup_user_with_resume_and_job(db, settings)

    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()  # inject fake provider, no live model needed

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job_id)
    version_id = str(version["_id"])

    # Approve only the legitimate, evidence-backed change.
    await tailoring_services.set_change_status(db, user_id, version_id, "c1", __import__(
        "app.core.ai_service.schemas", fromlist=["ChangeStatus"]
    ).ChangeStatus.APPROVED)

    finalized = await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    assert "Engineered a high-throughput REST API" in finalized["final_text"]
    # The unapproved, unevidenced fabrication must never appear, even
    # though the model proposed it.
    assert "Expert in Kubernetes" not in finalized["final_text"]
    assert "10-person infra team" not in finalized["final_text"]


@pytest.mark.asyncio
async def test_finalize_excludes_pending_changes_by_default(db, settings):
    """A change nobody has reviewed yet must NOT be treated as approved
    just because finalize was called — this is the core anti-fabrication
    guarantee: silence is never consent."""
    user_id, job_id = await _setup_user_with_resume_and_job(db, settings)

    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job_id)
    version_id = str(version["_id"])

    # No approvals at all — finalize immediately.
    finalized = await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    assert "Engineered a high-throughput REST API" not in finalized["final_text"]
    assert finalized["final_text"] == (
        "T Rao\ntrao@example.com 9876543210\n\nSkills\nPython, FastAPI\n\n"
        "Experience\nBuilt a REST API serving 10,000 requests per day\n\n"
        "Education\nB.Tech CS\n"
    )


@pytest.mark.asyncio
async def test_needs_user_input_change_cannot_be_silently_approved_into_final(db, settings):
    """Even if a caller tries to mark the NEEDS_USER_INPUT change as
    APPROVED, that's a legitimate explicit user action the API allows
    (a human reviewing it and choosing to accept a rephrasing) — but
    the fabricated, evidence-free version must still never appear
    because the human never actually saw evidence for it in this test,
    only chose to reject it, which is the realistic path."""
    user_id, job_id = await _setup_user_with_resume_and_job(db, settings)

    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job_id)
    version_id = str(version["_id"])

    from app.core.ai_service.schemas import ChangeStatus
    await tailoring_services.set_change_status(db, user_id, version_id, "c2", ChangeStatus.REJECTED)
    finalized = await tailoring_services.finalize_tailoring(db, user_id, version_id, settings=settings)

    assert "Expert in Kubernetes" not in finalized["final_text"]


def test_truth_guard_flags_metrics_added_by_a_rewrite():
    original = "Built a FastAPI service for internal reporting."
    proposed = "Engineered a FastAPI service that reduced reporting time by 65%."

    assert detect_unsupported_metrics(original, proposed) == ["65%"]


def test_truth_guard_flags_dropped_skills_and_generic_evidence():
    original = "Developed an AI-powered Streamlit application using OpenCV and Python."
    proposed = "Architected responsive full-stack features using Java."

    dropped = detect_dropped_source_skills(original, proposed)
    assert "opencv" in dropped
    assert "python" in dropped
    assert has_verbatim_source_evidence(original, "Master resume project") is False
    assert has_verbatim_source_evidence(original, "using OpenCV and Python") is True


@pytest.mark.asyncio
async def test_needs_user_input_change_cannot_be_approved_without_regeneration(db, settings):
    user_id, job_id = await _setup_user_with_resume_and_job(db, settings)
    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()

    version = await tailoring_services.generate_tailoring(db, ai_service, user_id, job_id)
    from app.core.ai_service.schemas import ChangeStatus

    with pytest.raises(tailoring_services.InvalidChangeStatusError):
        await tailoring_services.set_change_status(
            db, user_id, str(version["_id"]), "c2", ChangeStatus.APPROVED
        )


@pytest.mark.asyncio
async def test_generate_tailoring_requires_master_resume(db, settings):
    user, _ = await auth_services.register_user(db, settings, "nomaster@example.com", "supersecret1", "N", None)
    await jobs_services.ensure_seed_loaded(db)
    from app.modules.jobs import repositories as jobs_repo
    jobs = await jobs_repo.find_jobs(db, {}, limit=1)

    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()

    with pytest.raises(tailoring_services.NoMasterResumeError):
        await tailoring_services.generate_tailoring(db, ai_service, str(user["_id"]), jobs[0]["id"])


@pytest.mark.asyncio
async def test_custom_pasted_jd_flows_through_same_pipeline_as_curated_job(db, settings):
    """Regression coverage for the reported gap: a user must be able to
    paste an arbitrary JD (not just pick a curated job) and get a real
    tailoring proposal, with the resulting job discoverable via ATS/
    skill-gap/interview endpoints exactly like a curated job."""
    user, _ = await auth_services.register_user(db, settings, "custom@example.com", "supersecret1", "C", None)
    user_id = str(user["_id"])

    from app.modules.resume import repositories as resume_repo
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="r.pdf", file_type="pdf",
        raw_text="Built a REST API serving 10,000 requests per day",
        parsed={"skills": ["Python", "FastAPI"], "experience_raw": ["Built a REST API serving 10,000 requests per day"]},
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 80, "bullets_analyzed": 1, "quantified_bullets": 1, "weak_verb_bullets": 0,
                           "quantification_rate": 1.0, "issues": []},
    )

    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()

    version = await tailoring_services.generate_tailoring(
        db, ai_service, user_id,
        job_id=None,
        custom_company="Acme Corp",
        custom_role_title="Backend Engineer",
        custom_jd_text="Looking for a Python engineer with FastAPI and Docker experience.",
    )

    assert version["company"] == "Acme Corp"
    assert version["job_id"].startswith("custom_")

    # The custom job must actually exist in the jobs collection with
    # source="custom" -- this is what lets ATS/skill-gap/interview
    # endpoints work on it via the normal job_id-based lookups.
    from app.modules.jobs import repositories as jobs_repo
    job = await jobs_repo.get_job_by_id(db, version["job_id"])
    assert job is not None
    assert job["source"] == "custom"
    assert "Python" in job["skills_required"]
    assert job["apply_url"] == ""  # honest: no fabricated apply link for a hypothetical JD


@pytest.mark.asyncio
async def test_generate_tailoring_requires_either_job_id_or_custom_jd(db, settings):
    user, _ = await auth_services.register_user(db, settings, "neither@example.com", "supersecret1", "N", None)
    user_id = str(user["_id"])

    from app.modules.resume import repositories as resume_repo
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="r.pdf", file_type="pdf",
        raw_text="text", parsed={"skills": []},
        parseability={"score": 80, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {}, "likely_multi_column": False, "word_count": 5},
        recruiter_impact={"score": 70, "bullets_analyzed": 0, "quantified_bullets": 0, "weak_verb_bullets": 0,
                           "quantification_rate": 0, "issues": []},
    )

    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()

    with pytest.raises(tailoring_services.MissingJobOrJDError):
        await tailoring_services.generate_tailoring(db, ai_service, user_id)


@pytest.mark.asyncio
async def test_delete_tailored_version_removes_it_completely(db, settings):
    user, _ = await auth_services.register_user(db, settings, "delete_tailor@example.com", "supersecret1", "D", None)
    user_id = str(user["_id"])

    from app.modules.resume import repositories as resume_repo
    await resume_repo.create_master_resume(
        db, user_id, version=1, file_name="r.pdf", file_type="pdf",
        raw_text="text", parsed={"skills": []},
        parseability={"score": 80, "issues": [], "detected_sections": [], "missing_standard_sections": [],
                       "contact_info_found": {}, "likely_multi_column": False, "word_count": 5},
        recruiter_impact={"score": 70, "bullets_analyzed": 0, "quantified_bullets": 0, "weak_verb_bullets": 0,
                           "quantification_rate": 0, "issues": []},
    )

    ai_service = AIService(settings)
    ai_service._provider = FakeTailoringProvider()

    version = await tailoring_services.generate_tailoring(
        db, ai_service, user_id,
        job_id=None,
        custom_company="DeleteMe Corp",
        custom_role_title="Backend",
        custom_jd_text="Looking for a Python engineer.",
    )
    version_id = str(version["_id"])

    # Verify created
    from app.modules.tailoring import repositories as repo
    found = await repo.get_version(db, user_id, version_id)
    assert found is not None

    # Delete version
    success = await tailoring_services.delete_tailored_version(db, user_id, version_id)
    assert success is True

    # Verify deleted
    found_after = await repo.get_version(db, user_id, version_id)
    assert found_after is None

    # Deleting again raises VersionNotFoundError
    with pytest.raises(tailoring_services.VersionNotFoundError):
        await tailoring_services.delete_tailored_version(db, user_id, version_id)


def test_detect_unsupported_action_verbs_and_scope_audit():
    source_cataract = (
        "Convolutional Neural Network (CNN) image classification model using Python, "
        "TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy."
    )

    # 1. Unsupported deployment claim on a student/research DL model
    unsupported_deployed = (
        "Deployed a convolutional Neural Network (CNN) image classification model using Python, "
        "TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy."
    )
    violations = detect_unsupported_action_verbs_and_scope(source_cataract, unsupported_deployed)
    assert any("Deployment claim (deployed)" in v for v in violations)

    # 2. Unsupported leadership claim
    unsupported_leadership = (
        "Spearheaded the development of a Convolutional Neural Network (CNN) image classification model "
        "using Python, TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy."
    )
    violations_lead = detect_unsupported_action_verbs_and_scope(source_cataract, unsupported_leadership)
    assert any("Leadership claim (spearheaded)" in v for v in violations_lead)

    # 3. Unsupported architecture escalation
    unsupported_arch = (
        "Architected a scalable Convolutional Neural Network (CNN) image classification model "
        "using Python, TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy."
    )
    violations_arch = detect_unsupported_action_verbs_and_scope(source_cataract, unsupported_arch)
    assert any("Architecture claim (architected)" in v for v in violations_arch)

    api_implementation_source = "Created REST routes for listing products and documented API requests."
    architecture_escalation = "Architected RESTful backend services and documented API requests."
    architecture_violations = detect_unsupported_action_verbs_and_scope(
        api_implementation_source,
        architecture_escalation,
    )
    assert any("Architecture claim (architected)" in v for v in architecture_violations)

    # 4. Verified faithful paraphrase with neutral engineering verb
    verified_developed = (
        "Developed a Convolutional Neural Network (CNN) image classification model using Python, "
        "TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy."
    )
    violations_dev = detect_unsupported_action_verbs_and_scope(source_cataract, verified_developed)
    assert len(violations_dev) == 0

    verified_built = (
        "Built a Convolutional Neural Network (CNN) image classification model using Python, "
        "TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy."
    )
    violations_built = detect_unsupported_action_verbs_and_scope(source_cataract, verified_built)
    assert len(violations_built) == 0


def test_truth_guard_rejects_sentence_fragments_and_headless_bullets():
    """
    Truth Guard Rule: Every source evidence unit must produce either:
    1. A complete faithful paraphrase, OR
    2. A complete tailored rewrite supported by the same evidence.
    It must NEVER produce an incomplete sentence fragment, headless bullet, or orphaned continuation.
    """
    # 1. Concrete regression: Headless noun fragment missing 'Engineered a'
    source_cdn = "Engineered a global CDN distribution optimized for low-latency communication."
    headless_cdn = "• global CDN distribution optimized for low-latency communication."
    violations_cdn = detect_sentence_fragments_and_truncation(source_cdn, headless_cdn)
    assert len(violations_cdn) > 0
    assert any("lowercase" in v or "fragment" in v or "action verb" in v for v in violations_cdn)

    # 2. Orphaned continuation starting with conjunction
    source_cicd = "Built automated CI/CD pipeline using GitHub Actions."
    orphaned_prop = "and deployed on AWS"
    violations_conj = detect_sentence_fragments_and_truncation(source_cicd, orphaned_prop)
    assert len(violations_conj) > 0
    assert any("orphaned continuation" in v for v in violations_conj)

    # 3. Abruptly truncated sentence ending in dangling preposition/comma
    source_db = "Optimized database queries for PostgreSQL."
    truncated_prop = "Optimized database queries for,"
    violations_trunc = detect_sentence_fragments_and_truncation(source_db, truncated_prop)
    assert len(violations_trunc) > 0
    assert any("truncated" in v or "dangling" in v for v in violations_trunc)

    # 4. Valid faithful paraphrase must be accepted
    valid_paraphrase = "Engineered global CDN distribution optimized for low latency."
    violations_valid = detect_sentence_fragments_and_truncation(source_cdn, valid_paraphrase)
    assert len(violations_valid) == 0

    # 5. Truth Guard service warning check
    warning = tailoring_services._truth_guard_warning(
        original=source_cdn,
        proposed=headless_cdn,
        jd_text="We need engineers with CDN experience.",
        master_skills=["CDN", "Distributed Systems"],
    )
    assert warning is not None
    assert any(term in warning.lower() for term in ["fragment", "lowercase", "action verb"])

