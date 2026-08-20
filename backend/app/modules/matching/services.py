"""
Matching service orchestrating cached vs computed match scoring.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.embeddings.factory import build_embedding_provider
from app.modules.matching.engine import compute_match
from app.modules.matching import repositories as repo


async def get_or_compute_matches(
    db: AsyncIOMotorDatabase,
    user_id: str,
    resume: dict,
    profile: dict,
    jobs: list[dict],
    settings: Settings,
) -> list[dict]:
    """
    High-performance match resolver with caching.
    1. Looks up cached matches keyed by (user_id, resume_version, job_id).
    2. Only runs compute_match() on uncached / newly fetched jobs.
    3. Persists new matches to Collections.JOB_MATCHES.
    """
    if not jobs or not resume or not profile:
        return []

    resume_version = resume.get("version", 1)
    job_ids = [j["id"] for j in jobs]

    # 1. Fetch existing valid cache entries
    cached_map = await repo.get_cached_matches_for_jobs(db, user_id, resume_version, job_ids)

    candidate = {
        "skills": resume["parsed"].get("skills", []),
        "target_roles": profile.get("target_roles", []),
        "experience_years": profile.get("experience_years", 0),
        "preferred_locations": profile.get("preferred_locations", []),
        "remote_preference": profile.get("remote_preference", "any"),
        "min_lpa": profile.get("min_lpa"),
        "industries": profile.get("industries", []),
    }
    category = profile.get("category", "FRESHER")

    results = []
    uncached_jobs = []

    for job in jobs:
        j_id = job["id"]
        if j_id in cached_map:
            cached_data = cached_map[j_id]["match_data"]
            results.append({
                **cached_data,
                "job_title": job["title"],
                "company": job["company"],
                "job_type": job.get("job_type", "full_time"),
                "source": job.get("source", "curated"),
                "apply_url": job.get("apply_url", ""),
                "location": job.get("location", ""),
                "is_remote": job.get("is_remote", False),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "stipend_min": job.get("stipend_min"),
                "stipend_max": job.get("stipend_max"),
            })
        else:
            uncached_jobs.append(job)

    # 2. Compute only for missing / uncached jobs
    if uncached_jobs:
        embedder = build_embedding_provider(settings)
        newly_computed_to_cache = []

        for job in uncached_jobs:
            match = compute_match(candidate, job, embedder, category=category)
            match_data = {
                "job_id": job["id"],
                "overall_score": match.overall_score,
                "skill_score": match.skill_score,
                "role_score": match.role_score,
                "experience_score": match.experience_score,
                "location_score": match.location_score,
                "salary_score": match.salary_score,
                "industry_score": match.industry_score,
                "matched_skills": match.skill_match.matched,
                "partial_skills": match.skill_match.partial,
                "missing_skills": match.skill_match.missing,
                "apply_readiness": match.apply_readiness,
            }
            newly_computed_to_cache.append({
                "job_id": job["id"],
                "match_data": match_data,
            })
            results.append({
                **match_data,
                "job_title": job["title"],
                "company": job["company"],
                "job_type": job.get("job_type", "full_time"),
                "source": job.get("source", "curated"),
                "apply_url": job.get("apply_url", ""),
                "location": job.get("location", ""),
                "is_remote": job.get("is_remote", False),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "stipend_min": job.get("stipend_min"),
                "stipend_max": job.get("stipend_max"),
            })

        # 3. Cache newly computed matches
        await repo.save_cached_matches(db, user_id, resume_version, newly_computed_to_cache)

    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results
