"""
Ashby Direct Live Opportunity Provider Adapter.
Uses documented, unauthenticated public Job Board API:
- List openings: GET https://api.ashbyhq.com/posting-api/job-board/{board_token}?includeCompensation=true

Strictly adheres to RoleRadar Direct Requisition Policies:
1. Generates DIRECT_REQUISITION application URLs pointing directly to employer requisitions.
2. Employs authoritative provider inventory diffing:
   - Disappeared listings on successful sync -> CLOSED
   - Transient network/provider failures -> retain state, never close jobs destructively
3. Zero Date Fabrication: posted_at populated strictly from authoritative publishedAt timestamp.
4. Internships classified via explicit structured metadata and title markers (never description substring).
"""
from __future__ import annotations

from datetime import datetime, timezone
import html
import logging
import re
from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.db.mongo import Collections
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text
from app.modules.jobs.completeness import evaluate_opportunity_completeness
from app.modules.jobs.deduplication import deduplicate_opportunities
from app.modules.jobs.location_normalization import (
    extract_country_from_location,
    is_india_opportunity,
    normalize_india_location,
)
from app.modules.jobs.classification import classify_opportunity
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyProviderError(Exception):
    """Base error for Ashby provider failures."""
    pass


class AshbyNetworkError(AshbyProviderError):
    """Raised when a network or timeout error occurs during fetch."""
    pass


def _clean_html_description(html_text: str | None) -> str:
    """Strips basic HTML tags and unescapes all character entities for plaintext preview."""
    if not html_text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html_text)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def is_internship_opportunity(
    title: str,
    employment_type: str | None = None,
    department: str | None = None,
) -> bool:
    """
    Classifies whether an Ashby listing is an internship.
    Uses title detection and structured employmentType/department.
    STRICT RULE: Never classifies based merely on description substrings.
    """
    title_lower = title.lower()
    # Explicit internship markers in title
    if re.search(r"\b(?:intern|internship|co-?op|trainee|apprentice)\b", title_lower):
        return True

    # Structured employmentType classification
    if employment_type:
        emp_clean = employment_type.strip().lower()
        if emp_clean in ("intern", "internship", "coop", "co-op", "trainee", "apprentice"):
            return True

    # Department classification
    if department:
        dept_clean = department.strip().lower()
        if any(k in dept_clean for k in ("intern", "university", "campus", "trainee")):
            return True

    return False


