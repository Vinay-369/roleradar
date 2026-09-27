"""
SmartRecruiters Direct Live Opportunity Provider Adapter.
Uses documented, unauthenticated public Postings API:
- List openings: GET https://api.smartrecruiters.com/v1/companies/{company}/postings
- Specific opening: GET https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}

Strictly adheres to RoleRadar Direct Requisition Policies:
1. Generates DIRECT_REQUISITION application URLs pointing directly to employer requisitions.
2. Employs authoritative provider inventory diffing:
   - Disappeared listings on successful sync -> CLOSED
   - Transient network/provider failures -> retain state, never close jobs destructively
3. Zero Date Fabrication: posted_at populated strictly from releasedDate; updated_at preserved only if provided.
4. Country and India relevance based strictly on opportunity location geography (never description boilerplate).
5. Categorical experience level preserved (entry_level, associate, mid_senior_level, director).
   Zero fabricated numeric experience bounds (experience_min=None unless explicitly known or is internship).
6. Conservative fresher and internship classification.
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
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import OpportunityLifecycleStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://api.smartrecruiters.com/v1/companies"


class SmartRecruitersProviderError(Exception):
    """Base error for SmartRecruiters provider failures."""
    pass


class SmartRecruitersNetworkError(SmartRecruitersProviderError):
    """Raised when a network or timeout error occurs during fetch."""
    pass


def _clean_html_description(html_text: str | None) -> str:
    """
    Strips HTML tags, unescapes all character entities, transforms bullet/separator
    artifacts (such as \u00d8 / 'Ø' / middle dot \u00b7 / replacement characters) into readable markdown bullets,
    and cleanly partitions embedded subheadings.
    """
    if not html_text:
        return ""
    t = html.unescape(html_text)
    # Insert newlines before common inline section headers when embedded in prose
    t = re.sub(
        r"(?<=[^\n])\s*(?=\b(?:(?:Tasks\s*(?:\/|&)\s*)?Responsibilities|Expected\s+skill\s*set|Expected\s+skills|Good\s+to\s+have|Nice\s+to\s+have|Key\s+Skills|Required\s+Skills|Qualifications|Requirements)\s*:)",
        "\n\n",
        t,
        flags=re.I,
    )
    # Ensure colon after inline header is followed by newline/bullet
    t = re.sub(
        r"(\b(?:(?:Tasks\s*(?:\/|&)\s*)?Responsibilities|Expected\s+skill\s*set|Expected\s+skills|Good\s+to\s+have|Nice\s+to\s+have|Key\s+Skills|Required\s+Skills|Qualifications|Requirements)\s*:)\s*(?=[A-Za-z0-9])",
        r"\1\n- ",
        t,
        flags=re.I,
    )
    # Convert bullet and separator artifacts (e.g. Ø, \ufffd, •, ·, \u00b7, \uf0b7, \uf0a7, \u25aa, \u25b6, \u25c6) into clean markdown bullets
    t = re.sub(r"[\s\xa0]*[\u00d8\ufffd•·\u00b7\uf0b7\uf0a7\u25aa\u25b6\u25c6][\s\xa0]*", "\n- ", t)
    # Convert HTML line breaks and list items to proper newlines
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<li>", "\n- ", t, flags=re.I)
    t = re.sub(r"</li>", "\n", t, flags=re.I)
    t = re.sub(r"</(?:p|div|tr|h\d)>", "\n\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    # Normalize spaces per line
    lines = [re.sub(r"[\t\xa0 ]+", " ", l).strip() for l in t.split("\n")]
    clean = "\n".join(lines)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean


from app.modules.jobs.location_normalization import normalize_location_string


def is_internship_opportunity(
    title: str,
    type_of_employment: dict | str | None = None,
    experience_level: dict | str | None = None,
) -> bool:
    """
    Classifies whether a SmartRecruiters listing is an internship.
    Strictly checks:
    1. Structured typeOfEmployment (id == 'internship' or label contains 'intern')
    2. Structured experienceLevel (id == 'internship')
    3. Explicit title markers (e.g. 'Intern', 'Internship', 'Trainee', 'Apprentice')
    4. Guards against Senior/Lead/Manager roles.
    """
    if isinstance(type_of_employment, dict):
        emp_id = str(type_of_employment.get("id") or "").lower()
        emp_label = str(type_of_employment.get("label") or "").lower()
        return emp_id == "internship" or "intern" in emp_label
    if isinstance(type_of_employment, str) and type_of_employment.strip():
        return "intern" in type_of_employment.lower()

    if isinstance(experience_level, dict):
        if str(experience_level.get("id") or "").lower() == "internship":
            return True
    elif isinstance(experience_level, str) and "intern" in experience_level.lower():
        return True

    title_lower = title.lower().strip()

    # Disqualify senior / leadership roles from being marked as internships
    senior_markers = [
        "senior", "sr.", "lead", "principal", "staff", "director",
        "manager", "head of", "vp", "vice president", "architect",
    ]
    if any(re.search(rf"\b{re.escape(sm)}\b", title_lower) for sm in senior_markers):
        return False

    # Use title markers only when structured employment and experience types are absent.
    intern_patterns = [
        r"\bintern\b",
        r"\binternship\b",
        r"\binterns\b",
        r"\bgraduate\s+intern\b",
        r"\bsummer\s+intern\b",
        r"\bengineering\s+intern\b",
        r"\bstudent\s+intern\b",
        r"\bapprentice\b",
        r"\bapprenticeship\b",
    ]
    return any(re.search(p, title_lower) for p in intern_patterns)


FORBIDDEN_ATS_METADATA_REGEX = re.compile(
    r"^\s*(?:tariff\s*area|legal\s*entity(?:\s*\(acronym\))?|global\s*salary(?:\s*level)?|division(?:\s*full\s*name|\s*identifiers)?|local\s*grade|cost\s*center|entity\s*acronym|direct\s*or\s*indirect|working\s*(?:location|country|hours)|position\s*type|brands)\s*[:\-].*$",
    re.IGNORECASE | re.MULTILINE,
)


def _filter_candidate_facing_text(text: str) -> str:
    if not text:
        return ""
    filtered = FORBIDDEN_ATS_METADATA_REGEX.sub("", text)
    filtered = re.sub(r"\n{3,}", "\n\n", filtered)
    return filtered.strip()


def _build_smartrecruiters_description(raw: dict) -> tuple[str, str]:
    """
    Reconstructs complete description text and HTML structure from SmartRecruiters payload.
    Supports both detailed jobAd payload and list item fallback.
    Filters out internal ATS/HR administration fields (Tariff Area, Legal Entity, Local Grade, etc.).
    """
    job_ad = raw.get("jobAd") or {}
    sections = job_ad.get("sections") if isinstance(job_ad, dict) else {}

    plain_parts: list[str] = []
    html_parts: list[str] = []

    if isinstance(sections, dict) and sections:
        section_order = [
            ("companyDescription", "About Company"),
            ("jobDescription", "Job Description"),
            ("qualifications", "Qualifications"),
            ("additionalInformation", "Additional Information"),
        ]
        for key, default_title in section_order:
            sec = sections.get(key)
            if isinstance(sec, dict):
                text = sec.get("text")
                title = sec.get("title") or default_title
                if text and isinstance(text, str) and text.strip():
                    cleaned = _clean_html_description(text)
                    candidate_clean = _filter_candidate_facing_text(cleaned)
                    if candidate_clean:
                        plain_parts.append(f"## {title}\n{candidate_clean}")
                        html_parts.append(f"<h3>{title}</h3><div>{text}</div>")

    if plain_parts:
        return "\n\n".join(plain_parts), "\n".join(html_parts)

    # Fallback to summary built from structured list item metadata
    name = raw.get("name") or "Opportunity"
    company_dict = raw.get("company") or {}
    company_name = company_dict.get("name") if isinstance(company_dict, dict) else "Employer"
    function_dict = raw.get("function") or {}
    function_label = function_dict.get("label") if isinstance(function_dict, dict) else ""
    industry_dict = raw.get("industry") or {}
    industry_label = industry_dict.get("label") if isinstance(industry_dict, dict) else ""
    emp_dict = raw.get("typeOfEmployment") or {}
    emp_label = emp_dict.get("label") if isinstance(emp_dict, dict) else ""

    summary_lines = [
        f"{name} at {company_name}.",
        f"Role Function: {function_label or 'Not specified'}.",
        f"Industry: {industry_label or 'Technology'}.",
        f"Employment Type: {emp_label or 'Full-time'}.",
    ]

    custom_fields = raw.get("customField")
    if isinstance(custom_fields, list):
        for cf in custom_fields:
            if isinstance(cf, dict) and cf.get("fieldLabel") and cf.get("valueLabel"):
                label = str(cf["fieldLabel"])
                # Exclude internal ATS administration metadata
                if not re.search(r"tariff\s*area|legal\s*entity|global\s*salary|division|local\s*grade|cost\s*center|entity\s*acronym", label, re.I):
                    summary_lines.append(f"{label}: {cf['valueLabel']}")

    summary = "\n".join(summary_lines)
    html_summary = f"<p>{'<br/>'.join(summary_lines)}</p>"
    return summary, html_summary


class SmartRecruitersJobProvider:
    """
    Production-grade adapter for the SmartRecruiters Job Board API.
    Provides unauthenticated public synchronization, authoritative lifecycle diffing,
    and strict direct requisition URL enforcement.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._timeout = float(getattr(self._settings, "SMARTRECRUITERS_REQUEST_TIMEOUT_SECONDS", 15))

    async def fetch_company_openings(
        self,
        board_token: str,
        country: str | None = None,
        limit_per_page: int = 100,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Fetches all currently published openings for a given SmartRecruiters company identifier.
        Paginates through results until complete.
        Raises SmartRecruitersNetworkError on connection failure / timeout / 5xx / 429.
        """
        clean_token = (board_token or "").strip()
        if not clean_token:
            return []

        all_postings: list[dict[str, Any]] = []
        offset = 0

        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            for page in range(max_pages):
                url = f"{BASE_URL}/{clean_token}/postings"
                params: dict[str, Any] = {"limit": limit_per_page, "offset": offset}
                if country:
                    params["country"] = country

                try:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 404:
                        logger.warning(f"SmartRecruiters board '{clean_token}' returned 404 Not Found.")
                        return []
                    if resp.status_code == 429:
                        logger.error(f"Rate limited (429) on SmartRecruiters board '{clean_token}'.")
                        raise SmartRecruitersNetworkError(f"Rate limit exceeded (429) for SmartRecruiters board '{clean_token}'")
                    if resp.status_code >= 500:
                        logger.error(f"Server error ({resp.status_code}) on SmartRecruiters board '{clean_token}'.")
                        raise SmartRecruitersNetworkError(f"SmartRecruiters server error ({resp.status_code}) for '{clean_token}'")

                    resp.raise_for_status()
                    data = resp.json()

                    if not isinstance(data, dict):
                        logger.warning(f"Unexpected non-dict response for SmartRecruiters board '{clean_token}'.")
                        return all_postings

                    content = data.get("content") or []
                    if not isinstance(content, list) or not content:
                        break

                    all_postings.extend(content)
                    total_found = data.get("totalFound", len(all_postings))

                    offset += len(content)
                    if offset >= total_found or len(content) < limit_per_page:
                        break

                except httpx.TimeoutException as exc:
                    logger.error(f"Timeout fetching SmartRecruiters board '{clean_token}': {exc}")
                    raise SmartRecruitersNetworkError(f"Timeout connecting to SmartRecruiters board '{clean_token}'") from exc
                except httpx.HTTPError as exc:
                    logger.error(f"HTTP error fetching SmartRecruiters board '{clean_token}': {exc}")
                    raise SmartRecruitersNetworkError(f"HTTP failure fetching SmartRecruiters board '{clean_token}': {str(exc)}") from exc
                except Exception as exc:
                    if isinstance(exc, SmartRecruitersProviderError):
                        raise
                    logger.error(f"Unexpected error fetching SmartRecruiters board '{clean_token}': {exc}")
                    raise SmartRecruitersProviderError(f"Unexpected failure: {str(exc)}") from exc

        return all_postings

    async def fetch_specific_opening(
        self,
        board_token: str,
        job_id: str,
    ) -> dict[str, Any] | None:
        """
        Fetches the complete single-opening payload from SmartRecruiters, including jobAd sections.
        Returns None if opening is 404 or closed.
        """
        clean_token = (board_token or "").strip()
        clean_id = str(job_id or "").strip()
        if not clean_token or not clean_id:
            return None

        url = f"{BASE_URL}/{clean_token}/postings/{clean_id}"
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return None
                if resp.status_code >= 400:
                    return None
                data = resp.json()
                return data if isinstance(data, dict) else None
            except Exception as exc:
                logger.warning(f"Could not fetch SmartRecruiters specific opening {clean_token}/{clean_id}: {exc}")
                return None

    def normalize_smartrecruiters_job(
        self,
        raw: dict[str, Any],
        board_token: str,
        company_name: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Normalizes a raw SmartRecruiters API response item into the canonical Opportunity model.
        Strictly satisfies all product requirements:
        - Specific requisition URL evaluated through classify_application_url()
        - Zero date fabrication (posted_at only from releasedDate ISO timestamp)
        - Reconstructed comprehensive JD text
        - Country & India relevance based on opportunity location geography
        - Conservative fresher/seniority classification preserving categorical levels
        - Zero numeric experience fabrication for full-time roles (experience_min=None)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        job_id = str(raw.get("id") or "").strip()
        title = (raw.get("name") or "").strip()

        # Company resolution
        raw_company = raw.get("company") or {}
        comp_from_raw = raw_company.get("name") if isinstance(raw_company, dict) else None
        resolved_company = company_name or comp_from_raw

        # Location extraction
        loc_data = raw.get("location") or {}
        location = ""
        country_code = ""
        is_remote_loc = False
        is_hybrid_loc = False

        if isinstance(loc_data, dict):
            location = (loc_data.get("fullLocation") or "").strip()
            if not location:
                city = (loc_data.get("city") or "").strip()
                region = (loc_data.get("region") or "").strip()
                country = (loc_data.get("country") or "").strip()
                parts = [p for p in [city, region, country] if p]
                location = ", ".join(parts)
            country_code = str(loc_data.get("country") or "").strip().lower()
            is_remote_loc = bool(loc_data.get("remote"))
            is_hybrid_loc = bool(loc_data.get("hybrid"))

        location = normalize_location_string(location) if location else None

        # Workplace mode
        title_lower = title.lower()
        is_remote = is_remote_loc if isinstance(loc_data, dict) and isinstance(loc_data.get("remote"), bool) else None
        is_hybrid = is_hybrid_loc if isinstance(loc_data, dict) and isinstance(loc_data.get("hybrid"), bool) else None
        workplace_type = "REMOTE" if is_remote else ("HYBRID" if is_hybrid else ("ON_SITE" if is_remote is False and is_hybrid is False else None))

        # Description construction
        clean_desc, raw_html = _build_smartrecruiters_description(raw)

        # Direct Application URL Safety:
        # Standard SmartRecruiters requisition patterns:
        # postingUrl: https://jobs.smartrecruiters.com/{company}/{job_id}
        # applyUrl: https://jobs.smartrecruiters.com/{company}/{job_id}/apply
        raw_apply = (raw.get("applyUrl") or "").strip()
        raw_posting = (raw.get("postingUrl") or "").strip()

        chosen_url = ""
        url_type = ApplicationUrlType.INVALID
        url_reason = "Missing application URL."

        if raw_apply:
            apply_type, apply_reason = classify_application_url(raw_apply, company=resolved_company)
            if apply_type == ApplicationUrlType.DIRECT_REQUISITION:
                chosen_url = raw_apply
                url_type = apply_type
                url_reason = apply_reason
            elif raw_posting:
                posting_type, posting_reason = classify_application_url(raw_posting, company=resolved_company)
                if posting_type == ApplicationUrlType.DIRECT_REQUISITION:
                    chosen_url = raw_posting
                    url_type = posting_type
                    url_reason = posting_reason
                else:
                    chosen_url = raw_apply
                    url_type = apply_type
                    url_reason = apply_reason
            else:
                chosen_url = raw_apply
                url_type = apply_type
                url_reason = apply_reason
        elif raw_posting:
            posting_type, posting_reason = classify_application_url(raw_posting, company=resolved_company)
            chosen_url = raw_posting
            url_type = posting_type
            url_reason = posting_reason

        source_url = raw_posting or raw_apply or ""
        apply_url = chosen_url
        is_direct_apply = (url_type == ApplicationUrlType.DIRECT_REQUISITION)

        if is_direct_apply:
            verification_status = OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
            verification_reason = f"Authoritatively published on SmartRecruiters {board_token} board"
        else:
            verification_status = OpportunityLifecycleStatus.PENDING_VERIFICATION.value
            verification_reason = f"Application URL safety check failed: {url_reason}"

        # Timestamps: Zero Date Fabrication
        released_date = raw.get("releasedDate")
        posted_at_iso: str | None = None
        posted_days_ago = None

        if released_date and isinstance(released_date, str):
            try:
                dt = datetime.fromisoformat(released_date.replace("Z", "+00:00"))
                posted_at_iso = dt.isoformat()
                posted_days_ago = max(0, (now - dt).days)
            except Exception:
                posted_at_iso = released_date

        # Metadata parsing
        type_of_emp = raw.get("typeOfEmployment")
        exp_level = raw.get("experienceLevel")
        exp_level_id = str(exp_level.get("id") if isinstance(exp_level, dict) else exp_level or "").lower()
        exp_level_label = exp_level.get("label") if isinstance(exp_level, dict) else str(exp_level or "")
        emp_type_label = type_of_emp.get("label") if isinstance(type_of_emp, dict) else str(type_of_emp or "")

        # Internship classification
        is_intern = is_internship_opportunity(title, type_of_emp, exp_level)
        from app.modules.jobs.taxonomy import normalize_employment_type
        job_type = normalize_employment_type(type_of_emp, title, classified_internship=is_intern)

        # Seniority markers
        senior_markers = [
            "senior", "sr.", "lead", "staff", "principal", "manager",
            "director", "head", "architect", "ii", "iii", "iv",
        ]
        is_senior = any(re.search(rf"\b{re.escape(sm)}\b", title_lower) for sm in senior_markers)

        # Fresher & Entry-Level Classification
        # Criteria:
        # 1. Internships are student/fresher friendly.
        # 2. explicit exp_level_id == 'entry_level' (without senior title).
        # 3. Titles explicitly with graduate engineer trainee, get, junior, campus.
        # RULE: Never classify undisclosed experience as fresher!
        is_grad = any(k in title_lower for k in ["graduate engineer", "trainee", "get", "campus", "junior"]) and not is_senior
        is_fresher = is_intern or (exp_level_id == "entry_level" and not is_senior) or is_grad

        # Country extraction and India relevance
        # If country_code == 'in', country is India
        if country_code == "in":
            country = "India"
        else:
            country = extract_country_from_location(location)

        is_india = (country == "India") or is_india_opportunity(location, clean_desc)

        # Industry & Function
        industry_data = raw.get("industry") or {}
        industry = industry_data.get("label") if isinstance(industry_data, dict) else "Technology"
        function_data = raw.get("function") or {}
        department = function_data.get("label") if isinstance(function_data, dict) else ""

        # Skills extraction via canonical requirement-aware taxonomy
        from app.modules.jobs.taxonomy import analyze_job_description
        reqs = analyze_job_description(clean_desc, title)
        skills_required = list(dict.fromkeys(reqs.must_have_skills or reqs.required_skills))
        skills_nice_to_have = list(dict.fromkeys(reqs.preferred_skills))

        canonical_id = f"smartrecruiters_{board_token.lower()}_{job_id}"

        # Candidate suitability
        suitability = CandidateSuitabilitySignal.UNKNOWN.value
        if is_intern:
            suitability = CandidateSuitabilitySignal.STUDENT.value
        elif is_fresher:
            suitability = CandidateSuitabilitySignal.FRESHER.value
        elif exp_level_id == "associate" or not is_senior:
            suitability = CandidateSuitabilitySignal.EARLY_CAREER.value
        elif is_senior:
            suitability = CandidateSuitabilitySignal.EXPERIENCED.value

        student_eligible = is_intern or (exp_level_id == "entry_level")
        fresher_eligible = is_fresher or (exp_level_id == "associate" and not is_senior)

        comp = extract_compensation_from_payload_and_text(
            text=f"{clean_desc} {raw_html or ''}",
            raw_payload=raw,
            is_internship=is_intern,
        )

        # Completeness evaluation
        from app.modules.jobs.completeness import evaluate_opportunity_completeness
        comp_eval = evaluate_opportunity_completeness({
            "title": title,
            "company": resolved_company,
            "location": location,
            "country": country,
            "is_india_opportunity": is_india,
            "opportunity_type": job_type.upper() if job_type else None,
            "description": clean_desc,
            "responsibilities": reqs.responsibilities,
            "qualifications": reqs.qualifications,
            "skills_required": skills_required,
            "skills_nice_to_have": skills_nice_to_have,
            "verification_status": verification_status,
            "apply_url": apply_url,
            "is_direct_apply": is_direct_apply,
            "salary_min": comp.salary_min,
            "salary_max": comp.salary_max,
            "stipend_min": comp.stipend_min,
            "stipend_max": comp.stipend_max,
            "compensation_text": comp.compensation_text,
            "experience_min": reqs.min_years_experience,
            "experience_max": reqs.max_years_experience,
        })

        return {
            "id": canonical_id,
            "source": "smartrecruiters",
            "source_id": job_id,
            "internal_source": "smartrecruiters",
            "source_job_id": job_id,
            "company_board": board_token.lower(),
            "title": title,
            "company": resolved_company,
            "industry": industry,
            "department": department,
            "description": clean_desc,
            "jd_text": clean_desc,
            "raw_html": raw_html,
            "skills_required": skills_required,
            "skills_nice_to_have": skills_nice_to_have,
            "responsibilities": reqs.responsibilities,
            "qualifications": reqs.qualifications,
            "structured_requirements": reqs.model_dump(mode="json"),
            "completeness_status": comp_eval.source_completeness.value,
            "recommendation_quality": comp_eval.recommendation_quality.value,
            "experience_min": reqs.min_years_experience,
            "experience_max": reqs.max_years_experience,
            "experience_text": reqs.experience_requirements,
            "experience_level": exp_level_label or "Undisclosed",
            "type_of_employment": emp_type_label or None,
            "employment_type": emp_type_label or None,
            "job_type": job_type,
            "country": country,
            "is_india_opportunity": is_india,
            "is_india_relevant": is_india,
            "location": location,
            "is_remote": is_remote,
            "workplace_type": workplace_type,
            "opportunity_type": "INTERNSHIP" if is_intern else "FULL_TIME",
            "salary_min": comp.salary_min,
            "salary_max": comp.salary_max,
            "salary_currency": comp.salary_currency,
            "salary_period": comp.salary_period,
            "salary_unit": comp.salary_unit,
            "salary_disclosed": comp.salary_disclosed,
            "stipend_min": comp.stipend_min,
            "stipend_max": comp.stipend_max,
            "stipend_currency": comp.stipend_currency,
            "stipend_period": comp.stipend_period,
            "stipend_unit": comp.stipend_unit,
            "compensation_type": comp.compensation_type,
            "compensation_text": comp.compensation_text,
            "internship_duration_months": raw.get("internshipDurationMonths"),
            "fresher_friendly": is_fresher,
            "posted_days_ago": posted_days_ago,
            "posted_at": posted_at_iso,
            "updated_at": None,
            "first_seen_at": now_iso,
            "last_seen_at": now_iso,
            "last_verified_at": now_iso,
            "apply_url": apply_url,
            "source_url": source_url,
            "is_direct_apply": is_direct_apply,
            "url_type": url_type.value,
            "verification_status": verification_status,
            "verification_reason": verification_reason,
            "verification_method": "smartrecruiters_api_direct",
            "candidate_suitability": suitability,
            "student_eligible": student_eligible,
            "fresher_eligible": fresher_eligible,
            "eligibility": {
                "status": "ELIGIBLE" if (fresher_eligible or student_eligible) else "UNKNOWN",
                "reasons": ["SmartRecruiters Student / Entry Level opening"] if (fresher_eligible or student_eligible) else ["Upload resume to evaluate detailed eligibility"],
                "checks": {
                    "experience": "PASS" if fresher_eligible else "UNKNOWN",
                    "education": "UNKNOWN",
                    "location": "PASS" if is_india else "UNKNOWN",
                    "opportunity_type": "PASS",
                },
                "realistic_fit": "GOOD" if (is_intern or (exp_level_id in ("entry_level", "associate") and not is_senior)) else "UNKNOWN",
                "fit_explanation": "Categorical SmartRecruiters entry-level / associate role." if fresher_eligible else "Upload your resume to see your personalized eligibility and match score.",
            },
        }

    async def sync_company_openings(
        self,
        db: AsyncIOMotorDatabase,
        board_token: str,
        company_name: str | None = None,
        country: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Authoritative Synchronization Protocol:
        1. Fetches current published openings from SmartRecruiters API.
        2. Invariant: Network / Timeout / 5xx / 429 errors log warnings and retain existing active state without closing jobs.
        3. Authoritative Reconciliation:
           - Currently published items -> upserted as VERIFIED_ACTIVE.
           - Omitted/disappeared items previously active -> transitioned to CLOSED.
        """
        clean_token = (board_token or "").strip()
        if not clean_token:
            return {"board": "", "fetched": 0, "verified_active": 0, "closed": 0, "internships": 0}

        if now is None:
            now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Step 1: Fetch
        try:
            raw_postings = await self.fetch_company_openings(clean_token, country=country)
        except SmartRecruitersNetworkError as exc:
            logger.warning(f"Network error during SmartRecruiters sync for {clean_token}: {exc}. Retaining previous state.")
            return {"board": clean_token, "fetched": 0, "verified_active": 0, "closed": 0, "internships": 0, "network_error": True}
        except Exception as exc:
            logger.error(f"Unexpected error during SmartRecruiters sync for {clean_token}: {exc}. Retaining previous state.")
            return {"board": clean_token, "fetched": 0, "verified_active": 0, "closed": 0, "internships": 0, "error": str(exc)}

        # Step 2: Normalize
        normalized_jobs: list[dict[str, Any]] = []
        fetched_ids: set[str] = set()
        internship_count = 0

        for item in raw_postings:
            if not isinstance(item, dict):
                continue
            job_id = str(item.get("id") or "").strip()
            if not job_id:
                continue

            job_doc = self.normalize_smartrecruiters_job(
                item,
                clean_token,
                company_name=company_name,
                now=now,
            )
            normalized_jobs.append(job_doc)
            fetched_ids.add(job_doc["id"])
            if job_doc.get("job_type") == "internship":
                internship_count += 1

        # Step 3: Authoritative Closure of Disappeared Listings
        # Query stored active records for this board
        cursor = db[Collections.JOBS].find(
            {
                "source": "smartrecruiters",
                "company_board": clean_token.lower(),
                "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
            },
            {"id": 1},
        )
        stored_active = await cursor.to_list(length=10000)
        stored_active_ids = {doc["id"] for doc in stored_active if "id" in doc}

        disappeared_ids = stored_active_ids - fetched_ids

        if disappeared_ids:
            logger.info(f"Transitioning {len(disappeared_ids)} SmartRecruiters jobs to CLOSED for {clean_token}")
            await db[Collections.JOBS].update_many(
                {"id": {"$in": list(disappeared_ids)}},
                {
                    "$set": {
                        "verification_status": OpportunityLifecycleStatus.CLOSED.value,
                        "is_active": False,
                        "closed_at": now_iso,
                        "last_verified_at": now_iso,
                        "verification_reason": f"Requisition no longer present on SmartRecruiters {clean_token} board",
                        "verification_method": "smartrecruiters_reconciliation",
                    }
                },
            )

        # Step 4: Upsert Active Opportunities
        active_jobs = [j for j in normalized_jobs if j.get("is_direct_apply")]
        if active_jobs:
            deduped_active = deduplicate_opportunities(active_jobs)
            for j in deduped_active:
                update_payload = dict(j)
                first_seen = update_payload.pop("first_seen_at", now_iso)
                await db[Collections.JOBS].update_one(
                    {"id": j["id"]},
                    {
                        "$set": update_payload,
                        "$setOnInsert": {"first_seen_at": first_seen},
                    },
                    upsert=True,
                )

        logger.info(
            f"SmartRecruiters sync [{clean_token}]: {len(raw_postings)} fetched, "
            f"{len(active_jobs)} active, {len(disappeared_ids)} closed, {internship_count} internships."
        )

        return {
            "board": clean_token,
            "fetched": len(raw_postings),
            "verified_active": len(active_jobs),
            "closed": len(disappeared_ids),
            "internships": internship_count,
        }


def clean_token_identifier(token: str) -> str:
    """Validates and cleans a SmartRecruiters company identifier token."""
    if not token or not isinstance(token, str):
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", token.strip())
    return cleaned


def normalize_smartrecruiters_job(
    raw: dict[str, Any],
    board_token: str,
    company_name: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Convenience module-level normalizer for a SmartRecruiters posting."""
    return SmartRecruitersJobProvider().normalize_smartrecruiters_job(
        raw=raw, board_token=board_token, company_name=company_name, now=now
    )

