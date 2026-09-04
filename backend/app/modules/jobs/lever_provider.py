"""
Lever Direct Live Opportunity Provider Adapter.
Uses documented, unauthenticated public Postings API:
- List openings: GET https://api.lever.co/v0/postings/{company}?mode=json
- Specific opening: GET https://api.lever.co/v0/postings/{company}/{posting_id}

Strictly adheres to RoleRadar Direct Requisition Policies:
1. Generates DIRECT_REQUISITION application URLs pointing directly to employer requisitions.
2. Employs authoritative provider inventory diffing:
   - Disappeared listings on successful sync -> CLOSED
   - Transient network/provider failures -> retain state, never close jobs destructively
3. Zero Date Fabrication: posted_at populated from createdAt epoch; updated_at preserved only if provided.
4. Country and India relevance based strictly on opportunity location geography (never description boilerplate).
5. Fresher & Seniority classification handled conservatively via existing canonical classification contract.
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
from app.modules.jobs.classification import (
    CandidateSuitabilitySignal,
    classify_opportunity,
)
from app.modules.jobs.deduplication import deduplicate_opportunities
from app.modules.jobs.location_normalization import (
    extract_country_from_location,
    is_india_opportunity,
)
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://api.lever.co/v0/postings"


class LeverProviderError(Exception):
    """Base error for Lever provider failures."""
    pass


class LeverNetworkError(LeverProviderError):
    """Raised when a network or timeout error occurs during fetch."""
    pass


def _clean_html_description(html_text: str | None) -> str:
    """Strips basic HTML tags for plaintext preview while retaining text structure."""
    if not html_text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html_text)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&amp;", "&", clean)
    clean = re.sub(r"&lt;", "<", clean)
    clean = re.sub(r"&gt;", ">", clean)
    clean = re.sub(r"&quot;", '"', clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def is_internship_opportunity(
    title: str,
    commitment: str | None = None,
    department: str | None = None,
    team: str | None = None,
) -> bool:
    """
    Classifies whether a Lever listing is an internship.
    Uses title detection and structured metadata (commitment, department, team).
    STRICT RULE: Never classifies based merely on description substrings.
    """
    title_lower = (title or "").lower()
    if re.search(r"\b(?:intern|internship|co-?op|trainee|apprentice)\b", title_lower):
        return True

    # Structured commitment check (e.g. 'Intern', 'Internship', 'Student')
    if commitment:
        comm_lower = commitment.lower()
        if re.search(r"\b(?:intern|internship|co-?op|trainee|student|apprentice)\b", comm_lower):
            return True

    # Structured department or team check
    for field_val in (department, team):
        if field_val:
            val_lower = field_val.lower()
            if "intern" in val_lower or "university" in val_lower or "campus" in val_lower:
                return True

    return False


def _build_lever_description(raw: dict) -> tuple[str, str]:
    """
    Reconstructs clean plaintext and raw html descriptions from Lever's structured payload.
    Combines opening, description, lists (with headers & items), and additional information.
    """
    html_parts: list[str] = []
    plain_parts: list[str] = []

    # 1. Opening section
    opening_plain = raw.get("openingPlain")
    opening_html = raw.get("opening")
    if opening_plain:
        plain_parts.append(opening_plain.strip())
    elif opening_html:
        plain_parts.append(_clean_html_description(opening_html))
    if opening_html:
        html_parts.append(opening_html)

    # 2. Main description body
    desc_plain = raw.get("descriptionPlain")
    desc_html = raw.get("description")
    if desc_plain:
        plain_parts.append(desc_plain.strip())
    elif desc_html:
        plain_parts.append(_clean_html_description(desc_html))
    if desc_html:
        html_parts.append(desc_html)

    # 3. Structured lists (e.g. 'What you will do', 'What you will need')
    raw_lists = raw.get("lists") or []
    if isinstance(raw_lists, list):
        for item in raw_lists:
            if not isinstance(item, dict):
                continue
            heading = item.get("text", "").strip()
            content = item.get("content", "").strip()
            if heading:
                plain_parts.append(f"\n{heading}:")
                html_parts.append(f"<h3>{heading}</h3>")
            if content:
                cleaned_content = _clean_html_description(content)
                if cleaned_content:
                    plain_parts.append(cleaned_content)
                html_parts.append(content)

    # 4. Additional section (e.g. about the company, benefits)
    add_plain = raw.get("additionalPlain")
    add_html = raw.get("additional")
    if add_plain:
        plain_parts.append(add_plain.strip())
    elif add_html:
        plain_parts.append(_clean_html_description(add_html))
    if add_html:
        html_parts.append(add_html)

    full_plain = "\n\n".join(p for p in plain_parts if p).strip()
    full_html = "\n".join(html_parts).strip()
    return full_plain, full_html


class LeverJobProvider:
    """
    Production-grade adapter for Lever Job Board API.
    Interacts directly with public JSON endpoints:
    https://api.lever.co/v0/postings/{company}?mode=json
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._timeout = float(getattr(self._settings, "LEVER_REQUEST_TIMEOUT_SECONDS", 15))

    async def fetch_company_openings(self, board_token: str) -> list[dict]:
        """
        Fetches all currently published openings for a given Lever board token.
        Endpoint: GET https://api.lever.co/v0/postings/{board_token}?mode=json
        Raises LeverNetworkError on connection failure / timeout.
        """
        clean_token = board_token.strip().lower()
        url = f"{BASE_URL}/{clean_token}?mode=json"
        headers = {
            "User-Agent": "RoleRadar-DirectATS/1.0 (+https://roleradar.internal)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    logger.warning(f"Lever board '{clean_token}' returned 404 Not Found.")
                    return []
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    return data
                return []
        except httpx.TimeoutException as exc:
            logger.error(f"Timeout fetching Lever board '{clean_token}': {exc}")
            raise LeverNetworkError(f"Timeout connecting to Lever board '{clean_token}'") from exc
        except (httpx.HTTPError, httpx.RequestError) as exc:
            logger.error(f"HTTP error fetching Lever board '{clean_token}': {exc}")
            raise LeverNetworkError(f"HTTP failure fetching Lever board '{clean_token}': {str(exc)}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error fetching Lever board '{clean_token}': {exc}")
            raise LeverProviderError(f"Unexpected failure: {str(exc)}") from exc

    async def fetch_specific_opening(self, board_token: str, job_id: str) -> dict | None:
        """
        Lightweight check of a specific requisition status.
        Endpoint: GET https://api.lever.co/v0/postings/{board_token}/{job_id}
        Returns raw job dict if active, None if 404/closed.
        """
        clean_token = board_token.strip().lower()
        clean_job_id = str(job_id).strip()
        url = f"{BASE_URL}/{clean_token}/{clean_job_id}"
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

    def normalize_lever_job(
        self,
        raw: dict,
        board_token: str,
        company_name: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Normalizes a raw Lever API response item into the canonical Opportunity model.
        Strictly satisfies all product requirements:
        - Specific requisition URL evaluated through url_classifier
        - Zero date fabrication (posted_at only from createdAt epoch in ms)
        - Reconstructed comprehensive JD text
        - Country & India relevance based on opportunity location
        - Conservative fresher/seniority classification
        - Extraction of skills from raw description
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        job_id = str(raw.get("id") or "").strip()
        title = (raw.get("text") or "").strip()
        resolved_company = company_name or board_token.title()

        categories = raw.get("categories") or {}
        commitment = categories.get("commitment") if isinstance(categories, dict) else None
        department = categories.get("department") if isinstance(categories, dict) else None
        team = categories.get("team") if isinstance(categories, dict) else None

        # Location extraction: prioritize categories.location, fallback to allLocations
        location = ""
        if isinstance(categories, dict):
            location = (categories.get("location") or "").strip()
            if not location:
                all_locs = categories.get("allLocations") or []
                if isinstance(all_locs, list) and all_locs:
                    location = "; ".join(str(l).strip() for l in all_locs if str(l).strip())

        if not location:
            location = "Not specified"

        # Remote check
        workplace_type = str(raw.get("workplaceType") or "").lower()
        is_remote = (
            workplace_type == "remote"
            or "remote" in location.lower()
            or "remote" in title.lower()
        )

        # Reconstruct description
        clean_desc, raw_html = _build_lever_description(raw)
        if not clean_desc:
            clean_desc = title

        # Direct Application URL Safety:
        # Evaluate applyUrl first. If absent or non-direct, check hostedUrl explicitly.
        # hostedUrl must NEVER bypass direct-requisition validation.
        raw_apply = (raw.get("applyUrl") or "").strip()
        raw_hosted = (raw.get("hostedUrl") or "").strip()

        chosen_url = ""
        url_type = ApplicationUrlType.INVALID
        url_reason = "Missing application URL."

        if raw_apply:
            apply_type, apply_reason = classify_application_url(raw_apply, company=resolved_company)
            if apply_type == ApplicationUrlType.DIRECT_REQUISITION:
                chosen_url = raw_apply
                url_type = apply_type
                url_reason = apply_reason
            elif raw_hosted:
                hosted_type, hosted_reason = classify_application_url(raw_hosted, company=resolved_company)
                if hosted_type == ApplicationUrlType.DIRECT_REQUISITION:
                    chosen_url = raw_hosted
                    url_type = hosted_type
                    url_reason = hosted_reason
                else:
                    chosen_url = raw_apply
                    url_type = apply_type
                    url_reason = apply_reason
            else:
                chosen_url = raw_apply
                url_type = apply_type
                url_reason = apply_reason
        elif raw_hosted:
            hosted_type, hosted_reason = classify_application_url(raw_hosted, company=resolved_company)
            chosen_url = raw_hosted
            url_type = hosted_type
            url_reason = hosted_reason

        source_url = raw_hosted or raw_apply or ""
        apply_url = chosen_url
        is_direct_apply = (url_type == ApplicationUrlType.DIRECT_REQUISITION)

        # Verification Status Invariant:
        # Only opportunities with verified DIRECT_REQUISITION URLs may become VERIFIED_ACTIVE.
        if is_direct_apply:
            verification_status = OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
            verification_reason = f"Authoritatively published on Lever {board_token} board"
        elif url_type == ApplicationUrlType.INVALID:
            verification_status = OpportunityLifecycleStatus.INVALID.value
            verification_reason = f"Rejected invalid application URL: {url_reason}"
        else:
            verification_status = OpportunityLifecycleStatus.PENDING_VERIFICATION.value
            verification_reason = f"Non-direct requisition URL ({url_type.value}): {url_reason}"

        # Date normalization: NO FABRICATION RULE
        # Lever provides createdAt as an epoch timestamp in milliseconds
        created_at_ms = raw.get("createdAt")
        posted_at_iso = None
        posted_days_ago = 0
        if created_at_ms and isinstance(created_at_ms, (int, float)) and created_at_ms > 0:
            try:
                dt = datetime.fromtimestamp(created_at_ms / 1000.0, tz=timezone.utc)
                posted_at_iso = dt.isoformat()
                posted_days_ago = max(0, (now - dt).days)
            except Exception:
                posted_at_iso = None
                posted_days_ago = 0

        # Lever does not provide an updated_at field; leave None to avoid date fabrication
        updated_at_iso = None

        # Internship and suitability classification
        is_intern = is_internship_opportunity(
            title=title,
            commitment=commitment,
            department=department,
            team=team,
        )
        job_type = "internship" if is_intern else "full_time"

        classification = classify_opportunity(
            title=title,
            description=clean_desc,
            experience_min=0 if is_intern else None,
            experience_max=2 if is_intern else None,
            job_type_hint="internship" if is_intern else "",
        )

        # Country extraction and India relevance
        country = extract_country_from_location(location)
        is_india = is_india_opportunity(location, clean_desc)

        # Skills extraction from text
        extracted_skills = extract_skills_from_text(f"{title}\n{clean_desc}")

        canonical_id = f"lever_{board_token.lower()}_{job_id}"

        return {
            "id": canonical_id,
            "source": "lever",
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
            "country": country,
            "location": location,
            "is_remote": is_remote,
            "is_india_opportunity": is_india,
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": False,
            "stipend_min": None,
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
            "apply_url": apply_url,
            "source_url": source_url,
            "verification_status": verification_status,
            "verified_at": now_iso,
            "verification_reason": verification_reason,
            "verification_method": "lever_api_direct",
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
        Synchronizes all openings for a Lever board token.
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
        except LeverNetworkError as exc:
            logger.warning(f"Network error during Lever sync for {clean_token}: {exc}. Retaining previous state.")
            stats["errors"].append(f"Network error: {str(exc)}")
            return stats
        except Exception as exc:
            logger.error(f"Unexpected error during Lever sync for {clean_token}: {exc}. Retaining previous state.")
            stats["errors"].append(f"Unexpected error: {str(exc)}")
            return stats

        stats["fetched"] = len(raw_jobs)
        current_job_ids = set()
        active_normalized = []

        for item in raw_jobs:
            jid = str(item.get("id") or "").strip()
            if not jid:
                continue
            current_job_ids.add(jid)

            job_doc = self.normalize_lever_job(item, clean_token, company_name=company_name, now=now)

            # Check if direct requisition
            if job_doc.get("url_type") == ApplicationUrlType.DIRECT_REQUISITION.value:
                active_normalized.append(job_doc)
                if job_doc.get("job_type") == "internship":
                    stats["internships"] += 1

        stats["verified_active"] = len(active_normalized)

        # Step 2: Handle Disappeared Listings (Authoritative Closure)
        # Query existing stored active records for this Lever board
        existing_cursor = db[Collections.JOBS].find({
            "source": "lever",
            "company_board": clean_token,
            "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        })
        existing_active = await existing_cursor.to_list(length=5000)

        for old_job in existing_active:
            old_jid = old_job.get("source_job_id")
            if old_jid and old_jid not in current_job_ids:
                # Authoritative disappearance: employer removed posting from Lever
                await db[Collections.JOBS].update_one(
                    {"id": old_job["id"]},
                    {
                        "$set": {
                            "verification_status": OpportunityLifecycleStatus.CLOSED.value,
                            "last_verified_at": now_iso,
                            "verification_reason": f"Disappeared from employer's authoritative Lever {clean_token} feed.",
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
            f"Lever sync [{clean_token}]: {stats['fetched']} fetched, "
            f"{stats['verified_active']} active, {stats['closed']} closed, {stats['internships']} internships."
        )
        return stats
