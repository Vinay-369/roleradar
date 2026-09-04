"""
Direct Application URL Classifier.
Classifies application URLs into explicit semantic categories:
- DIRECT_REQUISITION: Verified direct job application/requisition page on employer ATS or careers portal.
- AGGREGATOR_REDIRECT: Third-party affiliate or aggregator click-tracking redirect (e.g. Adzuna redirect).
- CORPORATE_PORTAL: Top-level corporate homepage or general careers landing page without a specific requisition ID.
- SEARCH_RESULTS: Search query results page (e.g. LinkedIn search, Internshala search, URLs with search query params).
- INVALID: Malformed URL, missing scheme/host, placeholder domain (example.com, localhost), or vendor mismatch.
- UNVERIFIED: Ambiguous URL that cannot be confirmed as a direct requisition.

Conservative Policy:
Only DIRECT_REQUISITION is permitted for the public direct-apply discovery feed.
"""
from __future__ import annotations

from enum import Enum
import re
from urllib.parse import parse_qs, urlparse

KNOWN_ATS_DOMAINS = [
    "boards.greenhouse.io",
    "jobs.lever.co",
    "myworkdayjobs.com",
    "jobs.smartrecruiters.com",
    "applytojob.com",
    "jobs.ashbyhq.com",
    "bamboohr.com",
    "recruiting.ultipro.com",
    "icims.com",
    "taleo.net",
    "jobvite.com",
    "workable.com",
    "breezy.hr",
    "rippling-ats.com",
]

KNOWN_AGGREGATOR_REDIRECTS = [
    "adzuna.in/land/",
    "adzuna.com/land/",
    "jooble.org/desc/",
    "ziprecruiter.com/c/",
    "click.appcast.io",
    "appcast.io",
]

KNOWN_SEARCH_HOSTS = [
    "internshala.com",
    "linkedin.com",
    "wellfound.com",
    "indeed.com",
    "naukri.com",
    "glassdoor.com",
    "shine.com",
    "monster.com",
]

PLACEHOLDER_HOSTS = {
    "example.com",
    "example.org",
    "example.net",
    "localhost",
    "127.0.0.1",
    "test.com",
}

GENERIC_PATH_SEGMENTS = {
    "",
    "/",
    "/careers",
    "/careers/",
    "/jobs",
    "/jobs/",
    "/company/careers",
    "/company/careers/",
    "/in-en/careers",
    "/in-en/careers/",
    "/careers/india",
    "/careers/india/",
    "/about/careers",
    "/about/careers/",
    "/work-with-us",
    "/join-us",
}

SEARCH_QUERY_PARAMS = {"keywords", "q", "search", "query", "k"}


class ApplicationUrlType(str, Enum):
    DIRECT_REQUISITION = "DIRECT_REQUISITION"
    AGGREGATOR_REDIRECT = "AGGREGATOR_REDIRECT"
    CORPORATE_PORTAL = "CORPORATE_PORTAL"
    SEARCH_RESULTS = "SEARCH_RESULTS"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"


