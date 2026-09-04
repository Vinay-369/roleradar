"""
Phase 9 Stage B: Production Hardening & Security Regression Test Suite.
Tests SEC-01 through SEC-07 remediations.
"""
import io
import pytest
from mongomock_motor import AsyncMongoMockClient
from pydantic import ValidationError
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import Settings
from app.core.rate_limit import InMemorySlidingWindowLimiter
from app.db.mongo import Collections, ensure_indexes
from app.modules.auth import services as auth_services
from app.modules.chatbot.schemas import ChatRequest
from app.modules.profile import services as profile_services
from app.modules.profile.schemas import CandidateCategory, OnboardingRequest
from app.modules.resume import services as resume_services
from app.modules.tailoring.schemas import GenerateTailoringRequest


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


def _make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(50, 750, text)
    c.save()
    return buf.getvalue()


# ===========================================================================
# SEC-01: Production JWT Secret Enforcement
# ===========================================================================
def test_sec01_production_rejects_default_jwt_secret():
    with pytest.raises(ValueError, match="Production configuration error"):
        Settings(ENV="production", JWT_SECRET="change-me-in-env")

    with pytest.raises(ValueError, match="Production configuration error"):
        Settings(ENV="production", JWT_SECRET="replace-with-a-long-random-string")

    with pytest.raises(ValueError, match="Production configuration error"):
        Settings(ENV="production", JWT_SECRET="")

    with pytest.raises(ValueError, match="Production configuration error"):
        Settings(ENV="production", JWT_SECRET="short_secret")


def test_sec01_production_accepts_strong_jwt_secret():
    s = Settings(ENV="production", JWT_SECRET="a_strong_and_secure_random_production_secret_2026")
    assert s.JWT_SECRET == "a_strong_and_secure_random_production_secret_2026"


def test_sec01_development_allows_default_secret():
    s = Settings(ENV="development", JWT_SECRET="change-me-in-env")
    assert s.JWT_SECRET == "change-me-in-env"


# ===========================================================================
# SEC-02: Rate Limiting
# ===========================================================================
def test_sec02_rate_limiter_allows_under_limit_and_blocks_over_limit():
    limiter = InMemorySlidingWindowLimiter()
    key = "user_test_123"

    # Limit: 3 requests per 60 seconds
    for _ in range(3):
        allowed, _ = limiter.is_allowed(key, max_requests=3, window_seconds=60)
        assert allowed is True

    # 4th request must be rejected
    allowed, retry_after = limiter.is_allowed(key, max_requests=3, window_seconds=60)
    assert allowed is False
    assert retry_after > 0


def test_sec02_rate_limiter_isolates_different_users():
    limiter = InMemorySlidingWindowLimiter()
    user_a = "user_a"
    user_b = "user_b"

    # User A exhausts their limit
    for _ in range(2):
        limiter.is_allowed(user_a, max_requests=2, window_seconds=60)
    allowed_a, _ = limiter.is_allowed(user_a, max_requests=2, window_seconds=60)
    assert allowed_a is False

    # User B should still be allowed
    allowed_b, _ = limiter.is_allowed(user_b, max_requests=2, window_seconds=60)
    assert allowed_b is True


# ===========================================================================
# SEC-03: Upload Filename Sanitization
# ===========================================================================
@pytest.mark.asyncio
async def test_sec03_upload_sanitizes_path_traversal_filenames(db):
    settings = Settings(JWT_SECRET="test-secret")
    user, _ = await auth_services.register_user(db, settings, "sec03@example.com", "Password123!", "Sec Tester", None)
    user_id = str(user["_id"])

    pdf_bytes = _make_pdf("Security Resume Content\nSkills: Python, Docker")

    # Traversal filename 1
    doc1 = await resume_services.ingest_resume(db, settings, user_id, "../../../../etc/passwd.pdf", pdf_bytes)
    assert doc1["file_name"] == "passwd.pdf"
    assert "/" not in doc1["file_name"]
    assert "\\" not in doc1["file_name"]

    # Traversal filename 2
    doc2 = await resume_services.ingest_resume(db, settings, user_id, "..\\..\\windows\\system32.pdf", pdf_bytes)
    assert doc2["file_name"] == "system32.pdf"
    assert "\\" not in doc2["file_name"]


# ===========================================================================
# SEC-04: Numeric Input Validation Bounds
# ===========================================================================
def test_sec04_onboarding_rejects_negative_numerics():
    with pytest.raises(ValidationError):
        OnboardingRequest(
            category=CandidateCategory.EXPERIENCED,
            experience_years=-5.0,
            target_roles=["Backend Developer"],
            consent_text="consent"
        )

    with pytest.raises(ValidationError):
        OnboardingRequest(
            category=CandidateCategory.INTERNSHIP_SEEKER,
            min_stipend=-10000,
            target_roles=["Backend Developer"],
            consent_text="consent"
        )

    with pytest.raises(ValidationError):
        OnboardingRequest(
            category=CandidateCategory.FRESHER,
            cgpa=11.5,  # Exceeds max 10.0
            target_roles=["Backend Developer"],
            consent_text="consent"
        )


