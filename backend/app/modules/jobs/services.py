import asyncio
import json
import logging
import os
import threading
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.caching import get_cached_jd_requirements, set_cached_jd_requirements
from app.core.config import Settings, get_settings
from app.db.mongo import Collections
from app.modules.jobs import repositories as repo
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.taxonomy import RequirementCategory, StructuredJobRequirements, analyze_job_description

from datetime import datetime, timezone

from app.modules.jobs.deduplication import deduplicate_opportunities
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import (
    OpportunityLifecycleStatus,
    verify_opportunity_sync,
)

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "seeds", "jobs_seed.json")
logger = logging.getLogger("roleradar.jobs.sync")

_live_refresh_guard = threading.Lock()
_live_refresh_tasks: dict[tuple[int, int], asyncio.Task[dict]] = {}


def _public_provider_error(message: object) -> str:
    """Map provider exceptions to useful, credential-safe status text."""
    text = str(message or "").casefold()
    if "404" in text or "not found" in text:
        return "Configured employer board was not found (HTTP 404)."
    if "429" in text or "rate limit" in text or "rate-limit" in text:
        return "Provider rate-limited this board (HTTP 429)."
    if "timeout" in text or "timed out" in text:
        return "Provider request timed out."
    if "json" in text or "malformed" in text or "invalid response" in text:
        return "Provider returned a malformed response."
    if "network" in text or "connect" in text or "requesterror" in text:
        return "Provider could not be reached."
    return "Provider synchronization failed."


async def ensure_seed_loaded(db: AsyncIOMotorDatabase) -> int:
    """Loads, verifies, deduplicates, and syncs the seed dataset into MongoDB. Idempotent — safe to call on every app startup."""
    seed_path = os.path.abspath(SEED_PATH)
    if not os.path.exists(seed_path):
        return 0

    with open(seed_path) as f:
        jobs = json.load(f)

    if not jobs:
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()
    processed_jobs = []
    for job in jobs:
        url_type, url_reason = classify_application_url(job.get("apply_url"), company=job.get("company"))
        job_copy = dict(job)
        job_copy["source"] = "curated_benchmark"
        job_copy["verification_status"] = OpportunityLifecycleStatus.MARKET_BENCHMARK.value
        job_copy["url_type"] = url_type.value
        job_copy["is_direct_apply"] = False
        job_copy["first_seen_at"] = now_iso
        job_copy["last_verified_at"] = now_iso
        job_copy["verified_at"] = now_iso
        job_copy["verification_reason"] = f"Curated catalog benchmark record: {url_reason}"
        job_copy["verification_method"] = "seed_catalog"
        if not job_copy.get("source_url"):
            job_copy["source_url"] = job_copy.get("apply_url")
        processed_jobs.append(job_copy)

    deduped = deduplicate_opportunities(processed_jobs)
    await repo.upsert_jobs(db, deduped)
    return len(deduped)


async def search_jobs(db: AsyncIOMotorDatabase, filters: dict, user_id: str | None = None) -> list[dict]:
    search_filters = dict(filters)
    if user_id:
        search_filters["user_id"] = user_id
    provider = CuratedJobProvider(db)
    return await provider.search(search_filters)


async def count_jobs(db: AsyncIOMotorDatabase, filters: dict, user_id: str | None = None) -> int:
    search_filters = dict(filters)
    if user_id:
        search_filters["user_id"] = user_id
    provider = CuratedJobProvider(db)
    return await provider.count(search_filters)


def _configured_board_tokens(settings: Settings, attribute: str) -> list[str]:
    configured = getattr(settings, attribute, "")
    if isinstance(configured, str):
        tokens = configured.split(",")
    elif isinstance(configured, (list, tuple, set)):
        tokens = configured
    else:
        return []
    return list(dict.fromkeys(token.strip() for token in tokens if isinstance(token, str) and token.strip()))