class AshbyJobProvider:
    """
    Production-grade adapter for Ashby Job Board API.
    Interacts directly with official public JSON endpoints.
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._timeout = float(getattr(self._settings, "ASHBY_REQUEST_TIMEOUT_SECONDS", 15))

    async def fetch_company_openings(self, board_token: str) -> list[dict]:
        """
        Fetches all currently published openings for a given Ashby board token.
        Endpoint: GET https://api.ashbyhq.com/posting-api/job-board/{board_token}?includeCompensation=true
        Raises AshbyNetworkError on connection failure / timeout.
        """
        clean_token = board_token.strip().lower()
        url = f"{BASE_URL}/{clean_token}?includeCompensation=true"
        headers = {
            "User-Agent": "RoleRadar-DirectATS/1.0 (+https://roleradar.internal)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    logger.warning(f"Ashby board '{clean_token}' returned 404 Not Found.")
                    return []
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    return []
                return data.get("jobs", [])
        except httpx.TimeoutException as exc:
            logger.error(f"Timeout fetching Ashby board '{clean_token}': {exc}")
            raise AshbyNetworkError(f"Timeout connecting to Ashby board '{clean_token}'") from exc
        except (httpx.HTTPError, httpx.RequestError) as exc:
            logger.error(f"HTTP error fetching Ashby board '{clean_token}': {exc}")
            raise AshbyNetworkError(f"HTTP failure fetching Ashby board '{clean_token}': {str(exc)}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error fetching Ashby board '{clean_token}': {exc}")
            raise AshbyProviderError(f"Unexpected failure: {str(exc)}") from exc

    async def fetch_specific_opening(self, board_token: str, job_id: str) -> dict | None:
        """
        Fetches all openings and locates the specific job_id.
        Returns raw job dict if active, None if not found or closed.
        """
        try:
            openings = await self.fetch_company_openings(board_token)
            clean_job_id = str(job_id).strip()
            for job in openings:
                if str(job.get("id", "")).strip() == clean_job_id:
                    return job
            return None
        except Exception as exc:
            logger.warning(f"Could not probe specific Ashby opening {board_token}/{job_id}: {exc}")
            return None

    def normalize_ashby_job(
        self,
        raw: dict,
        board_token: str,
        company_name: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Normalizes a raw Ashby API response item into the canonical Opportunity model.
        Strictly satisfies all product requirements:
        - Specific requisition URL evaluated through url_classifier
        - Zero date fabrication (posted_at only from publishedAt)
        - Explicit internship classification
        - Extraction of skills and canonical taxonomy from description
        - Structured compensation parsing
        - India geography filtering
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        job_id = str(raw.get("id", "")).strip()
        title = (raw.get("title") or "").strip()
        resolved_company = company_name or board_token.title()

        # Location extraction
        location_raw = (raw.get("location") or "").strip()
        sec_locs = raw.get("secondaryLocations") or []
        sec_str_parts = []
        if isinstance(sec_locs, list):
            for sl in sec_locs:
                if isinstance(sl, dict) and sl.get("location"):
                    sec_str_parts.append(str(sl.get("location")).strip())
                elif isinstance(sl, str) and sl.strip():
                    sec_str_parts.append(sl.strip())

        # Structured postal address
        address_obj = raw.get("address") or {}
        postal_obj = address_obj.get("postalAddress") or {} if isinstance(address_obj, dict) else {}
        addr_country = postal_obj.get("addressCountry") or ""
        addr_locality = postal_obj.get("addressLocality") or ""
        addr_region = postal_obj.get("addressRegion") or ""

        # Build combined location display string
        loc_display_parts = []
        if location_raw:
            loc_display_parts.append(location_raw)
        elif addr_locality or addr_region or addr_country:
            loc_display_parts.append(", ".join(p for p in [addr_locality, addr_region, addr_country] if p))

        display_location = "; ".join(loc_display_parts) if loc_display_parts else "Not specified"

        # Remote / Workplace Mode
        is_remote_flag = bool(raw.get("isRemote"))
        workplace_raw = (raw.get("workplaceType") or "").strip().lower()
        is_remote = is_remote_flag or workplace_raw == "remote" or "remote" in display_location.lower() or "remote" in title.lower()

        if is_remote or workplace_raw == "remote":
            workplace_type = "REMOTE"
        elif workplace_raw == "hybrid":
            workplace_type = "HYBRID"
        elif display_location != "Not specified":
            workplace_type = "ON_SITE"
        else:
            workplace_type = "UNKNOWN"

        # Country Extraction and India Filtering
        # 1. Determine country
        country = extract_country_from_location(display_location)
        if not country and addr_country:
            country = extract_country_from_location(addr_country) or (
                "India" if addr_country.strip().lower() in ("india", "in") else addr_country.strip()
            )

        # 2. India Relevance Check
        all_loc_text = f"{display_location} {' '.join(sec_str_parts)} {addr_locality} {addr_region} {addr_country}"
        is_india = is_india_opportunity(all_loc_text)
        if not is_india and (addr_country.strip().lower() in ("india", "in") or country == "India"):
            is_india = True

        # Plaintext and HTML description
        raw_html = raw.get("descriptionHtml") or ""
        desc_plain = raw.get("descriptionPlain") or ""
        if desc_plain and desc_plain.strip():
            clean_desc = desc_plain.strip()
        else:
            clean_desc = _clean_html_description(raw_html) or title

        # Application URL Classification
        apply_url_raw = (raw.get("applyUrl") or "").strip()
        job_url_raw = (raw.get("jobUrl") or "").strip()

        chosen_url = apply_url_raw or job_url_raw
        if chosen_url:
            url_type, url_reason = classify_application_url(chosen_url, company=resolved_company)
        else:
            url_type, url_reason = ApplicationUrlType.INVALID, "Missing application URL."

        is_direct_apply = (url_type == ApplicationUrlType.DIRECT_REQUISITION)
        is_listed = raw.get("isListed", True)

        # Verification Status
        if is_direct_apply and is_listed:
            verification_status = OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
            verification_reason = f"Authoritatively published on Ashby {board_token} board"
        elif not is_listed:
            verification_status = OpportunityLifecycleStatus.CLOSED.value
            verification_reason = "Unlisted requisition on Ashby board"
        elif url_type == ApplicationUrlType.INVALID:
            verification_status = OpportunityLifecycleStatus.INVALID.value
            verification_reason = f"Rejected invalid application URL: {url_reason}"
        else:
            verification_status = OpportunityLifecycleStatus.PENDING_VERIFICATION.value
            verification_reason = f"Non-direct requisition URL ({url_type.value}): {url_reason}"

        # Dates: NO FABRICATION RULE
        published_at_raw = raw.get("publishedAt")
        posted_at_iso = None
        posted_days_ago = 0
        if published_at_raw:
            try:
                dt = datetime.fromisoformat(str(published_at_raw).replace("Z", "+00:00"))
                posted_at_iso = dt.isoformat()
                posted_days_ago = max(0, (now - dt).days)
            except Exception:
                posted_at_iso = str(published_at_raw)
                posted_days_ago = 0

        updated_at_iso = None

        # Internship / Suitability classification
        emp_type = raw.get("employmentType")
        dept = raw.get("department")
        is_intern = is_internship_opportunity(title=title, employment_type=emp_type, department=dept)
        job_type = "internship" if is_intern else "full_time"
        opportunity_type = "INTERNSHIP" if is_intern else "FULL_TIME"

        classification = classify_opportunity(
            title=title,
            description=clean_desc,
            experience_min=0 if is_intern else None,
            experience_max=2 if is_intern else None,
            job_type_hint="internship" if is_intern else "",
        )

        # Requirements analysis & Skill extraction
        reqs = analyze_job_description(clean_desc, title)
        skills_required = list(dict.fromkeys(reqs.must_have_skills or reqs.required_skills))
        skills_nice_to_have = list(dict.fromkeys(reqs.preferred_skills))

        canonical_id = f"ashby_{board_token.lower()}_{job_id}"

        # Structured Compensation extraction
        comp = extract_compensation_from_payload_and_text(
            text=f"{clean_desc} {raw_html or ''}",
            raw_payload=raw,
            is_internship=is_intern,
        )

        # Completeness evaluation
        comp_eval = evaluate_opportunity_completeness({
            "title": title,
            "company": resolved_company,
            "location": display_location,
            "country": country,
            "is_india_opportunity": is_india,
            "opportunity_type": opportunity_type,
            "description": clean_desc,
            "responsibilities": reqs.responsibilities,
            "qualifications": reqs.qualifications,
            "skills_required": skills_required,
            "skills_nice_to_have": skills_nice_to_have,
            "verification_status": verification_status,
            "apply_url": chosen_url,
            "is_direct_apply": is_direct_apply,
            "salary_min": comp.salary_min,
            "salary_max": comp.salary_max,
            "stipend_min": comp.stipend_min,
            "stipend_max": comp.stipend_max,
            "compensation_text": comp.compensation_text,
            "experience_min": (
                int(reqs.min_years_experience)
                if reqs.min_years_experience is not None
                else (0 if is_intern else None)
            ),
            "experience_max": (
                int(reqs.max_years_experience)
                if reqs.max_years_experience is not None
                else (2 if is_intern else None)
            ),
        })

        return {
            "id": canonical_id,
            "source": "ashby",
            "source_job_id": job_id,
            "company_board": board_token.lower(),
            "title": title,
            "company": resolved_company,
            "industry": "Technology",
            "description": clean_desc,
            "jd_text": clean_desc,
            "raw_html": raw_html,
            "skills_required": skills_required,
            "skills_nice_to_have": skills_nice_to_have,
            "responsibilities": reqs.responsibilities,
            "qualifications": reqs.qualifications,
            "structured_requirements": reqs.model_dump(mode="json"),
            "experience_min": (
                int(reqs.min_years_experience)
                if reqs.min_years_experience is not None
                else (0 if is_intern else None)
            ),
            "experience_max": (
                int(reqs.max_years_experience)
                if reqs.max_years_experience is not None
                else (2 if is_intern else None)
            ),
            "job_type": job_type,
            "opportunity_type": opportunity_type,
            "country": country,
            "location": display_location,
            "is_remote": is_remote,
            "workplace_type": workplace_type,
            "is_india_opportunity": is_india,
            "completeness_status": comp_eval.source_completeness.value,
            "recommendation_quality": comp_eval.recommendation_quality.value,
            "salary_min": comp.salary_min,
            "salary_max": comp.salary_max,
            "salary_currency": comp.salary_currency,
            "salary_disclosed": comp.salary_disclosed,
            "stipend_min": comp.stipend_min,
            "stipend_max": comp.stipend_max,
            "compensation_type": comp.compensation_type,
            "compensation_text": comp.compensation_text,
            "internship_duration_months": 3 if is_intern else None,
            "fresher_friendly": classification.fresher_eligible,
            "student_friendly": classification.student_eligible,
            "suitability_signal": classification.suitability.value,
            "posted_days_ago": posted_days_ago,
            "posted_at": posted_at_iso,
            "updated_at": updated_at_iso,
            "first_seen_at": now_iso,
            "last_seen_at": now_iso,
            "last_verified_at": now_iso,
            "apply_url": chosen_url,
            "source_url": job_url_raw or chosen_url,
            "verification_status": verification_status,
            "verified_at": now_iso,
            "verification_reason": verification_reason,
            "verification_method": "ashby_api_direct",
            "url_type": url_type.value,
            "is_direct_apply": is_direct_apply,
        }

    async def sync_company_openings(
        self,
        db: AsyncIOMotorDatabase,
        board_token: str,
        company_name: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Synchronizes all openings for an Ashby board token.
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
        except AshbyNetworkError as exc:
            logger.warning(f"Network error during Ashby sync for {clean_token}: {exc}. Retaining previous state.")
            stats["errors"].append(f"Network error: {str(exc)}")
            return stats
        except Exception as exc:
            logger.error(f"Unexpected error during Ashby sync for {clean_token}: {exc}. Retaining previous state.")
            stats["errors"].append(f"Unexpected error: {str(exc)}")
            return stats

        stats["fetched"] = len(raw_jobs)
        current_job_ids = set()
        active_normalized = []

        for item in raw_jobs:
            jid = str(item.get("id", "")).strip()
            if not jid:
                continue
            current_job_ids.add(jid)

            job_doc = self.normalize_ashby_job(item, clean_token, company_name=company_name, now=now)

            # Check if direct requisition and active
            if (
                job_doc.get("url_type") == ApplicationUrlType.DIRECT_REQUISITION.value
                and job_doc.get("verification_status") == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
            ):
                active_normalized.append(job_doc)
                if job_doc.get("job_type") == "internship":
                    stats["internships"] += 1

        stats["verified_active"] = len(active_normalized)

        # Step 2: Handle Disappeared Listings (Authoritative Closure)
        # Query existing stored active records for this Ashby board
        existing_cursor = db[Collections.JOBS].find({
            "source": "ashby",
            "company_board": clean_token,
            "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        })
        existing_active = await existing_cursor.to_list(length=5000)

        for old_job in existing_active:
            old_jid = old_job.get("source_job_id")
            if old_jid and old_jid not in current_job_ids:
                # Authoritative disappearance: employer removed posting from Ashby
                await db[Collections.JOBS].update_one(
                    {"id": old_job["id"]},
                    {
                        "$set": {
                            "verification_status": OpportunityLifecycleStatus.CLOSED.value,
                            "last_verified_at": now_iso,
                            "verification_reason": f"Disappeared from employer's authoritative Ashby {clean_token} feed.",
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
            f"Ashby sync [{clean_token}]: {stats['fetched']} fetched, "
            f"{stats['verified_active']} active, {stats['closed']} closed, {stats['internships']} internships."
        )
        return stats