def test_sec04_onboarding_accepts_valid_numerics():
    req = OnboardingRequest(
        category=CandidateCategory.INTERNSHIP_SEEKER,
        min_stipend=25000,
        internship_duration_months=6,
        cgpa=8.8,
        target_roles=["Backend Developer"],
        consent_text="consent"
    )
    assert req.min_stipend == 25000.0
    assert req.internship_duration_months == 6
    assert req.cgpa == 8.8


# ===========================================================================
# SEC-05: Bounded Large Text Inputs
# ===========================================================================
def test_sec05_tailoring_request_rejects_oversized_jd():
    with pytest.raises(ValidationError):
        GenerateTailoringRequest(
            custom_company="Corp",
            custom_role_title="Dev",
            custom_jd_text="A" * 60_000  # Exceeds 50,000 limit
        )


def test_sec05_copilot_request_rejects_oversized_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="A" * 5000)  # Exceeds 4000 limit


def test_sec05_accepts_realistic_lengths():
    req = GenerateTailoringRequest(
        custom_company="TechCorp",
        custom_role_title="Senior Engineer",
        custom_jd_text="Requirements: Python, FastAPI, Docker, Kubernetes"
    )
    assert req.custom_company == "TechCorp"

    chat_req = ChatRequest(message="Can you help tailor my summary for this job?")
    assert len(chat_req.message) > 0


# ===========================================================================
# SEC-06: Secondary MongoDB Indexes
# ===========================================================================
@pytest.mark.asyncio
async def test_sec06_ensure_indexes_creates_secondary_indexes(db):
    await ensure_indexes(db)

    # Verify user_id index exists on secondary collections
    profiles_indexes = await db[Collections.PROFILES].index_information()
    assert any("user_id" in str(idx["key"]) for idx in profiles_indexes.values())

    achievements_indexes = await db[Collections.ACHIEVEMENTS].index_information()
    assert any("user_id" in str(idx["key"]) for idx in achievements_indexes.values())

    chat_indexes = await db[Collections.CHAT_CONVERSATIONS].index_information()
    assert any("user_id" in str(idx["key"]) for idx in chat_indexes.values())


# ===========================================================================
# SEC-07: Account / User Data Deletion
# ===========================================================================
@pytest.mark.asyncio
async def test_sec07_account_purge_cascades_and_preserves_other_users(db):
    settings = Settings(JWT_SECRET="test-secret")

    # 1. Create User A (to be deleted)
    user_a, _ = await auth_services.register_user(db, settings, "purge_a@example.com", "Password123!", "User A", None)
    user_a_id = str(user_a["_id"])
    await profile_services.complete_onboarding(db, user_a_id, OnboardingRequest(
        category=CandidateCategory.FRESHER,
        target_roles=["Full Stack Developer"],
        consent_text="consent"
    ))
    pdf_bytes = _make_pdf("User A Resume")
    await resume_services.ingest_resume(db, settings, user_a_id, "resume_a.pdf", pdf_bytes)

    # 2. Create User B (must be preserved)
    user_b, _ = await auth_services.register_user(db, settings, "preserve_b@example.com", "Password123!", "User B", None)
    user_b_id = str(user_b["_id"])
    await profile_services.complete_onboarding(db, user_b_id, OnboardingRequest(
        category=CandidateCategory.EXPERIENCED,
        target_roles=["Senior Engineer"],
        consent_text="consent"
    ))

    # 3. Create global curated job
    await db[Collections.JOBS].insert_one({
        "job_id": "curated_job_999",
        "title": "Global Job Title",
        "company": "Global Company",
        "skills": ["Python"]
    })

    # Verify initial existence
    assert await db[Collections.PROFILES].find_one({"user_id": user_a_id}) is not None
    assert await db[Collections.MASTER_RESUMES].find_one({"user_id": user_a_id}) is not None
    assert await db[Collections.PROFILES].find_one({"user_id": user_b_id}) is not None

    # 4. Execute User A Purge
    res = await profile_services.purge_user_account_data(db, user_a_id)
    assert res["status"] == "deleted"

    # 5. Verify User A data is completely purged
    assert await db[Collections.USERS].find_one({"_id": user_a["_id"]}) is None
    assert await db[Collections.PROFILES].find_one({"user_id": user_a_id}) is None
    assert await db[Collections.MASTER_RESUMES].find_one({"user_id": user_a_id}) is None

    # 6. Verify User B data is 100% intact
    assert await db[Collections.USERS].find_one({"_id": user_b["_id"]}) is not None
    assert await db[Collections.PROFILES].find_one({"user_id": user_b_id}) is not None

    # 7. Verify global curated job is untouched
    curated_job = await db[Collections.JOBS].find_one({"job_id": "curated_job_999"})
    assert curated_job is not None
    assert curated_job["title"] == "Global Job Title"
