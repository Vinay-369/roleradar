"""
Matching service orchestrating cached vs computed match scoring.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.embeddings.factory import build_embedding_provider
from app.modules.matching.engine import compute_match
from app.modules.matching import repositories as repo


def build_india_metadata(
    job: dict,
    profile: dict | None = None,
    resume: dict | None = None,
    skill_score: int | None = None,
) -> dict:
    from app.modules.jobs.classification import classify_opportunity
    from app.modules.jobs.location_normalization import normalize_india_location, detect_workplace_type, extract_country_from_location
    from app.modules.jobs.eligibility import evaluate_eligibility

    title = job.get("title", "")
    desc = job.get("description", "")
    exp_min = job.get("experience_min")
    exp_max = job.get("experience_max")
    job_type = job.get("job_type", "full_time")
    location = job.get("location")
    is_remote = job.get("is_remote", False)

    classification = classify_opportunity(title, desc, exp_min, exp_max, job_type)
    eligibility = evaluate_eligibility(profile, resume, job, skill_score=skill_score)

    stipend_val = job.get("stipend") or job.get("stipend_min")
    stipend_currency = job.get("stipend_currency") or ("INR" if stipend_val else None)
    stipend_period = job.get("stipend_period") or ("per_month" if stipend_val else None)

    derived_country = job.get("country") or extract_country_from_location(location)

    return {
        "country": derived_country,
        "opportunity_type": classification.opportunity_type.value,
        "candidate_suitability": classification.suitability.value,
        "student_eligible": classification.student_eligible,
        "fresher_eligible": classification.fresher_eligible,
        "stipend": stipend_val,
        "stipend_currency": stipend_currency,
        "stipend_period": stipend_period,
        "salary_currency": job.get("salary_currency", "INR"),
        "compensation_type": job.get("compensation_type"),
        "compensation_text": job.get("compensation_text"),
        "eligibility_text": eligibility.reasons[0] if eligibility.reasons else None,
        "degree_requirements": classification.degree_requirements,
        "graduation_year_requirements": classification.graduation_year_requirements,
        "workplace_type": detect_workplace_type(location, desc, is_remote),
        "normalized_location": normalize_india_location(location),
        "eligibility": eligibility.model_dump(mode="json"),
        "realistic_fit": eligibility.realistic_fit.value,
        "fit_explanation": eligibility.fit_explanation,
    }


_build_india_metadata = build_india_metadata


def _get_role_metadata(job: dict) -> dict:
    from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role
    title = job.get("title") or ""
    prof, _, _ = resolve_role(title)
    if prof:
        canon_role = prof.canonical_role
        canon_key = None
        for k, p in ROLE_TAXONOMY.items():
            if p.canonical_role == prof.canonical_role:
                canon_key = k
                break
        return {
            "canonical_role": canon_role,
            "canonical_role_key": canon_key,
            "role_domain": prof.domain,
        }
    return {
        "canonical_role": title or None,
        "canonical_role_key": None,
        "role_domain": job.get("industry") or "Technology",
    }


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

    from app.modules.resume.models import CandidateProfile
    cand_profile = CandidateProfile.from_parsed_dict(resume.get("parsed") or {}, resume.get("raw_text", ""))
    canonical_skills = cand_profile.get_all_demonstrated_skills()

    candidate = {
        "skills": canonical_skills,
        "target_roles": profile.get("target_roles", []),
        "experience_years": profile.get("experience_years", 0),
        "preferred_locations": profile.get("preferred_locations", []),
        "remote_preference": profile.get("remote_preference", "any"),
        "min_lpa": profile.get("min_lpa"),
        "min_stipend": profile.get("min_stipend"),
        "industries": profile.get("industries", []),
    }
    category = profile.get("category", "FRESHER")

    results = []
    uncached_jobs = []

    for job in jobs:
        j_id = job["id"]
        created_val = job.get("created_at") or job.get("created")
        created_str = created_val.isoformat() if hasattr(created_val, "isoformat") else (str(created_val) if created_val else "")

        if j_id in cached_map:
            cached_data = cached_map[j_id]["match_data"]
            india_meta = _build_india_metadata(job, skill_score=cached_data.get("skill_score"))
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
                "posted_days_ago": job.get("posted_days_ago", 0),
                "created_at": created_str,
                "skills_required": job.get("skills_required", []),
                "has_match": True,
                "source_job_id": job.get("source_job_id"),
                "source_url": job.get("source_url"),
                "verification_status": job.get("verification_status", "VERIFIED_ACTIVE"),
                "verified_at": job.get("verified_at"),
                "last_verified_at": job.get("last_verified_at") or job.get("verified_at"),
                "verification_reason": job.get("verification_reason"),
                "verification_method": job.get("verification_method"),
                "url_type": job.get("url_type", "UNVERIFIED"),
                "is_direct_apply": job.get("is_direct_apply", job.get("url_type") == "DIRECT_REQUISITION"),
                "posted_at": job.get("posted_at"),
                "quality_tier": job.get("quality_tier", "PRIMARY"),
                "role_confidence": job.get("role_confidence"),
                "contextual_requirements": job.get("contextual_requirements", []),
                **_get_role_metadata(job),
                **india_meta,
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
                "factor_weights": match.factor_weights,
                "score_explanation": match.score_explanation,
            }
            newly_computed_to_cache.append({
                "job_id": job["id"],
                "match_data": match_data,
            })
            created_val = job.get("created_at") or job.get("created")
            created_str = created_val.isoformat() if hasattr(created_val, "isoformat") else (str(created_val) if created_val else "")

            india_meta = _build_india_metadata(job, skill_score=match.skill_score)
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
                "posted_days_ago": job.get("posted_days_ago", 0),
                "created_at": created_str,
                "skills_required": job.get("skills_required", []),
                "has_match": True,
                "source_job_id": job.get("source_job_id"),
                "source_url": job.get("source_url"),
                "verification_status": job.get("verification_status", "VERIFIED_ACTIVE"),
                "verified_at": job.get("verified_at"),
                "last_verified_at": job.get("last_verified_at") or job.get("verified_at"),
                "verification_reason": job.get("verification_reason"),
                "verification_method": job.get("verification_method"),
                "url_type": job.get("url_type", "UNVERIFIED"),
                "is_direct_apply": job.get("is_direct_apply", job.get("url_type") == "DIRECT_REQUISITION"),
                "posted_at": job.get("posted_at"),
                "quality_tier": job.get("quality_tier", "PRIMARY"),
                "role_confidence": job.get("role_confidence"),
                "contextual_requirements": job.get("contextual_requirements", []),
                **_get_role_metadata(job),
                **india_meta,
            })

        # 3. Cache newly computed matches
        await repo.save_cached_matches(db, user_id, resume_version, newly_computed_to_cache)

    results.sort(key=_multi_factor_rank_key)
    return results


def _is_india_entry(r: dict) -> bool:
    from app.modules.jobs.location_normalization import is_india_opportunity
    return r.get("country") == "India" or is_india_opportunity(r.get("location"))


def _multi_factor_rank_key(r: dict):
    """
    Deterministic multi-factor opportunity ranking adhering to Phase 17 priorities:
    1. Geography (India-first)
    2. Eligibility (Eligible/Likely > Unknown/Check > Ineligible)
    3. Canonical role relevance (Classified role > unclassified)
    4. Freshness (posted_days_ago)
    5. Valid direct application path trust (Direct requisition > other)
    6. Source/employer trust (Direct ATS > fallback)
    7. Information richness (PRIMARY tier > SECONDARY tier)
    8. Candidate technical match score (-overall_score)
    """
    geo_rank = 0 if _is_india_entry(r) else 1
    
    # Eligibility rank
    elig = r.get("eligibility")
    elig_status = elig.get("status") if isinstance(elig, dict) else None
    if elig_status in ("ELIGIBLE", "LIKELY_ELIGIBLE"):
        elig_rank = 0
    elif elig_status in ("OPPORTUNITY_NOT_SUFFICIENTLY_SPECIFIED", "UNKNOWN", None):
        elig_rank = 1
    else:
        elig_rank = 2

    # Role relevance: concrete canonical role prioritized over generic/unclassified
    c_role = r.get("canonical_role")
    role_rank = 0 if (c_role and c_role != "Specialized Requisition") else 1

    # Freshness
    freshness = int(r.get("posted_days_ago", 0))

    # Direct application trust
    direct_apply_rank = 0 if (r.get("is_direct_apply") or r.get("url_type") == "DIRECT_REQUISITION") else 1

    # Source trust: direct ATS feeds
    source_trust = 0 if r.get("source") in ("smartrecruiters", "lever", "greenhouse") else 1

    # Information richness / quality tier
    q_tier_rank = 0 if r.get("quality_tier") == "PRIMARY" else 1

    # Technical match score (higher is better, so negated)
    tech_match = -float(r.get("overall_score", 0.0))

    return (
        geo_rank,
        elig_rank,
        role_rank,
        freshness,
        direct_apply_rank,
        source_trust,
        q_tier_rank,
        tech_match,
    )

