"""
Deterministic Cross-Provider Opportunity Deduplication.
Normalizes company, title, location, and job_type to detect duplicate postings across providers
and merges them cleanly according to deterministic priority rules.
"""
from __future__ import annotations

import re
from typing import Any

from app.modules.jobs.verification import OpportunityLifecycleStatus

LEGAL_SUFFIXES = [
    r"\binc\.?\b",
    r"\bincorporated\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bllc\.?\b",
    r"\bltd\.?\b",
    r"\bpvt\.?\s*ltd\.?\b",
    r"\bpvt\.?\b",
    r"\bprivate\s+limited\b",
    r"\btechnologies\b",
    r"\bsoftware\b",
    r"\bsolutions\b",
    r"\bservices\b",
    r"\bsystems\b",
    r"\bglobal\b",
    r"\bgroup\b",
    r"\binternet\b",
    r"\bdigital\b",
    r"\bindia\b",
]

TITLE_NORMALIZATIONS = [
    (r"\bsr\.?\b", "senior"),
    (r"\bjr\.?\b", "junior"),
    (r"\bassoc\.?\b", "associate"),
    (r"\bdev\b", "developer"),
    (r"\beng\.?\b", "engineer"),
    (r"\bmgr\.?\b", "manager"),
]

LOCATION_SYNONYMS = {
    "bengaluru": "bangalore",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "madras": "chennai",
    "gurugram": "gurgaon",
}


def normalize_company(company: str | None) -> str:
    if not company:
        return "unknown"
    c = company.lower().strip()
    for pattern in LEGAL_SUFFIXES:
        c = re.sub(pattern, "", c)
    c = re.sub(r"[^\w\s]", "", c)
    return " ".join(c.split())


def normalize_title(title: str | None) -> str:
    if not title:
        return "unknown"
    t = title.lower().strip()
    # Normalize common abbreviations
    for pattern, replacement in TITLE_NORMALIZATIONS:
        t = re.sub(pattern, replacement, t)
    t = re.sub(r"[^\w\s]", "", t)
    return " ".join(t.split())


def normalize_location(location: str | None, is_remote: bool = False) -> str:
    if is_remote:
        return "remote"
    if not location:
        return "any"
    loc = location.lower().strip()
    loc = re.sub(r"[^\w\s]", "", loc)
    tokens = loc.split()
    normalized_tokens = [LOCATION_SYNONYMS.get(tok, tok) for tok in tokens]
    return " ".join(normalized_tokens)


def compute_dedup_key(company: str, title: str, location: str | None = None, job_type: str = "full_time", is_remote: bool = False) -> str:
    """Computes a deterministic string signature for an opportunity."""
    norm_comp = normalize_company(company)
    norm_title = normalize_title(title)
    norm_loc = normalize_location(location, is_remote=is_remote)
    norm_type = (job_type or "full_time").lower().strip()
    return f"{norm_comp}::{norm_title}::{norm_loc}::{norm_type}"


def is_direct_apply_url(url: str) -> bool:
    """Returns True if the URL appears to be a direct corporate careers portal rather than a third-party aggregator redirect."""
    url_lower = url.lower()
    aggregator_indicators = ["adzuna.", "indeed.", "monster.", "naukri.", "shine.", "ziprecruiter.", "linkedin.com/jobs/view/"]
    for ind in aggregator_indicators:
        if ind in url_lower:
            return False
    return "careers." in url_lower or "/careers" in url_lower or "/jobs" in url_lower or "workday" in url_lower or "greenhouse" in url_lower or "lever.co" in url_lower


def merge_two_opportunities(primary: dict, secondary: dict) -> dict:
    """
    Merges two duplicates into one canonical representation:
    - Retains VERIFIED_ACTIVE over non-active.
    - Prefers direct apply URLs over aggregators.
    - Unifies skills required & nice-to-have.
    - Takes the minimum (freshest) posted_days_ago.
    - Retains broader description if available.
    """
    merged = dict(primary)

    # 1. Lifecycle status precedence
    p_status = primary.get("verification_status")
    s_status = secondary.get("verification_status")
    if p_status != OpportunityLifecycleStatus.VERIFIED_ACTIVE and s_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE:
        merged["verification_status"] = s_status
        merged["verified_at"] = secondary.get("verified_at")
        merged["verification_reason"] = secondary.get("verification_reason")
        merged["verification_method"] = secondary.get("verification_method")

    # 2. Prefer direct apply URL
    p_url = primary.get("apply_url", "")
    s_url = secondary.get("apply_url", "")
    if not is_direct_apply_url(p_url) and is_direct_apply_url(s_url):
        merged["apply_url"] = s_url
        if not merged.get("source_url"):
            merged["source_url"] = p_url

    # 3. Union skills
    skills_req = list(dict.fromkeys(list(primary.get("skills_required", [])) + list(secondary.get("skills_required", []))))
    skills_nice = list(dict.fromkeys(list(primary.get("skills_nice_to_have", [])) + list(secondary.get("skills_nice_to_have", []))))
    # ensure no duplicate across req and nice
    skills_nice = [s for s in skills_nice if s not in skills_req]
    merged["skills_required"] = skills_req
    merged["skills_nice_to_have"] = skills_nice

    # 4. Freshest recency
    p_days = primary.get("posted_days_ago")
    s_days = secondary.get("posted_days_ago")
    if p_days is not None and s_days is not None:
        merged["posted_days_ago"] = min(p_days, s_days)
    elif s_days is not None:
        merged["posted_days_ago"] = s_days

    # 5. Longest description
    if len(secondary.get("description", "")) > len(primary.get("description", "")):
        merged["description"] = secondary["description"]
        merged["jd_text"] = secondary.get("jd_text", secondary["description"])

    return merged


def deduplicate_opportunities(opportunities: list[dict]) -> list[dict]:
    """Deduplicates a list of opportunities based on deterministic dedup keys."""
    groups: dict[str, dict] = {}
    for opp in opportunities:
        key = compute_dedup_key(
            company=opp.get("company", ""),
            title=opp.get("title", ""),
            location=opp.get("location"),
            job_type=opp.get("job_type", "full_time"),
            is_remote=opp.get("is_remote", False),
        )
        if key in groups:
            groups[key] = merge_two_opportunities(groups[key], opp)
        else:
            groups[key] = dict(opp)

    return list(groups.values())