def has_configured_direct_ats_boards(settings: Settings) -> bool:
    """Return whether at least one enabled official employer board can be synced."""
    return any(
        getattr(settings, enabled_attribute, False)
        and _configured_board_tokens(settings, companies_attribute)
        for companies_attribute, enabled_attribute in (
            ("ASHBY_COMPANIES", "ASHBY_ENABLED"),
            ("GREENHOUSE_COMPANIES", "GREENHOUSE_ENABLED"),
            ("LEVER_COMPANIES", "LEVER_ENABLED"),
            ("SMARTRECRUITERS_COMPANIES", "SMARTRECRUITERS_ENABLED"),
        )
    )


async def scheduled_job_refresh_loop(db: AsyncIOMotorDatabase, settings: Settings) -> None:
    """Refresh configured official ATS boards periodically until application shutdown."""
    interval_minutes = int(getattr(settings, "JOB_REFRESH_INTERVAL_MINUTES", 360))
    if (
        interval_minutes <= 0
        or getattr(settings, "JOB_SOURCE_MODE", "curated") != "direct_ats"
        or not has_configured_direct_ats_boards(settings)
    ):
        return

    interval_seconds = interval_minutes * 60
    while True:
        try:
            report = await refresh_live_jobs(db, settings, {}, include_report=True)
            if isinstance(report, dict):
                logger.info(
                    "Scheduled direct ATS refresh completed status=%s active=%s",
                    report.get("status"),
                    report.get("added_count", 0),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled direct ATS refresh failed")
        await asyncio.sleep(interval_seconds)


async def _sync_configured_boards(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    provider_class: type,
    companies_attribute: str,
    enabled_attribute: str,
    country: str | None = None,
) -> dict:
    boards = _configured_board_tokens(settings, companies_attribute)
    summary = {"total_boards": len(boards), "fetched": 0, "verified_active": 0, "unique_requisitions": 0, "closed": 0, "internships": 0, "detail_enriched": 0, "detail_enrichment_failed": 0, "detail_enrichment_skipped": 0, "errors": [], "results": []}
    if not getattr(settings, enabled_attribute, False):
        summary["status"] = "disabled"
        return summary
    if not boards:
        summary["status"] = "not_configured"
        return summary

    provider = provider_class(settings)
    semaphore = asyncio.Semaphore(max(1, int(getattr(settings, "JOB_PROVIDER_BOARD_CONCURRENCY", 8))))
    board_timeout = max(0.1, float(getattr(settings, "JOB_PROVIDER_SYNC_TIMEOUT_SECONDS", 25.0)))

    async def sync_board(board: str):
        async with semaphore:
            try:
                kwargs = {"country": country} if country else {}
                result = await asyncio.wait_for(
                    provider.sync_company_openings(db, board, **kwargs),
                    timeout=board_timeout,
                )
                result = dict(result or {})
                result.setdefault("board", board)
                raw_errors = list(result.get("errors") or [])
                if result.get("error"):
                    raw_errors.append(result["error"])
                if result.get("network_error") and not raw_errors:
                    raw_errors.append("Provider network error")
                result["errors"] = list(dict.fromkeys(_public_provider_error(error) for error in raw_errors))
                result["status"] = "partial" if result["errors"] and result.get("verified_active", 0) else (
                    "failed" if result["errors"] else "success"
                )
                return result
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                logger.warning("Provider sync timed out for configured board %s", board)
                return {
                    "board": board,
                    "status": "failed",
                    "errors": ["Board synchronization exceeded its time limit."],
                }
            except Exception as exc:
                logger.warning("Provider sync failed for configured board %s (%s)", board, type(exc).__name__)
                return {
                    "board": board,
                    "status": "failed",
                    "errors": [_public_provider_error(exc)],
                }

    results = await asyncio.gather(*(sync_board(board) for board in boards))
    summary["results"] = results
    for result in results:
        for key in ("fetched", "verified_active", "unique_requisitions", "closed", "internships", "detail_enriched", "detail_enrichment_failed", "detail_enrichment_skipped"):
            summary[key] += int(result.get(key) or 0)
        summary["errors"].extend(
            f"{result.get('board') or 'configured board'}: {error}"
            for error in (result.get("errors") or [])
        )
    return summary


async def sync_all_ashby_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    from app.modules.jobs.ashby_provider import AshbyJobProvider
    return await _sync_configured_boards(db, settings, AshbyJobProvider, "ASHBY_COMPANIES", "ASHBY_ENABLED")


async def sync_all_greenhouse_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
    return await _sync_configured_boards(db, settings, GreenhouseJobProvider, "GREENHOUSE_COMPANIES", "GREENHOUSE_ENABLED")


async def sync_all_lever_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    from app.modules.jobs.lever_provider import LeverJobProvider
    return await _sync_configured_boards(db, settings, LeverJobProvider, "LEVER_COMPANIES", "LEVER_ENABLED")


async def sync_all_smartrecruiters_boards(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider
    return await _sync_configured_boards(
        db,
        settings,
        SmartRecruitersJobProvider,
        "SMARTRECRUITERS_COMPANIES",
        "SMARTRECRUITERS_ENABLED",
        country=getattr(settings, "SMARTRECRUITERS_COUNTRY", None),
    )



async def _run_provider_sync(provider_name: str, sync_coro) -> dict:
    try:
        result = await sync_coro
        if result.get("status") in {"disabled", "not_configured"}:
            return {"provider": provider_name, **result}
        errors = list(result.get("errors") or [])
        configured = int(result.get("total_boards") or 0)
        failed = sum(1 for row in result.get("results", []) if row.get("status") == "failed")
        status = (
            "not_configured" if configured == 0 and not errors
            else "failed" if configured == 0 or failed == configured
            else "partial" if errors or failed
            else "success"
        )
        return {"provider": provider_name, "status": status, **result}
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Provider synchronization failed for %s (%s)", provider_name, type(exc).__name__)
        return {
            "provider": provider_name,
            "status": "failed",
            "total_boards": 0,
            "fetched": 0,
            "verified_active": 0,
            "unique_requisitions": 0,
            "closed": 0,
            "internships": 0,
            "detail_enriched": 0,
            "detail_enrichment_failed": 0,
            "detail_enrichment_skipped": 0,
            "errors": [_public_provider_error(exc)],
            "results": [],
        }


async def _perform_live_job_refresh(db: AsyncIOMotorDatabase, settings: Settings) -> dict:
    provider_calls = {
        "Ashby": sync_all_ashby_boards,
        "Greenhouse": sync_all_greenhouse_boards,
        "Lever": sync_all_lever_boards,
        "SmartRecruiters": sync_all_smartrecruiters_boards,
    }
    provider_tasks = {
        asyncio.create_task(_run_provider_sync(name, call(db, settings))): name
        for name, call in provider_calls.items()
    }
    refresh_timeout = max(0.1, float(getattr(settings, "JOB_REFRESH_TIMEOUT_SECONDS", 75.0)))
    try:
        done, pending = await asyncio.wait(provider_tasks, timeout=refresh_timeout)
    except asyncio.CancelledError:
        for task in provider_tasks:
            task.cancel()
        await asyncio.gather(*provider_tasks, return_exceptions=True)
        raise

    provider_results = []
    for task in done:
        name = provider_tasks[task]
        if task.cancelled():
            provider_results.append({
                "provider": name,
                "status": "failed",
                "total_boards": 0,
                "fetched": 0,
                "verified_active": 0,
                "unique_requisitions": 0,
                "closed": 0,
                "internships": 0,
                "detail_enriched": 0,
                "detail_enrichment_failed": 0,
                "detail_enrichment_skipped": 0,
                "errors": ["Provider task was cancelled."],
                "results": [],
            })
            continue
        try:
            provider_results.append(task.result())
        except Exception as exc:
            logger.exception("Provider task failed for %s (%s)", name, type(exc).__name__)
            provider_results.append({
                "provider": name,
                "status": "failed",
                "total_boards": 0,
                "fetched": 0,
                "verified_active": 0,
                "unique_requisitions": 0,
                "closed": 0,
                "internships": 0,
                "detail_enriched": 0,
                "detail_enrichment_failed": 0,
                "detail_enrichment_skipped": 0,
                "errors": [_public_provider_error(exc)],
                "results": [],
            })
    for task in pending:
        name = provider_tasks[task]
        task.cancel()
        provider_results.append({
            "provider": name,
            "status": "timed_out",
            "total_boards": 0,
            "fetched": 0,
            "verified_active": 0,
            "unique_requisitions": 0,
            "closed": 0,
            "internships": 0,
            "detail_enriched": 0,
            "detail_enrichment_failed": 0,
            "detail_enrichment_skipped": 0,
            "errors": ["Provider did not finish before the refresh deadline."],
            "results": [],
        })
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    provider_results.sort(key=lambda result: result["provider"])
    errors = [
        f"{provider['provider']}: {error}"
        for provider in provider_results
        for error in provider.get("errors", [])
    ]
    active = sum(int(result.get("verified_active") or 0) for result in provider_results)
    providers_configured = [
        result for result in provider_results
        if result.get("status") not in {"not_configured", "disabled"}
    ]
    status = "not_configured" if not providers_configured else (
        "failed" if all(result.get("status") in {"failed", "timed_out"} for result in providers_configured)
        else "partial" if errors
        else "success"
    )
    return {
        "status": status,
        "added_count": active,
        "unique_requisitions": sum(int(result.get("unique_requisitions") or 0) for result in provider_results),
        "errors": errors,
        "detail_enriched": sum(int(result.get("detail_enriched") or 0) for result in provider_results),
        "detail_enrichment_failed": sum(int(result.get("detail_enrichment_failed") or 0) for result in provider_results),
        "detail_enrichment_skipped": sum(int(result.get("detail_enrichment_skipped") or 0) for result in provider_results),
        "providers": provider_results,
    }


async def refresh_live_jobs(db: AsyncIOMotorDatabase, settings: Settings, filters: dict, include_report: bool = False) -> int | dict:
    """Refresh configured ATS feeds with bounded, single-flight provider work."""
    if getattr(settings, "JOB_SOURCE_MODE", "curated") != "direct_ats":
        report = {
            "status": "not_configured",
            "added_count": 0,
            "unique_requisitions": 0,
            "errors": [],
            "detail_enriched": 0,
            "detail_enrichment_failed": 0,
            "detail_enrichment_skipped": 0,
            "providers": [],
        }
        return report if include_report else 0

    loop = asyncio.get_running_loop()
    task_key = (id(db), id(settings))
    with _live_refresh_guard:
        task = _live_refresh_tasks.get(task_key)
        if task is None or task.done() or task.get_loop() is not loop:
            task = loop.create_task(_perform_live_job_refresh(db, settings))
            _live_refresh_tasks[task_key] = task

            def remove_completed(done_task: asyncio.Task, key: tuple[int, int] = task_key) -> None:
                with _live_refresh_guard:
                    if _live_refresh_tasks.get(key) is done_task:
                        _live_refresh_tasks.pop(key, None)

            task.add_done_callback(remove_completed)

    report = await asyncio.shield(task)
    return report if include_report else int(report["added_count"])


async def reverify_active_opportunities(db: AsyncIOMotorDatabase, now: datetime | None = None) -> dict:
    """
    Re-verifies existing opportunities in MongoDB.
    Transitions stale/closed/expired/invalid listings out of VERIFIED_ACTIVE.
    Preserves historical records internally with updated status.
    """
    cursor = db[Collections.JOBS].find({})
    all_jobs = await cursor.to_list(length=2000)

    stats = {
        "checked": len(all_jobs),
        "retained_active": 0,
        "transitioned_closed": 0,
        "transitioned_expired": 0,
        "transitioned_stale": 0,
        "transitioned_invalid": 0,
    }

    for job in all_jobs:
        prev_status = job.get("verification_status", OpportunityLifecycleStatus.VERIFIED_ACTIVE.value)
        source = job.get("source")
        is_aggregator = source in ("adzuna", "jooble", "remotive", "arbeitnow", "jsearch")
        vres = verify_opportunity_sync(job, now=now, enforce_direct_apply=not is_aggregator)
        new_status = vres.status.value

        update_fields = {
            "verification_status": new_status,
            "verified_at": vres.verified_at,
            "last_verified_at": vres.verified_at,
            "verification_reason": vres.reason,
            "verification_method": "reverification_audit",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type == ApplicationUrlType.DIRECT_REQUISITION and new_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value),
        }

        if new_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value:
            stats["retained_active"] += 1
        elif new_status == OpportunityLifecycleStatus.CLOSED.value:
            stats["transitioned_closed"] += 1
        elif new_status == OpportunityLifecycleStatus.EXPIRED.value:
            stats["transitioned_expired"] += 1
        elif new_status == OpportunityLifecycleStatus.STALE.value:
            stats["transitioned_stale"] += 1
        elif new_status == OpportunityLifecycleStatus.INVALID.value:
            stats["transitioned_invalid"] += 1

        await db[Collections.JOBS].update_one({"id": job["id"]}, {"$set": update_fields})

    return stats


async def get_job(db: AsyncIOMotorDatabase, job_id: str, user_id: str | None = None) -> dict | None:
    job = await repo.get_job_by_id(db, job_id)
    if job is None:
        return None
    # User-scoping for custom JDs
    if job.get("source") == "custom" and job.get("user_id"):
        if not user_id or job.get("user_id") != user_id:
            return None

    posted_at = job.get("posted_at") or job.get("first_seen_at")
    if posted_at:
        try:
            p_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            job["posted_days_ago"] = max(0, (datetime.now(timezone.utc) - p_dt).days)
        except (ValueError, TypeError):
            pass

    return job


async def get_canonical_job_requirements(db: AsyncIOMotorDatabase, job: dict) -> StructuredJobRequirements:
    """
    Canonical JD Intelligence Accessor.
    Resolves authoritative StructuredJobRequirements from:
    1. Pre-stored structured_requirements dictionary if present
    2. Cached in-memory taxonomy analysis
    3. Fresh analyze_job_description(jd_text, title) with lazy caching
    """
    # 1. Direct structured_requirements in document
    if job.get("structured_requirements") and isinstance(job["structured_requirements"], dict):
        try:
            sr = StructuredJobRequirements(**job["structured_requirements"])
            # If experience bounds were not extracted previously, re-evaluate to catch explicit requirements
            if sr.min_years_experience is None and sr.max_years_experience is None:
                jd_text = job.get("jd_text") or job.get("description") or ""
                fresh = analyze_job_description(jd_text, job.get("title") or "")
                if fresh.min_years_experience is not None or fresh.max_years_experience is not None:
                    sr.min_years_experience = fresh.min_years_experience
                    sr.max_years_experience = fresh.max_years_experience
                    sr.experience_requirements = fresh.experience_requirements
                    if job.get("id"):
                        try:
                            update_dict = {"structured_requirements": sr.model_dump(mode="json")}
                            if sr.min_years_experience is not None:
                                update_dict["experience_min"] = int(sr.min_years_experience)
                                job["experience_min"] = int(sr.min_years_experience)
                            if sr.max_years_experience is not None:
                                update_dict["experience_max"] = int(sr.max_years_experience)
                                job["experience_max"] = int(sr.max_years_experience)
                            await db[Collections.JOBS].update_one({"id": job["id"]}, {"$set": update_dict})
                        except Exception:
                            pass
            if sr.must_have_skills or sr.required_skills or sr.responsibilities:
                return sr
        except Exception:
            pass

    jd_text = job.get("jd_text") or job.get("description") or ""
    title = job.get("title") or ""

    # 2. Check in-memory cache
    cached = get_cached_jd_requirements(jd_text, title)
    if cached is not None:
        return cached

    # 3. Analyze raw JD text through Phase 3 generalized taxonomy
    reqs = analyze_job_description(jd_text, title)
    set_cached_jd_requirements(jd_text, title, reqs)

    # Lazily update MongoDB job document if it has an id
    if job.get("id"):
        try:
            update_dict = {"structured_requirements": reqs.model_dump(mode="json")}
            if reqs.min_years_experience is not None and job.get("experience_min") is None:
                update_dict["experience_min"] = int(reqs.min_years_experience)
                job["experience_min"] = int(reqs.min_years_experience)
            if reqs.max_years_experience is not None and job.get("experience_max") is None:
                update_dict["experience_max"] = int(reqs.max_years_experience)
                job["experience_max"] = int(reqs.max_years_experience)
            await db[Collections.JOBS].update_one(
                {"id": job["id"]},
                {"$set": update_dict}
            )
        except Exception:
            pass

    return reqs


async def create_custom_job(
    db: AsyncIOMotorDatabase,
    company: str,
    title: str,
    jd_text: str,
    user_id: str | None = None,
) -> dict:
    """
    Canonical Opportunity Factory for User-Pasted External JDs.
    Runs full Phase 3 generalized semantic analysis (analyze_job_description).
    Zero arbitrary skill slicing, complete responsibilities preservation,
    and user-scoped isolation.
    """
    # 1. Canonical JD Analysis
    reqs = analyze_job_description(jd_text, title)

    # 2. Extract structured fields
    resolved_title = reqs.target_role or title or "Target Role"
    resolved_company = reqs.company or company or "Custom Application"
    resolved_location = reqs.location or "Not specified"
    resolved_work_mode = reqs.work_mode
    is_remote = (resolved_work_mode == "Remote") or ("remote" in resolved_location.lower())

    resp_list = [
        r.text for r in reqs.requirements
        if r.category == RequirementCategory.RESPONSIBILITY
    ]
    if not resp_list and reqs.responsibilities:
        resp_list = list(reqs.responsibilities)

    exp_min = int(reqs.min_years_experience) if reqs.min_years_experience is not None else 0
    exp_max = int(reqs.max_years_experience) if reqs.max_years_experience is not None else (exp_min + 3 if exp_min > 0 else 5)

    is_intern = (
        (reqs.employment_type and "intern" in reqs.employment_type.lower())
        or ("intern" in resolved_title.lower())
    )

    must_have_skills = list(reqs.must_have_skills)
    preferred_skills = list(reqs.preferred_skills)

    # If the JD had no explicit requirement headings (e.g. single-paragraph or informal JD),
    # fallback to detected technologies, keywords, or vocabulary extraction so skills are preserved
    if not must_have_skills and not preferred_skills:
        fallback = reqs.technologies or reqs.required_skills or extract_skills_from_text(jd_text)
        must_have_skills = list(fallback)

    job = {
        "id": f"custom_{uuid.uuid4().hex[:10]}",
        "user_id": user_id,  # User-scoped ownership for privacy & isolation
        "source": "custom",
        "title": resolved_title,
        "company": resolved_company,
        "industry": reqs.domain or "Technology",
        "description": jd_text,
        "jd_text": jd_text,
        # Canonical Phase 3 fields
        "must_have_skills": must_have_skills,
        "preferred_skills": preferred_skills,
        "seniority": reqs.seniority,
        "domain": reqs.domain,
        "min_years_experience": reqs.min_years_experience,
        "max_years_experience": reqs.max_years_experience,
        "company_overview": reqs.company_overview,
        "role_overview": reqs.role_overview,
        "structured_requirements": reqs.model_dump(mode="json"),
        # Backward-compatibility projection fields for discovery / legacy queries
        "skills_required": list(must_have_skills),
        "skills_nice_to_have": list(preferred_skills),
        "responsibilities": resp_list,
        "experience_min": exp_min,
        "experience_max": exp_max,
        "job_type": "internship" if is_intern else "full_time",
        "location": resolved_location,
        "is_remote": is_remote,
        "salary_min": None,
        "salary_max": None,
        "salary_disclosed": False,
        "stipend_min": None,
        "internship_duration_months": None,
        "fresher_friendly": exp_min == 0,
        "apply_url": "",
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "url_type": ApplicationUrlType.UNVERIFIED.value,
        "is_direct_apply": False,
        "verification_reason": "User-created private custom opportunity",
        "verification_method": "custom_creation",
    }

    # Persist and cache canonical analysis
    await db[Collections.JOBS].insert_one(job)
    set_cached_jd_requirements(jd_text, resolved_title, reqs)
    return job
