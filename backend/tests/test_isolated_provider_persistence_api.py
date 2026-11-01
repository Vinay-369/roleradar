from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import mongomock_motor
import pytest

from app.core.config import Settings, get_settings
from app.db.mongo import Collections, get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs.routes import router as jobs_router
from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider
from app.modules.matching.routes import router as matching_router
from app.modules.matching import services as matching_services
from app.modules.resume.routes import router as resume_router


BOARD = "SyntheticAutomationBoard"
USER_ID = "isolated-provider-integration-user"
JOB_ID = "smartrecruiters_syntheticautomationboard_synthetic-req-001"


def _listing(job_id: str = "synthetic-req-001") -> dict:
    return {
        "id": job_id,
        "name": "Platform Engineer",
        "company": {"identifier": BOARD, "name": "Example Robotics"},
        "releasedDate": "2026-10-01T12:00:00Z",
        "location": {"fullLocation": "Bengaluru, Karnataka, India", "country": "in", "remote": False},
        "industry": {"label": "Engineering"},
        "function": {"label": "Software"},
        "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
        "experienceLevel": {"id": "mid_senior_level", "label": "Mid-Senior level"},
        "postingUrl": f"https://jobs.smartrecruiters.com/{BOARD}/{job_id}",
        "applyUrl": f"https://jobs.smartrecruiters.com/{BOARD}/{job_id}/apply",
    }


def _detail(required_text: str) -> dict:
    return {
        "jobAd": {
            "sections": {
                "jobDescription": {
                    "title": "Job Description",
                    "text": "Build developer platforms using Python and Kafka.",
                },
                "qualifications": {
                    "title": "Required Skills",
                    "text": required_text + "\nMinimum 5 years of professional experience.",
                },
                "additionalInformation": {
                    "title": "Preferred Qualifications",
                    "text": "Experience with Docker.",
                },
                "responsibilities": {
                    "title": "Responsibilities",
                    "text": "Design and maintain reliable internal services.",
                },
            }
        }
    }


class ExactMatchOnlyEmbedder:
    def similarity(self, left: str, right: str) -> float:
        return 1.0 if left.casefold() == right.casefold() else 0.0