def _extract_brand_token(text: str | None) -> str:
    """Extracts the primary brand keyword from a company name (e.g. 'Flipkart Internet Pvt Ltd' -> 'flipkart')."""
    if not text:
        return ""
    cleaned = text.lower()
    # Strip common corporate suffixes
    cleaned = re.sub(r"\b(pvt|ltd|limited|private|inc|incorporated|corp|corporation|llc|technologies|software|solutions|services|systems|internet|india|global|group)\b", "", cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    tokens = cleaned.split()
    return tokens[0] if tokens else ""


def _extract_domain_tokens(netloc: str) -> list[str]:
    """Extracts alphanumeric tokens from hostname (e.g. 'careers.cred.club' -> ['careers', 'cred', 'club'])."""
    host = netloc.split(":")[0].lower()
    return [t for t in re.split(r"[^a-z0-9]", host) if t and t not in ("com", "org", "net", "io", "in", "co", "ai", "www")]


def classify_application_url(url: str | None, company: str | None = None) -> tuple[ApplicationUrlType, str]:
    """
    Deterministically classifies an application URL.
    Returns (ApplicationUrlType, explanation).
    """
    # 1. Null / Empty Check
    if not url or not isinstance(url, str):
        return ApplicationUrlType.INVALID, "Missing or empty application URL."

    cleaned_url = url.strip()
    if not cleaned_url:
        return ApplicationUrlType.INVALID, "Application URL is blank."

    # 2. Parse URL
    try:
        parsed = urlparse(cleaned_url)
    except Exception as exc:
        return ApplicationUrlType.INVALID, f"Malformed URL syntax: {exc}"

    if parsed.scheme not in ("http", "https"):
        return ApplicationUrlType.INVALID, f"Invalid scheme '{parsed.scheme}'. Scheme must be http or https."

    netloc = (parsed.netloc or "").lower().split(":")[0]
    if not netloc or "." not in netloc:
        return ApplicationUrlType.INVALID, f"Missing or invalid host in URL: '{netloc}'."

    # 3. Placeholder / Localhost Domain Check
    if netloc in PLACEHOLDER_HOSTS or netloc.endswith(".example.com"):
        return ApplicationUrlType.INVALID, f"Prohibited placeholder domain: '{netloc}'."

    path = (parsed.path or "").rstrip("/")
    path_with_slash = path + "/"
    query = parsed.query or ""
    full_url_lower = cleaned_url.lower()

    # 4. Aggregator Redirect Check
    for agg in KNOWN_AGGREGATOR_REDIRECTS:
        if agg in full_url_lower:
            return ApplicationUrlType.AGGREGATOR_REDIRECT, f"URL is a third-party aggregator redirect ({agg})."

    # 5. Search Results / Query Page Check
    if query:
        params = parse_qs(query)
        if any(p.lower() in SEARCH_QUERY_PARAMS for p in params):
            return ApplicationUrlType.SEARCH_RESULTS, "URL contains search query parameters."

    # Check search result aggregator paths
    for search_host in KNOWN_SEARCH_HOSTS:
        if netloc == search_host or netloc.endswith("." + search_host):
            # If path contains /jobs/search or /internships without a specific numeric/alphanumeric ID
            if "/search" in path or path in ("/internships", "/jobs", "/jobs/search", "/browse"):
                return ApplicationUrlType.SEARCH_RESULTS, f"URL is a search results page on {search_host}."
            if not re.search(r"/(?:detail|jobs|view)/[a-zA-Z0-9_\-]+", path):
                return ApplicationUrlType.SEARCH_RESULTS, f"URL lacks a specific requisition path on {search_host}."

    # 6. Company / Vendor Domain Mismatch Detection
    if company:
        company_brand = _extract_brand_token(company)
        domain_tokens = _extract_domain_tokens(netloc)
        is_known_multi_tenant_ats = any(ats in netloc for ats in KNOWN_ATS_DOMAINS)

        if company_brand and not is_known_multi_tenant_ats:
            # If domain tokens exist and none match company_brand
            # e.g. company 'Accenture' with domain 'razorpay.com'
            if domain_tokens and not any(company_brand in dt or dt in company_brand for dt in domain_tokens):
                # Check path as well (e.g. greenhouse.io/<company>)
                path_tokens = [p.lower() for p in re.split(r"[^a-z0-9]", path) if p]
                if not any(company_brand in pt for pt in path_tokens):
                    return ApplicationUrlType.INVALID, f"Vendor mismatch: Company '{company}' does not match URL domain '{netloc}'."

    # 7. Generic Corporate / Careers Portal Homepage Check
    normalized_path = path if path else "/"
    if normalized_path in GENERIC_PATH_SEGMENTS or path_with_slash in GENERIC_PATH_SEGMENTS:
        return ApplicationUrlType.CORPORATE_PORTAL, f"URL points to a generic careers homepage ('{path}') rather than a specific requisition."

    # If path only has a single generic segment like "/careers" or "/jobs" or "/locations/bangalore-india"
    if path.lower() in ("/careers", "/jobs", "/positions", "/openings", "/en/locations/bangalore-india", "/locations/bangalore-india"):
        return ApplicationUrlType.CORPORATE_PORTAL, f"URL is a generic portal path ('{path}')."

    # 8. Direct ATS Requisition Check
    # A. Multi-tenant ATS with specific requisition slug/ID
    for ats in KNOWN_ATS_DOMAINS:
        if ats in netloc:
            # Must have at least one specific path identifier beyond root
            segments = [s for s in path.split("/") if s]
            if len(segments) >= 2 or (len(segments) == 1 and re.search(r"\d+", segments[0])):
                return ApplicationUrlType.DIRECT_REQUISITION, f"Verified direct ATS requisition on {ats}."
            return ApplicationUrlType.CORPORATE_PORTAL, f"Top-level portal on {ats} without requisition slug."

    # B. Specific Requisition on Company's Own Careers Subdomain
    # Path contains specific job requisition markers with identifier (e.g., /jobs/1234, /requisition/99, /job/backend-dev-xyz)
    has_requisition_id = bool(
        re.search(r"/(?:jobs?|requisitions?|positions?|openings?|careers?|posting)/[a-zA-Z0-9_-]*(?:\d+|[a-f0-9]{8,}|[a-zA-Z]+-[a-zA-Z]+)", path, re.I)
    )

    if has_requisition_id:
        return ApplicationUrlType.DIRECT_REQUISITION, "Direct employer requisition URL with specific opening identifier."

    # 9. Conservative Fallback: If not definitively a direct requisition, classify as UNVERIFIED
    return ApplicationUrlType.UNVERIFIED, "URL path structure is ambiguous and cannot be confirmed as a direct requisition."
