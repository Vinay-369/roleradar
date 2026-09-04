"""
Greenhouse Direct Live Opportunity Provider Adapter.
Uses documented, unauthenticated public Job Board API:
- List openings: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
- Specific opening: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}

Strictly adheres to RoleRadar Direct Requisition Policies:
1. Generates DIRECT_REQUISITION application URLs pointing directly to employer requisitions.
2. Employs authoritative provider inventory diffing:
   - Disappeared listings on successful sync -> CLOSED
   - Transient network/provider failures -> retain state, never close jobs destructively
3. Zero Date Fabrication: posted_at populated only if first_published is provided.
4. Internships classified via explicit structured metadata and title markers (never description substring).
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.db.mongo import Collections
from app.modules.jobs import repositories as repo
from app.modules.jobs.deduplication import deduplicate_opportunities
from app.modules.jobs.location_normalization import extract_country_from_location
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseProviderError(Exception):
    """Base error for Greenhouse provider failures."""
    pass


class GreenhouseNetworkError(GreenhouseProviderError):
    """Raised when a network or timeout error occurs during fetch."""
    pass


def _clean_html_description(html_text: str | None) -> str:
    """Strips basic HTML tags for plaintext preview while retaining text structure."""
    if not html_text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def is_internship_opportunity(title: str, departments: list[dict] | None = None) -> bool:
    """
    Classifies whether a Greenhouse listing is an internship.
    Uses title detection and structured department names.
    STRICT RULE: Never classifies based merely on description substrings.
    """
    title_lower = title.lower()
    # Explicit internship markers in title
    if re.search(r"\b(?:intern|internship|co-?op|trainee|apprentice)\b", title_lower):
        return True

    # Department classification
    if departments:
        for dept in departments:
            name = dept.get("name", "").lower()
            if "intern" in name or "university" in name or "campus" in name:
                return True

    return False


class GreenhouseJobProvider:
    """
    Production-grade adapter for Greenhouse Job Board API.
    Interacts directly with public JSON endpoints.
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._timeout = float(getattr(self._settings, "GREENHOUSE_REQUEST_TIMEOUT_SECONDS", 15))

    async def fetch_company_openings(self, board_token: str) -> list[dict]:
        """
        Fetches all currently published openings for a given Greenhouse board token.
        Endpoint: GET /v1/boards/{board_token}/jobs?content=true
        Raises GreenhouseNetworkError on connection failure / timeout.
        """
        clean_token = board_token.strip().lower()
        url = f"{BASE_URL}/{clean_token}/jobs?content=true"
        headers = {
            "User-Agent": "RoleRadar-DirectATS/1.0 (+https://roleradar.internal)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    logger.warning(f"Greenhouse board '{clean_token}' returned 404 Not Found.")
                    return []
                resp.raise_for_status()
                data = resp.json()
                return data.get("jobs", [])
        except httpx.TimeoutException as exc:
            logger.error(f"Timeout fetching Greenhouse board '{clean_token}': {exc}")
            raise GreenhouseNetworkError(f"Timeout connecting to Greenhouse board '{clean_token}'") from exc
        except (httpx.HTTPError, httpx.RequestError) as exc:
            logger.error(f"HTTP error fetching Greenhouse board '{clean_token}': {exc}")
            raise GreenhouseNetworkError(f"HTTP failure fetching Greenhouse board '{clean_token}': {str(exc)}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error fetching Greenhouse board '{clean_token}': {exc}")
            raise GreenhouseProviderError(f"Unexpected failure: {str(exc)}") from exc

    async def fetch_specific_opening(self, board_token: str, job_id: str | int) -> dict | None:
        """
        Lightweight check of a specific requisition status.
        Endpoint: GET /v1/boards/{board_token}/jobs/{job_id}
        Returns raw job dict if active, None if 404/closed.
        """
        clean_token = board_token.strip().lower()
        clean_job_id = str(job_id).strip()
        url = f"{BASE_URL}/{clean_token}/jobs/{clean_job_id}"
        headers = {
            "User-Agent": "RoleRadar-DirectATS/1.0 (+https://roleradar.internal)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning(f"Could not probe specific opening {clean_token}/{clean_job_id}: {exc}")
            return None

    def normalize_greenhouse_job(
        self,
        raw: dict,
        board_token: str,
        company_name: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Normalizes a raw Greenhouse API response item into the canonical Opportunity model.
        Strictly satisfies all product requirements:
        - Specific requisition URL evaluated through url_classifier
        - Zero date fabrication (posted_at only from first_published)
        - Updated_at preserved from updated_at
        - Explicit internship classification
        - Extraction of skills from raw description
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        job_id = str(raw.get("id", ""))
        title = (raw.get("title") or "").strip()
        resolved_company = company_name or raw.get("company_name") or board_token.title()

        loc_obj = raw.get("location") or {}
        location = loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj)
        location = (location or "Not specified").strip()
        is_remote = "remote" in location.lower() or "remote" in title.lower()

        # HTML and clean description
        raw_html = raw.get("content") or ""
        clean_desc = _clean_html_description(raw_html) or title

        # Application URL classification
        apply_url = (raw.get("absolute_url") or "").strip()
        url_type, url_reason = classify_application_url(apply_url, company=resolved_company)

        # Dates: NO FABRICATION RULE
        # first_published represents original posting date
        # updated_at represents last update date
        first_pub = raw.get("first_published")
        posted_at_iso = None
        if first_pub:
            try:
                # Validate and format ISO
                dt = datetime.fromisoformat(first_pub.replace("Z", "+00:00"))
                posted_at_iso = dt.isoformat()
            except (ValueError, TypeError):
                posted_at_iso = first_pub

        updated_at = raw.get("updated_at")
        updated_at_iso = None
        if updated_at:
            try:
                dt_u = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                updated_at_iso = dt_u.isoformat()
            except (ValueError, TypeError):
                updated_at_iso = updated_at

        # Calculate posted_days_ago if posted_at available
        posted_days_ago = 0
        if posted_at_iso:
            try:
                dt = datetime.fromisoformat(posted_at_iso.replace("Z", "+00:00"))
                posted_days_ago = max(0, (now - dt).days)
            except Exception:
                posted_days_ago = 0

        # Department / internship detection
        departments = raw.get("departments") or []
        is_intern = is_internship_opportunity(title, departments)
        job_type = "internship" if is_intern else "full_time"

        # Skills extraction from text
        extracted_skills = extract_skills_from_text(f"{title}\n{clean_desc}")

        canonical_id = f"gh_{board_token.lower()}_{job_id}"

        return {
            "id": canonical_id,
            "source": "greenhouse",
            "source_job_id": job_id,
            "company_board": board_token.lower(),
            "title": title,
            "company": resolved_company,
            "industry": "Technology",
            "description": clean_desc,
            "jd_text": clean_desc,
            "raw_html": raw_html,
            "skills_required": extracted_skills[:8],
            "skills_nice_to_have": extracted_skills[8:16],
            "responsibilities": [],
            "experience_min": 0 if is_intern else None,
            "experience_max": 2 if is_intern else None,
            "job_type": job_type,
            "country": extract_country_from_location(location),
            "location": location,
            "is_remote": is_remote,
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": False,
            "stipend_min": None,
            "internship_duration_months": 3 if is_intern else None,
            "fresher_friendly": is_intern or ("junior" in title.lower()) or ("graduate" in title.lower()),
            "posted_days_ago": posted_days_ago,
            "posted_at": posted_at_iso,
            "updated_at": updated_at_iso,
            "first_seen_at": now_iso,
            "last_seen_at": now_iso,
            "last_verified_at": now_iso,
            "apply_url": apply_url,
            "source_url": apply_url,
            "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
            "verified_at": now_iso,
            "verification_reason": f"Authoritatively published on Greenhouse {board_token} board",
            "verification_method": "greenhouse_api_direct",
            "url_type": url_type.value,
            "is_direct_apply": (url_type == ApplicationUrlType.DIRECT_REQUISITION),
        }

    async def sync_company_openings(
        self,
        db: AsyncIOMotorDatabase,
        board_token: str,
        company_name: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Synchronizes all openings for a Greenhouse board token.
        1. Queries authoritative published openings list.
        2. Normalizes, verifies, and deduplicates active openings.
        3. Identifies previously active records for this board token that disappeared.
        4. Transitions disappeared records to CLOSED.
        5. Handles failures gracefully: Network error -> keep state, never close jobs.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        clean_token = board_token.strip().lower()
        stats = {
            "board": clean_token,
            "fetched": 0,
            "verified_active": 0,
            "closed": 0,
            "retained": 0,
            "internships": 0,
            "errors": [],
        }

        # Step 1: Fetch published jobs
        try:
            raw_jobs = await self.fetch_company_openings(clean_token)
        except GreenhouseNetworkError as exc:
            logger.warning(f"Network error during Greenhouse sync for {clean_token}: {exc}. Retaining previous state.")
            stats["errors"].append(f"Network error: {str(exc)}")
            return stats
        except Exception as exc:
            logger.error(f"Unexpected error during Greenhouse sync for {clean_token}: {exc}. Retaining previous state.")
            stats["errors"].append(f"Unexpected error: {str(exc)}")
            return stats

        stats["fetched"] = len(raw_jobs)
        current_job_ids = set()
        active_normalized = []

        for item in raw_jobs:
            jid = str(item.get("id", ""))
            if not jid:
                continue
            current_job_ids.add(jid)

            job_doc = self.normalize_greenhouse_job(item, clean_token, company_name=company_name, now=now)

            # Check if direct requisition
            if job_doc.get("url_type") == ApplicationUrlType.DIRECT_REQUISITION.value:
                active_normalized.append(job_doc)
                if job_doc.get("job_type") == "internship":
                    stats["internships"] += 1

        stats["verified_active"] = len(active_normalized)

        # Step 2: Handle Disappeared Listings (Authoritative Closure)
        # Query existing stored active records for this Greenhouse board
        existing_cursor = db[Collections.JOBS].find({
            "source": "greenhouse",
            "company_board": clean_token,
            "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        })
        existing_active = await existing_cursor.to_list(length=5000)

        for old_job in existing_active:
            old_jid = old_job.get("source_job_id")
            if old_jid and old_jid not in current_job_ids:
                # Authoritative disappearance: employer removed posting from Greenhouse
                await db[Collections.JOBS].update_one(
                    {"id": old_job["id"]},
                    {
                        "$set": {
                            "verification_status": OpportunityLifecycleStatus.CLOSED.value,
                            "last_verified_at": now_iso,
                            "verification_reason": f"Disappeared from employer's authoritative Greenhouse {clean_token} feed.",
                            "is_direct_apply": False,
                        }
                    },
                )
                stats["closed"] += 1
            else:
                stats["retained"] += 1

        # Step 3: Upsert active openings into MongoDB with first_seen_at preservation
        if active_normalized:
            deduped = deduplicate_opportunities(active_normalized)
            for doc in deduped:
                doc_to_save = dict(doc)
                doc_id = doc_to_save.pop("id")
                first_seen = doc_to_save.pop("first_seen_at")

                await db[Collections.JOBS].update_one(
                    {"id": doc_id},
                    {
                        "$set": doc_to_save,
                        "$setOnInsert": {
                            "id": doc_id,
                            "first_seen_at": first_seen,
                        },
                    },
                    upsert=True,
                )

        logger.info(
            f"Greenhouse sync [{clean_token}]: {stats['fetched']} fetched, "
            f"{stats['verified_active']} active, {stats['closed']} closed, {stats['internships']} internships."
        )
        return stats