@pytest.mark.asyncio
async def test_smartrecruiters_persistence_api_and_match_cache_are_isolated(monkeypatch):
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["roleradar_isolated_provider_persistence_test"]
    settings = Settings(EMBEDDING_PROVIDER="mock")
    provider = SmartRecruitersJobProvider(settings)
    sparse_listing = _listing()

    async def detail_for_first_sync(board: str, job_id: str):
        return {**sparse_listing, **_detail("Python")}

    monkeypatch.setattr(provider, "fetch_company_openings", AsyncMock(return_value=[sparse_listing, deepcopy(sparse_listing)]))
    monkeypatch.setattr(provider, "_fetch_detail_rate_limited", AsyncMock(side_effect=detail_for_first_sync))
    first_sync = await provider.sync_company_openings(db, BOARD)
    assert first_sync["fetched"] == 2
    assert first_sync["verified_active"] == 2
    assert first_sync["unique_requisitions"] == 1
    assert await db[Collections.JOBS].count_documents({"id": JOB_ID}) == 1

    stored = await db[Collections.JOBS].find_one({"id": JOB_ID})
    assert stored["jd_evidence_status"] == "COMPLETE"
    assert stored["jd_evidence_source"] == "EMPLOYER_JOB_AD"
    assert stored["url_type"] == "DIRECT_REQUISITION"
    assert stored["source_url"] == sparse_listing["postingUrl"]
    assert stored["apply_url"] == sparse_listing["applyUrl"]
    assert "Kafka" in stored["description"]
    assert stored["skills_required"] == ["Python"]
    assert stored["skills_nice_to_have"] == ["Docker"]
    assert any("Design and maintain" in row for row in stored["responsibilities"])
    assert stored["experience_min"] == 5
    assert any(row["evidence_type"] == "EXPLICIT" for row in stored["structured_requirements"]["requirements"])
    assert any(row["evidence_type"] == "INFERRED" for row in stored["structured_requirements"]["requirements"])

    monkeypatch.setattr(provider, "fetch_company_openings", AsyncMock(return_value=[sparse_listing]))
    monkeypatch.setattr(provider, "_fetch_detail_rate_limited", AsyncMock(return_value=None))
    await provider.sync_company_openings(db, BOARD)
    preserved = await db[Collections.JOBS].find_one({"id": JOB_ID})
    assert preserved["jd_text"] == stored["jd_text"]
    assert preserved["jd_evidence_status"] == "COMPLETE"

    no_requirements_listing = {**_listing("synthetic-req-no-skills"), "name": "Research Engineer"}
    no_requirements_id = "smartrecruiters_syntheticautomationboard_synthetic-req-no-skills"
    no_requirements_detail = {
        **no_requirements_listing,
        "jobAd": {"sections": {"jobDescription": {"title": "Job Description", "text": "The team uses Rust and Kubernetes to build automation tools."}}},
    }
    monkeypatch.setattr(provider, "fetch_company_openings", AsyncMock(return_value=[sparse_listing, no_requirements_listing]))

    async def details_by_id(board: str, job_id: str):
        if job_id == "synthetic-req-001":
            return {**sparse_listing, **_detail("Python")}
        return no_requirements_detail

    monkeypatch.setattr(provider, "_fetch_detail_rate_limited", AsyncMock(side_effect=details_by_id))
    await provider.sync_company_openings(db, BOARD)
    no_requirements = await db[Collections.JOBS].find_one({"id": no_requirements_id})
    assert no_requirements["skills_required"] == []
    assert no_requirements["structured_requirements"]["role_overview"]
    assert no_requirements["structured_requirements"]["requirements"] == []

    await db[Collections.MASTER_RESUMES].insert_one({
        "user_id": USER_ID,
        "version": 1,
        "is_active": True,
        "parsed": {"skills": ["Python"]},
        "raw_text": "Synthetic resume evidence for Python.",
    })
    await db[Collections.PROFILES].insert_one({
        "user_id": USER_ID,
        "target_roles": ["Platform Engineer"],
        "experience_years": 2,
        "preferred_locations": [],
        "remote_preference": "any",
        "category": "EXPERIENCED",
    })

    app = FastAPI()
    app.include_router(jobs_router, prefix="/api/jobs")
    app.include_router(matching_router, prefix="/api/matches")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {"_id": USER_ID}
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(matching_services, "build_embedding_provider", lambda _: ExactMatchOnlyEmbedder())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        job_response = await api.get(f"/api/jobs/{JOB_ID}")
        assert job_response.status_code == 200
        job_payload = job_response.json()
        assert job_payload["jd_evidence_status"] == "COMPLETE"
        assert job_payload["skills_required"] == ["Python"]
        assert job_payload["skills_nice_to_have"] == ["Docker"]
        assert job_payload["url_type"] == "DIRECT_REQUISITION"
        assert job_payload["apply_url"] == sparse_listing["applyUrl"]

        single_job_response = await api.get(f"/api/matches/job/{JOB_ID}")
        assert single_job_response.status_code == 200
        single_job = single_job_response.json()
        assert single_job["status"] == "READY"
        assert single_job["resume_version"] == 1
        assert single_job["match"]["skill_score"] == 100
        assert single_job["match"]["overall_score"] < 100

        single_job_match_response = await api.get(f"/api/matches/job/{JOB_ID}")
        assert single_job_match_response.status_code == 200
        single_job_match = single_job_match_response.json()
        assert single_job_match["status"] == "READY"
        assert single_job_match["resume_version"] == 1
        assert single_job_match["match"]["skill_score"] == 100
        assert single_job_match["match"]["overall_score"] < 100

        first_matches_response = await api.get("/api/matches/recommended")
        assert first_matches_response.status_code == 200
        first_matches = {row["job_id"]: row for row in first_matches_response.json()}
        first_match = first_matches[JOB_ID]
        no_req_match = first_matches[no_requirements_id]
        assert first_match["skill_score"] == 100
        assert first_match["overall_score"] < 100
        assert "skills" in first_match["score_explanation"]
        assert first_match["jd_evidence_status"] == "COMPLETE"
        assert no_req_match["skill_score"] is None
        assert no_req_match["overall_score"] < 100
        assert "technical skill alignment is not scored" in no_req_match["score_explanation"].lower()

        cache_before = await db[Collections.JOB_MATCHES].find_one({"user_id": USER_ID, "job_id": JOB_ID})
        fingerprint_before = cache_before["job_fingerprint"]

        async def changed_detail(board: str, job_id: str):
            return {**sparse_listing, **_detail("Python\nKubernetes")}

        monkeypatch.setattr(provider, "fetch_company_openings", AsyncMock(return_value=[sparse_listing, no_requirements_listing]))
        monkeypatch.setattr(provider, "_fetch_detail_rate_limited", AsyncMock(side_effect=changed_detail))
        await provider.sync_company_openings(db, BOARD)

        second_matches_response = await api.get("/api/matches/recommended?search=Platform%20Engineer")
        assert second_matches_response.status_code == 200
        second_matches = {row["job_id"]: row for row in second_matches_response.json()}
        second_match = second_matches[JOB_ID]
        cache_after = await db[Collections.JOB_MATCHES].find_one({"user_id": USER_ID, "job_id": JOB_ID})
        assert cache_after["job_fingerprint"] != fingerprint_before
        assert second_match["skill_score"] == 50
        assert second_match["overall_score"] != first_match["overall_score"]

        detail_after_match = await api.get(f"/api/jobs/{JOB_ID}")
        assert detail_after_match.status_code == 200
        rendered_job = detail_after_match.json()
        assert rendered_job["match"]["skill_score"] == 50
        assert rendered_job["match"]["overall_score"] == second_match["overall_score"]
        assert rendered_job["match"]["score_explanation"] == second_match["score_explanation"]
        assert rendered_job["student_eligible"] is False

    assert await db[Collections.MASTER_RESUMES].count_documents({"user_id": USER_ID}) == 1
    assert await db[Collections.JOB_MATCHES].count_documents({"user_id": USER_ID}) == 2
    client.close()


