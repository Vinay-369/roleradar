"""
Opportunity Verification & Lifecycle Engine.
Enforces the canonical lifecycle states for all published jobs and internships:
- PENDING_VERIFICATION: Newly ingested, awaiting validation or non-direct application URL.
- VERIFIED_ACTIVE: Verified with a valid direct application URL (DIRECT_REQUISITION), within freshness window (<=45d), active.
- STALE: Previously verified, but last verification is > 14 days old and needs re-verification.
- EXPIRED: Posting date or first_seen is > 45 days old.
- CLOSED: Provider signals or page checks confirm the position is closed/filled/404/410.
- INVALID: Missing, malformed, placeholder URL, search query page, generic homepage, or vendor mismatch.
- MARKET_BENCHMARK: Reference catalog/seed benchmark records (kept for role taxonomy & testing, excluded from live feed).

Rule: The opportunity discovery APIs publish ONLY VERIFIED_ACTIVE listings with url_type == DIRECT_REQUISITION.
Rule: HTTP 200 alone is never treated as proof that an opening is active.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from urllib.parse import urlparse

import httpx

from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url

MAX_FRESHNESS_DAYS = 45
STALE_THRESHOLD_DAYS = 14

CLOSED_CONTENT_MARKERS = [
    "no longer accepting applications",
    "this position has been closed",
    "position is closed",
    "job is closed",
    "role has been filled",
    "position filled",
    "job has expired",
    "listing has expired",
    "opening is no longer available",
    "this job is no longer available",
    "application is closed",
]

PLACEHOLDER_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "localhost",
    "127.0.0.1",
    "test.com",
}


class OpportunityLifecycleStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"
    INVALID = "INVALID"
    MARKET_BENCHMARK = "MARKET_BENCHMARK"


@dataclass
class VerificationResult:
    status: OpportunityLifecycleStatus
    reason: str
    verified_at: str
    method: str
    url_type: ApplicationUrlType = ApplicationUrlType.UNVERIFIED


def validate_apply_url(url: str | None) -> tuple[bool, str]:
    """Validates that an apply_url is syntactically valid and not a placeholder."""
    if url is None or not isinstance(url, str):
        return False, "Missing application URL."

    cleaned = url.strip()
    if not cleaned:
        return False, "Empty application URL."

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return False, "Malformed URL structure."

    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid URL scheme '{parsed.scheme}'. Must be http or https."

    netloc = (parsed.netloc or "").lower()
    if not netloc:
        return False, "Missing hostname in application URL."

    host = netloc.split(":")[0]

    if host in PLACEHOLDER_DOMAINS or host.endswith(".example.com"):
        return False, f"Placeholder domain '{host}' is prohibited."

    if "." not in host:
        return False, f"Invalid host '{host}' in application URL."

    return True, "URL syntax valid."


def check_content_for_closed_markers(text: str) -> str | None:
    """Detects explicit closed markers in JD or page content."""
    text_lower = text.lower()
    for marker in CLOSED_CONTENT_MARKERS:
        if marker in text_lower:
            return marker
    return None


async def probe_application_url(url: str, timeout_seconds: float = 3.0) -> tuple[int | None, str | None]:
    """
    Safely probes an application URL using HTTP HEAD or GET.
    Returns (status_code, error_message).
    Fail-safe: timeouts or network errors return None status rather than crashing.
    """
    headers = {
        "User-Agent": "RoleRadar-Verifier/1.0 (+https://roleradar.internal)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            try:
                resp = await client.head(url, headers=headers)
                if resp.status_code == 405:
                    resp = await client.get(url, headers=headers)
            except Exception:
                resp = await client.get(url, headers=headers)
            return resp.status_code, None
    except httpx.TimeoutException:
        return None, "Request timed out during verification probe"
    except httpx.HTTPError as exc:
        return None, f"HTTP probe error: {str(exc)}"
    except Exception as exc:
        return None, f"Probe connection error: {str(exc)}"


def verify_opportunity_sync(
    opportunity: dict,
    now: datetime | None = None,
    enforce_direct_apply: bool = True,
) -> VerificationResult:
    """
    Conservative deterministic verification of an opportunity:
    1. Core fields check (title, company)
    2. URL classification (DIRECT_REQUISITION, AGGREGATOR_REDIRECT, CORPORATE_PORTAL, SEARCH_RESULTS, INVALID)
    3. Vendor / company domain mismatch detection
    4. Provider status signals
    5. Freshness / Expiry evaluation (<= 45 days)
    6. Content closure markers
    7. Staleness evaluation (<= 14 days since verified_at)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # 1. Mandatory Core Fields
    title = (opportunity.get("title") or "").strip()
    company = (opportunity.get("company") or "").strip()
    if not title or not company:
        return VerificationResult(
            status=OpportunityLifecycleStatus.INVALID,
            reason="Missing mandatory title or company name.",
            verified_at=now_iso,
            method="schema_validation",
            url_type=ApplicationUrlType.INVALID,
        )

    # 2. Application URL Classification & Vendor Mismatch Check
    apply_url = opportunity.get("apply_url")
    url_type, url_reason = classify_application_url(apply_url, company=company)

    if url_type == ApplicationUrlType.INVALID:
        return VerificationResult(
            status=OpportunityLifecycleStatus.INVALID,
            reason=f"Invalid apply_url: {url_reason}",
            verified_at=now_iso,
            method="url_validation",
            url_type=url_type,
        )

    if url_type == ApplicationUrlType.SEARCH_RESULTS:
        return VerificationResult(
            status=OpportunityLifecycleStatus.INVALID,
            reason=f"Rejected search results URL: {url_reason}",
            verified_at=now_iso,
            method="url_classifier",
            url_type=url_type,
        )

    if url_type == ApplicationUrlType.CORPORATE_PORTAL:
        return VerificationResult(
            status=OpportunityLifecycleStatus.INVALID,
            reason=f"Rejected generic corporate/careers portal: {url_reason}",
            verified_at=now_iso,
            method="url_classifier",
            url_type=url_type,
        )

    if enforce_direct_apply and url_type != ApplicationUrlType.DIRECT_REQUISITION:
        # Aggregator redirects or unverified URLs cannot be published to the direct-apply feed
        return VerificationResult(
            status=OpportunityLifecycleStatus.PENDING_VERIFICATION,
            reason=f"Non-direct requisition URL ({url_type.value}): {url_reason}",
            verified_at=now_iso,
            method="url_classifier",
            url_type=url_type,
        )

    # 3. Provider Status Signals
    if opportunity.get("is_active") is False:
        return VerificationResult(
            status=OpportunityLifecycleStatus.CLOSED,
            reason="Provider explicitly reported listing as inactive.",
            verified_at=now_iso,
            method="provider_signal",
            url_type=url_type,
        )

    provider_status = str(opportunity.get("status") or "").lower()
    if provider_status in ("closed", "expired", "archived", "filled", "inactive"):
        return VerificationResult(
            status=OpportunityLifecycleStatus.CLOSED,
            reason=f"Provider status reported as '{provider_status}'.",
            verified_at=now_iso,
            method="provider_signal",
            url_type=url_type,
        )

    # 4. Freshness & Verification Recency Check
    source = opportunity.get("source")
    if source in ("greenhouse", "lever", "smartrecruiters"):
        last_verified_at = opportunity.get("last_verified_at")
        if last_verified_at:
            try:
                lv_dt = datetime.fromisoformat(last_verified_at.replace("Z", "+00:00"))
                verification_age_hours = max(0, (now - lv_dt).total_seconds() / 3600)
                max_verification_hours = float(opportunity.get("max_verification_age_hours") or 48)
                if verification_age_hours > max_verification_hours:
                    return VerificationResult(
                        status=OpportunityLifecycleStatus.STALE,
                        reason=f"Verification age ({int(verification_age_hours)}h) exceeds threshold ({int(max_verification_hours)}h); re-verification required.",
                        verified_at=now_iso,
                        method="verification_recency",
                        url_type=url_type,
                    )
            except (ValueError, TypeError):
                pass
    else:
        posted_at = opportunity.get("posted_at") or opportunity.get("first_seen_at")
        age_days: int | None = None
        if posted_at:
            try:
                p_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                age_days = max(0, (now - p_dt).days)
            except (ValueError, TypeError):
                pass

        if age_days is None:
            posted_days_ago = opportunity.get("posted_days_ago")
            if posted_days_ago is not None and isinstance(posted_days_ago, (int, float)):
                age_days = int(posted_days_ago)

        if age_days is not None and age_days > MAX_FRESHNESS_DAYS:
            return VerificationResult(
                status=OpportunityLifecycleStatus.EXPIRED,
                reason=f"Posting age ({age_days}d) exceeds maximum active threshold ({MAX_FRESHNESS_DAYS}d).",
                verified_at=now_iso,
                method="freshness_evaluation",
                url_type=url_type,
            )

    # 5. Closed Content Markers in JD / Description
    jd_content = f"{opportunity.get('title', '')} {opportunity.get('description', '')} {opportunity.get('jd_text', '')}"
    closed_marker = check_content_for_closed_markers(jd_content)
    if closed_marker:
        return VerificationResult(
            status=OpportunityLifecycleStatus.CLOSED,
            reason=f"Listing content contains closed marker: '{closed_marker}'.",
            verified_at=now_iso,
            method="content_signal",
            url_type=url_type,
        )

    # 6. Staleness Check
    last_verified = opportunity.get("last_verified_at") or opportunity.get("verified_at")
    if last_verified:
        try:
            last_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
            verified_age = (now - last_dt).days
            if verified_age > STALE_THRESHOLD_DAYS and opportunity.get("verification_status") != OpportunityLifecycleStatus.VERIFIED_ACTIVE.value:
                return VerificationResult(
                    status=OpportunityLifecycleStatus.STALE,
                    reason=f"Last verification was {verified_age} days ago (> {STALE_THRESHOLD_DAYS}d threshold).",
                    verified_at=now_iso,
                    method="staleness_evaluation",
                    url_type=url_type,
                )
        except (ValueError, TypeError):
            pass

    # All checks passed
    return VerificationResult(
        status=OpportunityLifecycleStatus.VERIFIED_ACTIVE,
        reason="Direct employer requisition URL validated, within freshness window, no closed signals.",
        verified_at=now_iso,
        method="rule_engine",
        url_type=url_type,
    )


async def verify_opportunity(
    opportunity: dict,
    check_http: bool = False,
    now: datetime | None = None,
    enforce_direct_apply: bool = True,
) -> VerificationResult:
    """
    Asynchronous verification pipeline with optional HTTP probing.
    Rule: HTTP 200 alone is never proof of active status; rule checks take precedence.
    """
    sync_result = verify_opportunity_sync(opportunity, now=now, enforce_direct_apply=enforce_direct_apply)
    if sync_result.status != OpportunityLifecycleStatus.VERIFIED_ACTIVE:
        return sync_result

    if not check_http:
        return sync_result

    apply_url = opportunity.get("apply_url")
    status_code, probe_err = await probe_application_url(apply_url)

    if status_code in (404, 410):
        return VerificationResult(
            status=OpportunityLifecycleStatus.CLOSED,
            reason=f"Application page returned HTTP {status_code} (Not Found / Gone).",
            verified_at=datetime.now(timezone.utc).isoformat(),
            method="http_probe",
            url_type=sync_result.url_type,
        )

    return sync_result
