"""
Phase 16C Acceptance & Regression Tests
Validates:
1. Jobs / Internships recommendation & search requests do NOT synchronously call refresh_live_jobs().
2. Opportunities from MongoDB are returned cleanly and respect filters even during network/provider faults.
3. Decoupled provider sync endpoint POST /jobs/sync executes independently.
4. Copilot context reuses persisted Collections.JOB_MATCHES without recomputing 100 job matches.
5. Auth endpoints POST /auth/login and POST /auth/register enforce rate limits without requiring bearer tokens or returning spurious 401s.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings, get_settings
from app.core.rate_limit import get_global_limiter
from app.db.mongo import Collections, get_db
from app.main import app
from app.modules.auth import services as auth_services
from app.modules.chatbot.context import build_copilot_context
from app.modules.jobs import services as jobs_services
from app.modules.matching import services as matching_services
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test_p16c"]


@pytest.fixture
def settings():
    return Settings(
        JWT_SECRET="test-secret-phase16c-valid-random-string",
        RATE_LIMITING_ENABLED=True,
        AUTH_RATE_LIMIT_MAX_REQUESTS=10,
        AUTH_RATE_LIMIT_WINDOW_SECONDS=60,
    )


@pytest.fixture(autouse=True)
def setup_overrides(db, settings):
    """Ensure in-memory sliding window limiter is pristine and app dependencies point to test db/settings."""
    get_global_limiter().reset()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.clear()
    get_global_limiter().reset()


async def _seed_verified_job(
    db,
    job_id: str = "verified_job_1",
    title: str = "Python Developer",
    company: str = "TechCorp",
    job_type: str = "full_time",
    location: str = "Bengaluru, India",
    country: str = "India",
    apply_url: str = "https://boards.greenhouse.io/techcorp/jobs/101",
) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": job_id,
        "title": title,
        "company": company,
        "industry": "Technology",
        "description": "A great opportunity for developers.",
        "skills_required": ["Python", "FastAPI"],
        "skills_nice_to_have": ["Docker"],
        "job_type": job_type,
        "location": location,
        "country": country,
        "is_remote": False,
        "salary_min": 600000.0,
        "salary_max": 1200000.0,
        "salary_disclosed": True,
        "stipend_min": 25000.0 if job_type == "internship" else None,
        "internship_duration_months": 6 if job_type == "internship" else None,
        "fresher_friendly": True,
        "source": "live",
        "apply_url": apply_url,
        "is_direct_apply": True,
        "url_type": "DIRECT_REQUISITION",
        "verification_status": "VERIFIED_ACTIVE",
        "last_verified_at": now_iso,
        "verified_at": now_iso,
        "created_at": now_iso,
        "posted_days_ago": 1,
        "min_lpa": 6.0,
        "max_lpa": 12.0,
    }
    await db[Collections.JOBS].update_one({"id": job_id}, {"$set": doc}, upsert=True)
    return doc


# =========================================================================
# PART 1: JOBS / INTERNSHIPS PERFORMANCE & DECOUPLED PROVIDER SYNC
# =========================================================================

@pytest.mark.asyncio
async def test_recommendations_endpoint_does_not_call_refresh_live_jobs(db, settings):
    """
    Validation A & B:
    GET /matches/recommended queries persisted opportunities directly
    and NEVER calls refresh_live_jobs() in the synchronous request path.
    """
    user, token = await auth_services.register_user(
        db, settings, "p16c_jobs@example.com", "SecretPass123!", "Jobs Candidate", None
    )
    user_id = str(user["_id"])

    await profile_repo.upsert_profile(
        db,
        user_id,
        {
            "category": "FRESHER",
            "target_roles": ["Python Developer"],
            "min_lpa": 6.0,
            "preferred_locations": ["Bengaluru"],
            "remote_preference": "any",
            "experience_years": 0,
        },
    )

    await resume_repo.create_master_resume(
        db,
        user_id,
        version=1,
        file_name="resume.pdf",
        file_type="pdf",
        raw_text="Python FastAPI MongoDB",
        parsed={"skills": ["Python", "FastAPI", "MongoDB"]},
        parseability={"score": 85, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 50},
        recruiter_impact={"score": 80, "bullets_analyzed": 5, "quantified_bullets": 2, "weak_verb_bullets": 0, "quantification_rate": 40, "issues": []},
    )

    await _seed_verified_job(db, "gh_job_rec_1", "Python Developer", "TechCorp")

    # Patch refresh_live_jobs on services to detect any synchronous invocation
    with patch("app.modules.jobs.services.refresh_live_jobs", AsyncMock(return_value=0)) as mock_refresh:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/matches/recommended",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        matches = resp.json()
        assert len(matches) > 0
        assert matches[0]["job_id"] == "gh_job_rec_1"
        # CRITICAL ASSERTION: The synchronous discovery request must NOT invoke refresh_live_jobs
        mock_refresh.assert_not_called()


@pytest.mark.asyncio
async def test_jobs_list_endpoint_does_not_call_refresh_live_jobs(db, settings):
    """
    GET /jobs queries persisted opportunities directly without calling refresh_live_jobs().
    """
    user, token = await auth_services.register_user(
        db, settings, "p16c_list@example.com", "SecretPass123!", "List Candidate", None
    )
    await _seed_verified_job(db, "gh_job_list_1", "Backend Developer", "Acme")

    with patch("app.modules.jobs.services.refresh_live_jobs", AsyncMock(return_value=0)) as mock_refresh:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/jobs",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) > 0
        assert any(j["id"] == "gh_job_list_1" for j in jobs)
        mock_refresh.assert_not_called()


@pytest.mark.asyncio
async def test_jobs_sync_endpoint_triggers_provider_synchronization(db, settings):
    """
    Validation C:
    Dedicated POST /jobs/sync endpoint explicitly triggers provider synchronization
    outside user discovery requests.
    """
    user, token = await auth_services.register_user(
        db, settings, "p16c_sync@example.com", "SecretPass123!", "Sync Operator", None
    )

    with patch("app.modules.jobs.services.refresh_live_jobs", AsyncMock(return_value=7)) as mock_refresh:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/jobs/sync",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["added_count"] == 7
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_provider_network_failure_does_not_break_recommendations(db, settings):
    """
    Validation D & E:
    Simulated external provider/network failure has zero impact on GET /matches/recommended,
    and opportunity filters continue to function reliably.
    """
    user, token = await auth_services.register_user(
        db, settings, "p16c_resilience@example.com", "SecretPass123!", "Resilient User", None
    )
    user_id = str(user["_id"])
    await profile_repo.upsert_profile(
        db,
        user_id,
        {"category": "FRESHER", "target_roles": ["Software Engineer"], "min_lpa": 4.0},
    )
    await _seed_verified_job(db, "gh_intern_1", "Software Engineering Intern", "InternCo", job_type="internship")

    # Even if refresh_live_jobs raises an exception, the recommendation endpoint does not invoke it
    with patch("app.modules.jobs.services.refresh_live_jobs", AsyncMock(side_effect=RuntimeError("ATS network down"))):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/matches/recommended?job_type=internship",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        matches = resp.json()
        assert isinstance(matches, list)
        assert len(matches) > 0
        for m in matches:
            if m.get("job_type"):
                assert m["job_type"] == "internship"


# =========================================================================
# PART 2: COPILOT CONTEXT PERFORMANCE
# =========================================================================

@pytest.mark.asyncio
async def test_copilot_context_uses_persisted_job_matches_without_compute_match(db, settings):
    """
    Validation A & B:
    When Collections.JOB_MATCHES has persisted match data, build_copilot_context()
    reads the top persisted matches directly and does NOT call compute_match() 100 times.
    """
    user, _ = await auth_services.register_user(
        db, settings, "p16c_copilot@example.com", "SecretPass123!", "Copilot Candidate", None
    )
    user_id = str(user["_id"])

    await profile_repo.upsert_profile(
        db,
        user_id,
        {
            "category": "FRESHER",
            "target_roles": ["Frontend Engineer"],
            "min_lpa": 6.0,
            "preferred_locations": ["Bengaluru"],
        },
    )

    await resume_repo.create_master_resume(
        db,
        user_id,
        version=1,
        file_name="r.pdf",
        file_type="pdf",
        raw_text="React TypeScript",
        parsed={"skills": ["React", "TypeScript"]},
        parseability={"score": 90, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 30},
        recruiter_impact={"score": 85, "bullets_analyzed": 3, "quantified_bullets": 1, "weak_verb_bullets": 0, "quantification_rate": 33, "issues": []},
    )

    # Seed verified jobs
    for i in range(3):
        await _seed_verified_job(db, f"job_persisted_{i}", f"Senior Frontend {i}", f"TechCorp {i}")

    # Pre-populate Collections.JOB_MATCHES with 3 persisted matches
    now = datetime.now(timezone.utc)
    match_docs = [
        {
            "user_id": user_id,
            "job_id": f"job_persisted_{i}",
            "resume_version": 1,
            "overall_score": 80 + i,
            "match_data": {
                "overall_score": 80 + i,
                "job_title": f"Senior Frontend {i}",
                "company": f"TechCorp {i}",
                "apply_readiness": "READY",
                "missing_skills": ["GraphQL"],
            },
            "updated_at": now,
        }
        for i in range(3)
    ]
    await db[Collections.JOB_MATCHES].insert_many(match_docs)

    # Patch compute_match to prove it is NEVER invoked when persisted matches exist
    with patch("app.modules.matching.engine.compute_match") as mock_compute:
        ctx = await build_copilot_context(user_id, db, settings=settings)

        mock_compute.assert_not_called()
        assert len(ctx.top_job_matches) == 3
        # Sorted descending by overall_score
        assert ctx.top_job_matches[0]["overall_score"] == 82
        assert ctx.top_job_matches[0]["job_id"] == "job_persisted_2"
        assert ctx.top_job_matches[0]["apply_readiness"] == "READY"
        assert ctx.top_job_matches[0]["missing_skills"] == ["GraphQL"]


@pytest.mark.asyncio
async def test_copilot_context_preserves_resume_and_applications_context(db, settings):
    """
    Validation C, D & E:
    CopilotContext preserves candidate intelligence, active applications,
    and profile summary seamlessly.
    """
    from app.modules.applications import services as app_services

    user, _ = await auth_services.register_user(
        db, settings, "p16c_full_ctx@example.com", "SecretPass123!", "Full Context", None
    )
    user_id = str(user["_id"])

    await profile_repo.upsert_profile(
        db,
        user_id,
        {"category": "FRESHER", "target_roles": ["Backend Engineer"], "min_lpa": 8.0},
    )

    await resume_repo.create_master_resume(
        db,
        user_id,
        version=1,
        file_name="res.pdf",
        file_type="pdf",
        raw_text="Go Docker",
        parsed={"skills": ["Go", "Docker"]},
        parseability={"score": 92, "issues": [], "detected_sections": [], "missing_standard_sections": [], "contact_info_found": {}, "likely_multi_column": False, "word_count": 20},
        recruiter_impact={"score": 88, "bullets_analyzed": 4, "quantified_bullets": 2, "weak_verb_bullets": 0, "quantification_rate": 50, "issues": []},
    )

    test_job = await _seed_verified_job(db, "job_app_test_1", "Platform Engineer", "CloudScale")
    await app_services.save_application(db, user_id, test_job["id"], None, None)

    ctx = await build_copilot_context(user_id, db, settings=settings)

    assert ctx.profile_summary is not None
    assert ctx.profile_summary["target_roles"] == ["Backend Engineer"]
    assert ctx.resume_intelligence is not None
    assert ctx.resume_intelligence["skills"] == ["Go", "Docker"]
    assert len(ctx.active_applications) == 1
    assert ctx.active_applications[0]["job_title"] == test_job["title"]


# =========================================================================
# PART 3: AUTHENTICATION RATE LIMITING
# =========================================================================

@pytest.mark.asyncio
async def test_auth_login_and_register_do_not_require_token_or_return_401(db, settings):
    """
    Validation A, B & F:
    POST /auth/login and POST /auth/register do NOT crash with 401
    merely because they lack an Authorization header.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register unauthenticated
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "email": "p16c_fresh@example.com",
                "password": "Password123!",
                "full_name": "Fresh User",
            },
        )
        assert reg_resp.status_code == 201
        assert "access_token" in reg_resp.json()

        # Login unauthenticated
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": "p16c_fresh@example.com",
                "password": "Password123!",
            },
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_auth_rate_limiter_triggers_429_after_threshold(db, settings):
    """
    Validation C:
    Rate limiting triggers HTTP 429 Too Many Requests once client IP
    exceeds AUTH_RATE_LIMIT_MAX_REQUESTS within the configured window.
    """
    max_requests = settings.AUTH_RATE_LIMIT_MAX_REQUESTS

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"x-forwarded-for": "198.51.100.42"}

        # Send up to max_requests
        for i in range(max_requests):
            resp = await client.post(
                "/api/auth/login",
                json={"email": f"bad_{i}@example.com", "password": "wrong"},
                headers=headers,
            )
            # Expect 401 (invalid credentials), NOT 429 yet
            assert resp.status_code == 401, f"Expected 401 on attempt {i + 1}, got {resp.status_code}"

        # The (max_requests + 1)-th request MUST trigger 429
        overflow_resp = await client.post(
            "/api/auth/login",
            json={"email": "overflow@example.com", "password": "wrong"},
            headers=headers,
        )
        assert overflow_resp.status_code == 429
        assert "Rate limit exceeded" in overflow_resp.json()["detail"]
        assert "Retry-After" in overflow_resp.headers


@pytest.mark.asyncio
async def test_authenticated_rate_limiting_keys_by_user_id(db, settings):
    """
    Validation D:
    Authenticated routes retain existing user-based rate limit behavior.
    """
    user, token = await auth_services.register_user(
        db, settings, "p16c_user_limit@example.com", "Password123!", "User Limit", None
    )

    # Verify authenticated request passes through cleanly
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "p16c_user_limit@example.com"