@pytest.mark.asyncio
async def test_single_job_match_reports_resume_prerequisite_and_parse_failure(monkeypatch):
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["roleradar_single_job_match_states_test"]
    settings = Settings(EMBEDDING_PROVIDER="mock")
    job = {
        "id": "synthetic-backend-job",
        "user_id": USER_ID,
        "source": "custom",
        "title": "Backend Engineer",
        "company": "Synthetic Matching Lab",
        "description": "Build backend APIs with Python.",
        "jd_text": "Build backend APIs with Python.",
        "skills_required": ["Python"],
        "skills_nice_to_have": [],
        "job_type": "full_time",
        "location": "Bengaluru",
        "apply_url": "",
        "experience_min": None,
        "experience_max": None,
        "is_remote": False,
    }
    await db[Collections.JOBS].insert_one(job)

    app = FastAPI()
    app.include_router(matching_router, prefix="/api/matches")
    app.include_router(resume_router, prefix="/api/resumes")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {"_id": USER_ID}
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(matching_services, "build_embedding_provider", lambda _: ExactMatchOnlyEmbedder())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        missing = await api.get(f"/api/matches/job/{job['id']}")
        assert missing.status_code == 200
        assert missing.json()["status"] == "RESUME_REQUIRED"
        assert missing.json()["match"] is None

        parse_failure = await api.post(
            "/api/resumes/upload",
            files={"file": ("broken.pdf", b"not actually a pdf", "application/pdf")},
        )
        assert parse_failure.status_code == 422
        assert await db[Collections.MASTER_RESUMES].count_documents({"user_id": USER_ID}) == 0
        assert (await api.get(f"/api/matches/job/{job['id']}")).json()["status"] == "RESUME_REQUIRED"

        await db[Collections.MASTER_RESUMES].insert_one({
            "user_id": USER_ID,
            "version": 1,
            "is_active": True,
            "parsed": {},
            "raw_text": "  ",
        })
        unreadable = await api.get(f"/api/matches/job/{job['id']}")
        assert unreadable.status_code == 200
        assert unreadable.json()["status"] == "RESUME_UNREADABLE"
        assert unreadable.json()["match"] is None

    client.close()


