"""
Live job and internship provider via the JSearch API (RapidAPI / Google for Jobs).
Aggregates high-volume opportunities from LinkedIn, Indeed, Glassdoor, ZipRecruiter,
and Internshala with rich metadata:
- Transparent salary (LPA / Annual INR / USD)
- Monthly stipend for internships
- Application deadline / offer expiration end date
- Direct employer requisition URLs
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.modules.jobs.compensation_extractor import extract_compensation_details
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.taxonomy import extract_experience_bounds
from app.modules.jobs.url_classifier import classify_application_url
from app.modules.jobs.verification import verify_opportunity_sync

logger = logging.getLogger("roleradar.jobs.jsearch")

JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"
FRESHER_KEYWORDS = ["fresher", "entry level", "entry-level", "graduate", "trainee", "junior", "0-1 year", "intern"]


class JSearchJobProvider:
    """Fetches real-time jobs and internships with salary, stipend, and deadlines from JSearch."""

    name: str = "jsearch"

    def __init__(self, settings: Settings | None = None, api_key: str | None = None):
        self._settings = settings
        self._api_key = api_key or (getattr(settings, "JSEARCH_RAPIDAPI_KEY", None) if settings else None)

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def normalize_job(self, result: dict) -> dict:
        return self._transform(result)

    async def search(self, filters: dict) -> list[dict]:
        if not self.is_configured:
            logger.info("JSEARCH_RAPIDAPI_KEY is not configured; skipping JSearch live lookup.")
            return []

        role = filters.get("role") or (filters["target_roles"][0] if filters.get("target_roles") else None) or filters.get("title") or filters.get("skill") or "Software Engineer"
        location = filters.get("location") or filters.get("location_preset") or "India"
        is_internship = filters.get("job_type") == "internship" or filters.get("opportunity_type") == "INTERNSHIP"

        query_parts = []
        if is_internship:
            query_parts.append(f"{role} intern in {location}")
        else:
            query_parts.append(f"{role} in {location}")

        query_str = " ".join(query_parts)

        params: dict[str, Any] = {
            "query": query_str,
            "page": "1",
            "num_pages": "1",
            "date_posted": "all",
        }

        if is_internship:
            params["employment_types"] = "INTERN"

        headers = {
            "X-RapidAPI-Key": self._api_key.strip(),
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(JSEARCH_API_URL, params=params, headers=headers)
                if resp.status_code == 401 or resp.status_code == 403:
                    logger.warning("JSearch API key unauthorized or quota exceeded: HTTP %d", resp.status_code)
                    return []
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("JSearch live request failed: %s", exc)
            return []

        results = data.get("data", [])
        if not isinstance(results, list):
            return []

        limit = getattr(self._settings, "JSEARCH_RESULTS_PER_QUERY", 30)
        return [self._transform(r) for r in results[:limit] if isinstance(r, dict)]

    def _transform(self, result: dict) -> dict:
        title = (result.get("job_title") or "").strip()
        company = (result.get("employer_name") or "Unknown Company").strip()
        description = (result.get("job_description") or "").strip()
        city = result.get("job_city") or ""
        state = result.get("job_state") or ""
        country = result.get("job_country") or "India"
        location_parts = [p for p in [city, state, country] if p]
        location = ", ".join(location_parts) if location_parts else "India"

        is_remote = bool(result.get("job_is_remote")) or "remote" in description.lower() or "remote" in location.lower()
        emp_type = (result.get("job_employment_type") or "").upper()
        title_lower = title.lower()

        is_internship = emp_type == "INTERN" or "intern" in title_lower or "internship" in title_lower
        job_type = "internship" if is_internship else "full_time"
        opportunity_type = "INTERNSHIP" if is_internship else "FULL_TIME"

        fresher_friendly = is_internship or any(kw in title_lower or kw in description.lower() for kw in FRESHER_KEYWORDS)

        # 1. Application Deadline / End Date
        application_deadline = None
        raw_expiration = result.get("job_offer_expiration_datetime_utc")
        if raw_expiration and isinstance(raw_expiration, str) and raw_expiration.strip():
            try:
                dt = datetime.fromisoformat(raw_expiration.replace("Z", "+00:00"))
                application_deadline = dt.isoformat()
            except ValueError:
                application_deadline = raw_expiration.strip()

        # If API didn't return an expiration date, look for deadline text in the JD
        if not application_deadline:
            deadline_match = re.search(
                r"\b(?:apply\s+(?:by|before|until)|deadline|closing\s+date|last\s+date\s+to\s+apply)\s*[:\-]?\s*([A-Za-z0-9,\s\/\-]+(?:\d{4}|\d{2}))\b",
                description,
                re.IGNORECASE,
            )
            if deadline_match:
                application_deadline = deadline_match.group(1).strip()

        # 2. Compensation & Stipend Extraction
        min_sal = result.get("job_min_salary")
        max_sal = result.get("job_max_salary")
        sal_period = (result.get("job_salary_period") or "").upper()
        sal_curr = (result.get("job_salary_currency") or "INR").upper()

        salary_min = None
        salary_max = None
        stipend = None
        stipend_min = None
        stipend_max = None
        stipend_period = None
        salary_disclosed = False
        compensation_type = None
        compensation_text = None

        if is_internship:
            if min_sal is not None and sal_period in ("MONTH", "MONTHLY"):
                stipend_min = float(min_sal)
                stipend_max = float(max_sal) if max_sal is not None else stipend_min
                stipend = stipend_min
                stipend_period = "MONTH"
                salary_disclosed = True
                compensation_type = "STIPEND"
                compensation_text = f"₹{int(stipend_min):,} - ₹{int(stipend_max):,} / month" if stipend_max != stipend_min else f"₹{int(stipend_min):,} / month"
            elif min_sal is not None and sal_period in ("YEAR", "ANNUAL"):
                # Annual stipend converted to monthly
                stipend_min = round(float(min_sal) / 12, 0)
                stipend_max = round(float(max_sal) / 12, 0) if max_sal is not None else stipend_min
                stipend = stipend_min
                stipend_period = "MONTH"
                salary_disclosed = True
                compensation_type = "STIPEND"
                compensation_text = f"₹{int(stipend_min):,} / month"
        else:
            if min_sal is not None:
                if sal_curr == "INR":
                    salary_min = round(float(min_sal) / 100_000, 1) if float(min_sal) >= 10_000 else round(float(min_sal), 1)
                    salary_max = round(float(max_sal) / 100_000, 1) if max_sal is not None and float(max_sal) >= 10_000 else salary_min
                    compensation_text = f"₹{salary_min}–{salary_max} LPA" if salary_max != salary_min else f"₹{salary_min} LPA"
                else:
                    salary_min = round(float(min_sal), 1)
                    salary_max = round(float(max_sal), 1) if max_sal is not None else salary_min
                    compensation_text = f"{sal_curr} {salary_min:,} - {salary_max:,} / yr"
                salary_disclosed = True
                compensation_type = "SALARY"

        # Fallback to local compensation extractor if no structured compensation was returned by JSearch
        if not salary_disclosed:
            extracted = extract_compensation_details(f"{title} {description}")
            if extracted:
                if is_internship and extracted.get("stipend"):
                    stipend = extracted.get("stipend")
                    stipend_min = extracted.get("stipend_min") or stipend
                    stipend_max = extracted.get("stipend_max") or stipend
                    stipend_period = extracted.get("stipend_period") or "MONTH"
                    salary_disclosed = True
                    compensation_type = "STIPEND"
                    compensation_text = extracted.get("compensation_text")
                elif extracted.get("salary_min"):
                    salary_min = extracted.get("salary_min")
                    salary_max = extracted.get("salary_max")
                    salary_disclosed = True
                    compensation_type = "SALARY"
                    compensation_text = extracted.get("compensation_text")

        # 3. Freshness / Posted Date
        posted_days_ago = 0
        raw_posted = result.get("job_posted_at_datetime_utc")
        if raw_posted and isinstance(raw_posted, str):
            try:
                posted_dt = datetime.fromisoformat(raw_posted.replace("Z", "+00:00"))
                posted_days_ago = max(0, (datetime.now(timezone.utc) - posted_dt).days)
            except ValueError:
                pass

        required_experience = result.get("job_required_experience")
        required_months = required_experience.get("required_experience_in_months") if isinstance(required_experience, dict) else None
        api_experience_min = float(required_months) / 12 if isinstance(required_months, (int, float)) and required_months > 0 else None
        jd_experience_min, jd_experience_max = extract_experience_bounds(description, title)
        experience_min = jd_experience_min if jd_experience_min is not None else api_experience_min
        experience_max = jd_experience_max

        apply_url = (result.get("job_apply_link") or "").strip()
        skills = extract_skills_from_text(f"{title} {description}")

        job_id_suffix = re.sub(r"[^a-zA-Z0-9_-]", "", str(result.get("job_id", "")))[:64]
        if not job_id_suffix:
            import uuid
            job_id_suffix = str(uuid.uuid4())[:12]

        draft = {
            "title": title,
            "company": company,
            "apply_url": apply_url,
            "posted_days_ago": posted_days_ago,
            "description": description,
        }
        vres = verify_opportunity_sync(draft)

        return {
            "id": f"jsearch_{job_id_suffix}",
            "source": "jsearch",
            "title": title,
            "company": company,
            "industry": result.get("employer_company_type") or "Technology",
            "description": description,
            "jd_text": description,
            "skills_required": skills[:6],
            "skills_nice_to_have": skills[6:12],
            "responsibilities": result.get("job_highlights", {}).get("Responsibilities", []) if isinstance(result.get("job_highlights"), dict) else [],
            "qualifications": result.get("job_highlights", {}).get("Qualifications", []) if isinstance(result.get("job_highlights"), dict) else [],
            "experience_min": experience_min,
            "experience_max": experience_max,
            "job_type": job_type,
            "opportunity_type": opportunity_type,
            "candidate_suitability": "STUDENT" if is_internship else ("FRESHER" if fresher_friendly else "EXPERIENCED"),
            "student_eligible": is_internship,
            "fresher_eligible": fresher_friendly,
            "location": location,
            "is_remote": is_remote,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_disclosed": salary_disclosed,
            "salary_currency": sal_curr,
            "stipend": stipend,
            "stipend_min": stipend_min,
            "stipend_max": stipend_max,
            "stipend_currency": "INR" if country == "India" else sal_curr,
            "stipend_period": stipend_period,
            "compensation_type": compensation_type,
            "compensation_text": compensation_text,
            "internship_duration_months": 3 if is_internship else None,
            "fresher_friendly": fresher_friendly,
            "posted_days_ago": posted_days_ago,
            "posted_at": raw_posted if raw_posted else None,
            "registration_closing_date": application_deadline,
            "application_deadline": application_deadline,
            "end_date": application_deadline,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "source_job_id": str(result.get("job_id", "")),
            "source_url": apply_url,
            "apply_url": apply_url,
            "verification_status": vres.status.value,
            "verified_at": vres.verified_at,
            "last_verified_at": vres.verified_at,
            "verification_reason": vres.reason,
            "verification_method": "jsearch_aggregator_adapter",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type.value == "DIRECT_REQUISITION"),
            "country": country,
        }
