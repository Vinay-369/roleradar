import pytest
from mongomock_motor import AsyncMongoMockClient

from app.modules.jobs import services as jobs_services
from app.modules.jobs.providers import CuratedJobProvider


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_test"]


@pytest.mark.asyncio
async def test_seed_loads_curated_jobs(db):
    count = await jobs_services.ensure_seed_loaded(db)
    assert count > 0
    total_in_db = await db["jobs"].count_documents({})
    assert total_in_db == count


@pytest.mark.asyncio
async def test_seed_is_idempotent(db):
    first = await jobs_services.ensure_seed_loaded(db)
    second = await jobs_services.ensure_seed_loaded(db)
    assert second == first  # second call is a no-op, doesn't duplicate


@pytest.mark.asyncio
async def test_curated_provider_filters_by_job_type(db):
    await jobs_services.ensure_seed_loaded(db)
    provider = CuratedJobProvider(db)
    internships = await provider.search({"job_type": "internship"})
    assert len(internships) > 0
    assert all(j["job_type"] == "internship" for j in internships)


@pytest.mark.asyncio
async def test_every_seeded_job_discloses_curated_source(db):
    await jobs_services.ensure_seed_loaded(db)
    provider = CuratedJobProvider(db)
    jobs = await provider.search({})
    assert len(jobs) > 0
    assert all(bool(j.get("apply_url")) for j in jobs)