@pytest.mark.asyncio
async def test_single_job_match_calculates_from_active_resume_and_returns_version(monkeypatch):
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["roleradar_single_job_match_compute_test"]
    settings = Settings(EMBEDDING_PROVIDER="mock")
    job = {
        "id": "synthetic-active-match-job",
        "user_id": USER_ID,
        "source": "custom",
        "title": "Backend Engineer",
        "company": "Synthetic Matching Lab",
        "description": "Build backend APIs with Python.",
        "jd_text": "Build backend APIs with Python.",
        "skills_required": ["Python"],
        "skills_nice_to_have": [],
        "job_type": "full_time",
        "location": "Bengaluru",
        "apply_url": "",
        "experience_min": None,
        "experience_max": None,
        "is_remote": False,
    }
    await db[Collections.JOBS].insert_one(job)
    await db[Collections.MASTER_RESUMES].insert_one({
        "user_id": USER_ID,
        "version": 7,
        "is_active": True,
        "parsed": {"skills": ["Python"]},
        "raw_text": "Synthetic resume evidence for Python.",
    })
    app = FastAPI()
    app.include_router(matching_router, prefix="/api/matches")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {"_id": USER_ID}
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(matching_services, "build_embedding_provider", lambda _: ExactMatchOnlyEmbedder())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        response = await api.get(f"/api/matches/job/{job['id']}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "READY"
        assert payload["resume_version"] == 7
        assert payload["match"]["skill_score"] == 100
        assert payload["match"]["overall_score"] < 100
        assert await db[Collections.JOB_MATCHES].count_documents({"user_id": USER_ID}) == 1

    client.close()


@pytest.mark.asyncio
async def test_single_job_match_distinguishes_missing_unreadable_and_valid_resume(monkeypatch):
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["roleradar_single_job_match_states_test"]
    settings = Settings(EMBEDDING_PROVIDER="mock")
    job = {
        "id": "synthetic-backend-job",
        "user_id": USER_ID,
        "source": "custom",
        "title": "Backend Engineer",
        "company": "Synthetic Matching Lab",
        "description": "Build backend APIs with Python.",
        "jd_text": "Build backend APIs with Python.",
        "skills_required": ["Python"],
        "skills_nice_to_have": [],
        "job_type": "full_time",
        "location": "Bengaluru",
        "apply_url": "",
        "experience_min": None,
        "experience_max": None,
        "is_remote": False,
    }
    await db[Collections.JOBS].insert_one(job)

    app = FastAPI()
    app.include_router(matching_router, prefix="/api/matches")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {"_id": USER_ID}
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(matching_services, "build_embedding_provider", lambda _: ExactMatchOnlyEmbedder())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        missing = await api.get(f"/api/matches/job/{job['id']}")
        assert missing.status_code == 200
        assert missing.json()["status"] == "RESUME_REQUIRED"
        assert missing.json()["match"] is None

        await db[Collections.MASTER_RESUMES].insert_one({
            "user_id": USER_ID,
            "version": 1,
            "is_active": True,
            "parsed": {},
            "raw_text": "  ",
        })
        unreadable = await api.get(f"/api/matches/job/{job['id']}")
        assert unreadable.status_code == 200
        assert unreadable.json()["status"] == "RESUME_UNREADABLE"
        assert unreadable.json()["match"] is None

        await db[Collections.MASTER_RESUMES].update_one(
            {"user_id": USER_ID},
            {"$set": {"parsed": {"skills": ["Python"]}, "raw_text": "Synthetic Python resume evidence."}},
        )
        readable = await api.get(f"/api/matches/job/{job['id']}")
        assert readable.status_code == 200
        assert readable.json()["status"] == "READY"
        assert readable.json()["match"]["skill_score"] == 100

    client.close()
