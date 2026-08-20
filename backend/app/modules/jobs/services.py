import json
import os
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.db.mongo import Collections
from app.modules.jobs import repositories as repo
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.skill_vocabulary import extract_skills_from_text

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "seeds", "jobs_seed.json")


async def ensure_seed_loaded(db: AsyncIOMotorDatabase) -> int:
    """Loads and syncs the seed dataset into MongoDB. Idempotent — safe to call on every app startup."""
    seed_path = os.path.abspath(SEED_PATH)
    if not os.path.exists(seed_path):
        return 0

    with open(seed_path) as f:
        jobs = json.load(f)

    if jobs:
        await repo.upsert_jobs(db, jobs)
    return len(jobs)


async def search_jobs(db: AsyncIOMotorDatabase, filters: dict) -> list[dict]:
    provider = CuratedJobProvider(db)
    return await provider.search(filters)


async def refresh_live_jobs(db: AsyncIOMotorDatabase, settings: Settings, filters: dict) -> int:
    """
    Fetches from Adzuna (if configured) and upserts results into the
    jobs collection so they show up in normal searches alongside
    curated data. Called explicitly from the jobs list route (a user
    actually visiting the Jobs page), not from every matching/dashboard
    read, to avoid hammering the external API on every page load
    (Feature 28: don't make unnecessary external calls).

    Fails silently (returns 0) if JOB_SOURCE_MODE isn't "hybrid" or
    Adzuna isn't configured -- this is the default, zero-config-required
    path and must never break the app for someone who hasn't set up a
    live job source.
    """
    if settings.JOB_SOURCE_MODE != "hybrid":
        return 0

    from app.modules.jobs.live_provider import AdzunaConfigError, AdzunaJobProvider

    try:
        provider = AdzunaJobProvider(settings)
    except AdzunaConfigError:
        return 0

    live_jobs = await provider.search(filters)
    if live_jobs:
        await repo.upsert_jobs(db, live_jobs)
    return len(live_jobs)


async def get_job(db: AsyncIOMotorDatabase, job_id: str) -> dict | None:
    return await repo.get_job_by_id(db, job_id)


async def create_custom_job(db: AsyncIOMotorDatabase, company: str, title: str, jd_text: str) -> dict:
    """
    Creates a job entry from a user-pasted JD, source="custom" (never
    presented as a curated/live listing). Required skills are extracted
    via a static vocabulary match (skill_vocabulary.py) -- deterministic,
    no LLM call. This lets a custom-pasted JD flow through the exact
    same matching/ATS/skill-gap/interview pipeline as a curated job,
    since everything downstream only needs a job_id.
    """
    skills = extract_skills_from_text(jd_text)
    job = {
        "id": f"custom_{uuid.uuid4().hex[:10]}",
        "source": "custom",
        "title": title,
        "company": company,
        "industry": "Unspecified",
        "description": jd_text,
        "jd_text": jd_text,
        "skills_required": skills[:6],
        "skills_nice_to_have": skills[6:12],
        "responsibilities": [],
        "experience_min": 0,
        "experience_max": 99,
        "job_type": "full_time",
        "location": "Not specified",
        "is_remote": False,
        "salary_min": None,
        "salary_max": None,
        "salary_disclosed": False,
        "stipend_min": None,
        "internship_duration_months": None,
        "fresher_friendly": True,
        "posted_days_ago": 0,
        # No apply_url for a custom/hypothetical JD -- there's no real
        # listing to apply to, and fabricating one would violate
        # Feature 8 (no fake functionality).
        "apply_url": "",
    }
    await db[Collections.JOBS].insert_one(job)
    return job
