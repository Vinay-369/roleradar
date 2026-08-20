import pytest
from mongomock_motor import AsyncMongoMockClient
from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.matching.services import get_or_compute_matches
from app.modules.matching import repositories as matching_repo


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.fixture
def sample_candidate():
    return {
        "resume": {
            "version": 1,
            "parsed": {
                "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
            },
        },
        "profile": {
            "target_roles": ["Backend Developer"],
            "experience_years": 1,
            "category": "FRESHER",
        },
    }


@pytest.fixture
def sample_jobs():
    return [
        {
            "id": "job_1",
            "title": "Python Developer",
            "company": "TechCorp",
            "skills_required": ["Python", "FastAPI"],
            "skills_nice_to_have": ["Docker"],
            "job_type": "full_time",
            "source": "curated",
            "apply_url": "https://example.com/apply1",
        },
        {
            "id": "job_2",
            "title": "Backend Engineer",
            "company": "DataSys",
            "skills_required": ["Python", "PostgreSQL"],
            "skills_nice_to_have": ["Kubernetes"],
            "job_type": "full_time",
            "source": "curated",
            "apply_url": "https://example.com/apply2",
        },
    ]


@pytest.mark.asyncio
async def test_first_call_computes_and_caches_matches(db, sample_candidate, sample_jobs):
    settings = Settings(EMBEDDING_PROVIDER="sentence_transformer")
    user_id = "user_123"

    # Initial state: cache is empty
    count_before = await db[Collections.JOB_MATCHES].count_documents({"user_id": user_id})
    assert count_before == 0

    results = await get_or_compute_matches(
        db, user_id, sample_candidate["resume"], sample_candidate["profile"], sample_jobs, settings
    )

    assert len(results) == 2
    # Verify cached in database
    count_after = await db[Collections.JOB_MATCHES].count_documents({"user_id": user_id})
    assert count_after == 2


@pytest.mark.asyncio
async def test_subsequent_call_uses_cache_without_calling_compute_match(db, sample_candidate, sample_jobs, monkeypatch):
    settings = Settings(EMBEDDING_PROVIDER="sentence_transformer")
    user_id = "user_123"

    # First call: computes and caches
    await get_or_compute_matches(
        db, user_id, sample_candidate["resume"], sample_candidate["profile"], sample_jobs, settings
    )

    # Mock compute_match to raise error if called
    def fail_if_computed(*args, **kwargs):
        raise AssertionError("compute_match should NOT be called for cached jobs!")

    monkeypatch.setattr("app.modules.matching.services.compute_match", fail_if_computed)

    # Second call: must retrieve from cache cleanly without error
    cached_results = await get_or_compute_matches(
        db, user_id, sample_candidate["resume"], sample_candidate["profile"], sample_jobs, settings
    )

    assert len(cached_results) == 2
    assert cached_results[0]["job_id"] in ["job_1", "job_2"]


@pytest.mark.asyncio
async def test_partial_cache_computes_only_newly_added_jobs(db, sample_candidate, sample_jobs, monkeypatch):
    settings = Settings(EMBEDDING_PROVIDER="sentence_transformer")
    user_id = "user_123"

    # Cache job_1 first
    await get_or_compute_matches(
        db, user_id, sample_candidate["resume"], sample_candidate["profile"], [sample_jobs[0]], settings
    )

    computed_call_count = 0
    from app.modules.matching.engine import compute_match as real_compute_match

    def counting_compute_match(*args, **kwargs):
        nonlocal computed_call_count
        computed_call_count += 1
        return real_compute_match(*args, **kwargs)

    monkeypatch.setattr("app.modules.matching.services.compute_match", counting_compute_match)

    # Request both job_1 (cached) and job_2 (new)
    results = await get_or_compute_matches(
        db, user_id, sample_candidate["resume"], sample_candidate["profile"], sample_jobs, settings
    )

    assert len(results) == 2
    # Only job_2 should have triggered compute_match
    assert computed_call_count == 1


@pytest.mark.asyncio
async def test_cache_invalidation(db, sample_candidate, sample_jobs):
    settings = Settings(EMBEDDING_PROVIDER="sentence_transformer")
    user_id = "user_123"

    await get_or_compute_matches(
        db, user_id, sample_candidate["resume"], sample_candidate["profile"], sample_jobs, settings
    )
    assert await db[Collections.JOB_MATCHES].count_documents({"user_id": user_id}) == 2

    # Invalidate cache
    await matching_repo.invalidate_user_matches(db, user_id)
    assert await db[Collections.JOB_MATCHES].count_documents({"user_id": user_id}) == 0
