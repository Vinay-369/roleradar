"""
Zero-auth & public job and internship aggregators:
1. Remotive (https://remotive.com/api/remote-jobs) - Free tech jobs & internships with salary & remote tags.
2. Arbeitnow (https://www.arbeitnow.com/api/job-board-api) - Free job board API with salary, internships, and visa sponsorship.
3. Jooble (https://jooble.org/api/about) - Global & India-specific job search aggregator.
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
from app.modules.jobs.verification import verify_opportunity_sync

logger = logging.getLogger("roleradar.jobs.public_aggregators")

FRESHER_KEYWORDS = ["fresher", "entry level", "entry-level", "graduate", "trainee", "junior", "0-1 year", "intern"]


def extract_deadline_from_text(text: str | None) -> str | None:
    """Extracts application closing date or deadline from job description text."""
    if not text:
        return None
    match = re.search(
        r"\b(?:apply\s+(?:by|before|until)|deadline|closing\s+date|last\s+date\s+to\s+apply)\s*[:\-]?\s*([A-Za-z0-9,\s\/\-]+(?:\d{4}|\d{2}))\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None


class RemotiveJobProvider:
    """Zero-auth public provider for real-time remote tech jobs and internships with salary disclosures."""

    name: str = "remotive"

    def __init__(self, settings: Settings | None = None):
        self._settings = settings

    def normalize_job(self, result: dict) -> dict:
        return self._transform(result)

    async def search(self, filters: dict) -> list[dict]:
        if self._settings and not getattr(self._settings, "REMOTIVE_ENABLED", True):
            return []

        role = filters.get("role") or (filters["target_roles"][0] if filters.get("target_roles") else None) or filters.get("title") or filters.get("skill") or ""
        params: dict[str, Any] = {}
        if role:
            params["search"] = role

        url = "https://remotive.com/api/remote-jobs"
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Remotive API request failed: %s", exc)
            return []

        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        is_internship = filters.get("job_type") == "internship" or filters.get("opportunity_type") == "INTERNSHIP"
        results = []
        for job in jobs[:40]:
            item = self._transform(job)
            if is_internship and item["job_type"] != "internship":
                continue
            results.append(item)
        return results

    def _transform(self, result: dict) -> dict:
        title = (result.get("title") or "").strip()
        company = (result.get("company_name") or "Unknown Company").strip()
        description = (result.get("description") or "").strip()
        category = result.get("category") or "Software Development"
        location = result.get("candidate_required_location") or "Remote / Global"
        apply_url = result.get("url") or ""
        salary_raw = (result.get("salary") or "").strip()
        job_type_raw = (result.get("job_type") or "").lower()

        title_lower = title.lower()
        is_internship = "intern" in job_type_raw or "intern" in title_lower or "internship" in title_lower
        job_type = "internship" if is_internship else "full_time"
        opportunity_type = "INTERNSHIP" if is_internship else "FULL_TIME"
        fresher_friendly = is_internship or any(kw in title_lower or kw in description.lower() for kw in FRESHER_KEYWORDS)
        experience_min, experience_max = extract_experience_bounds(description, title)

        # Only show a closing date when the provider or posting explicitly supplies one.
        pub_date = result.get("publication_date")
        application_deadline = extract_deadline_from_text(description)

        # Compensation parsing
        salary_min = None
        salary_max = None
        stipend = None
        stipend_min = None
        stipend_max = None
        stipend_period = None
        salary_disclosed = False
        compensation_type = None
        compensation_text = salary_raw if salary_raw else None

        if salary_raw:
            salary_disclosed = True
            extracted = extract_compensation_details(f"{title} {salary_raw}")
            if is_internship and extracted.get("stipend"):
                stipend = extracted.get("stipend")
                stipend_min = extracted.get("stipend_min") or stipend
                stipend_max = extracted.get("stipend_max") or stipend
                stipend_period = "MONTH"
                compensation_type = "STIPEND"
            elif extracted.get("salary_min"):
                salary_min = extracted.get("salary_min")
                salary_max = extracted.get("salary_max")
                compensation_type = "SALARY"
            else:
                compensation_type = "SALARY"

        if not salary_disclosed:
            extracted = extract_compensation_details(f"{title} {description}")
            if extracted and extracted.get("compensation_text"):
                salary_disclosed = True
                salary_min = extracted.get("salary_min")
                salary_max = extracted.get("salary_max")
                stipend = extracted.get("stipend")
                stipend_min = extracted.get("stipend_min")
                stipend_max = extracted.get("stipend_max")
                stipend_period = extracted.get("stipend_period")
                compensation_type = extracted.get("compensation_type")
                compensation_text = extracted.get("compensation_text")

        # Posted days ago
        posted_days_ago = 0
        pub_date = result.get("publication_date")
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                posted_days_ago = max(0, (datetime.now(timezone.utc) - dt).days)
            except (ValueError, TypeError):
                pass

        skills = extract_skills_from_text(f"{title} {description}")
        tags = result.get("tags") or []
        for t in tags:
            if isinstance(t, str) and t.strip() and t.strip() not in skills:
                skills.append(t.strip())

        draft = {
            "title": title,
            "company": company,
            "apply_url": apply_url,
            "posted_days_ago": posted_days_ago,
            "description": description,
        }
        vres = verify_opportunity_sync(draft)

        return {
            "id": f"remotive_{result.get('id', '')}",
            "source": "remotive",
            "title": title,
            "company": company,
            "industry": category,
            "description": description,
            "jd_text": description,
            "skills_required": skills[:6],
            "skills_nice_to_have": skills[6:12],
            "responsibilities": [],
            "qualifications": [],
            "experience_min": experience_min,
            "experience_max": experience_max,
            "job_type": job_type,
            "opportunity_type": opportunity_type,
            "candidate_suitability": "STUDENT" if is_internship else ("FRESHER" if fresher_friendly else "EXPERIENCED"),
            "student_eligible": is_internship,
            "fresher_eligible": fresher_friendly,
            "location": location,
            "is_remote": True,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_disclosed": salary_disclosed,
            "salary_currency": "USD",
            "stipend": stipend,
            "stipend_min": stipend_min,
            "stipend_max": stipend_max,
            "stipend_currency": "USD",
            "stipend_period": stipend_period,
            "compensation_type": compensation_type,
            "compensation_text": compensation_text,
            "internship_duration_months": 3 if is_internship else None,
            "fresher_friendly": fresher_friendly,
            "posted_days_ago": posted_days_ago,
            "posted_at": pub_date if pub_date else None,
            "registration_closing_date": application_deadline,
            "application_deadline": application_deadline,
            "end_date": application_deadline,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "source_job_id": str(result.get("id", "")),
            "source_url": apply_url,
            "apply_url": apply_url,
            "verification_status": vres.status.value,
            "verified_at": vres.verified_at,
            "last_verified_at": vres.verified_at,
            "verification_reason": vres.reason,
            "verification_method": "remotive_aggregator_adapter",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type.value == "DIRECT_REQUISITION"),
            "country": "Remote",
        }


class ArbeitnowJobProvider:
    """Zero-auth public provider for international and remote opportunities with salary disclosures."""

    name: str = "arbeitnow"

    def __init__(self, settings: Settings | None = None):
        self._settings = settings

    def normalize_job(self, result: dict) -> dict:
        return self._transform(result)

    async def search(self, filters: dict) -> list[dict]:
        if self._settings and not getattr(self._settings, "ARBEITNOW_ENABLED", True):
            return []

        url = "https://www.arbeitnow.com/api/job-board-api"
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Arbeitnow API request failed: %s", exc)
            return []

        jobs = data.get("data", [])
        if not isinstance(jobs, list):
            return []

        role = (filters.get("role") or "").lower()
        is_internship = filters.get("job_type") == "internship" or filters.get("opportunity_type") == "INTERNSHIP"

        results = []
        for job in jobs[:30]:
            title_lower = (job.get("title") or "").lower()
            if role and role not in title_lower and role not in (job.get("description") or "").lower():
                continue
            item = self._transform(job)
            if is_internship and item["job_type"] != "internship":
                continue
            results.append(item)
        return results

    def _transform(self, result: dict) -> dict:
        title = (result.get("title") or "").strip()
        company = (result.get("company_name") or "Unknown Company").strip()
        description = (result.get("description") or "").strip()
        location = result.get("location") or "Remote"
        is_remote = bool(result.get("remote")) or "remote" in location.lower()
        apply_url = result.get("url") or ""
        job_types = [str(t).lower() for t in result.get("job_types", [])]

        title_lower = title.lower()
        is_internship = any("intern" in t for t in job_types) or "intern" in title_lower
        job_type = "internship" if is_internship else "full_time"
        opportunity_type = "INTERNSHIP" if is_internship else "FULL_TIME"
        fresher_friendly = is_internship or any(kw in title_lower or kw in description.lower() for kw in FRESHER_KEYWORDS)
        experience_min, experience_max = extract_experience_bounds(description, title)

        # Only use a closing date explicitly present in the provider data.
        created_at = result.get("created_at")
        application_deadline = extract_deadline_from_text(description)

        # Compensation
        extracted = extract_compensation_details(f"{title} {description}")
        salary_min = extracted.get("salary_min")
        salary_max = extracted.get("salary_max")
        stipend = extracted.get("stipend")
        stipend_min = extracted.get("stipend_min")
        stipend_max = extracted.get("stipend_max")
        stipend_period = extracted.get("stipend_period")
        salary_disclosed = bool(salary_min or stipend)
        compensation_type = extracted.get("compensation_type")
        compensation_text = extracted.get("compensation_text")

        posted_days_ago = 0
        created_at_ts = result.get("created_at")
        posted_at_iso = None
        if created_at_ts:
            try:
                dt = datetime.fromtimestamp(created_at_ts, tz=timezone.utc)
                posted_days_ago = max(0, (datetime.now(timezone.utc) - dt).days)
                posted_at_iso = dt.isoformat()
            except (ValueError, TypeError, OSError):
                pass

        skills = extract_skills_from_text(f"{title} {description}")
        tags = result.get("tags") or []
        for t in tags:
            if isinstance(t, str) and t.strip() and t.strip() not in skills:
                skills.append(t.strip())

        slug = result.get("slug") or str(hash(title + company))[:12]
        draft = {
            "title": title,
            "company": company,
            "apply_url": apply_url,
            "posted_days_ago": posted_days_ago,
            "description": description,
        }
        vres = verify_opportunity_sync(draft)

        return {
            "id": f"arbeitnow_{slug}",
            "source": "arbeitnow",
            "title": title,
            "company": company,
            "industry": "Technology",
            "description": description,
            "jd_text": description,
            "skills_required": skills[:6],
            "skills_nice_to_have": skills[6:12],
            "responsibilities": [],
            "qualifications": [],
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
            "salary_currency": "EUR" if "europe" in location.lower() or "germany" in location.lower() else "USD",
            "stipend": stipend,
            "stipend_min": stipend_min,
            "stipend_max": stipend_max,
            "stipend_currency": "EUR",
            "stipend_period": stipend_period,
            "compensation_type": compensation_type,
            "compensation_text": compensation_text,
            "internship_duration_months": 3 if is_internship else None,
            "fresher_friendly": fresher_friendly,
            "posted_days_ago": posted_days_ago,
            "posted_at": posted_at_iso,
            "registration_closing_date": application_deadline,
            "application_deadline": application_deadline,
            "end_date": application_deadline,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "source_job_id": slug,
            "source_url": apply_url,
            "apply_url": apply_url,
            "verification_status": vres.status.value,
            "verified_at": vres.verified_at,
            "last_verified_at": vres.verified_at,
            "verification_reason": vres.reason,
            "verification_method": "arbeitnow_aggregator_adapter",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type.value == "DIRECT_REQUISITION"),
            "country": "Germany" if "germany" in location.lower() else ("Remote" if is_remote else "Global"),
        }


class JoobleJobProvider:
    """High-volume aggregator for India (in.jooble.org) and global opportunities."""

    name: str = "jooble"

    def __init__(self, settings: Settings | None = None, api_key: str | None = None):
        self._settings = settings
        self._api_key = api_key or (getattr(settings, "JOOBLE_API_KEY", None) if settings else None)

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def normalize_job(self, result: dict) -> dict:
        return self._transform(result)

    async def search(self, filters: dict) -> list[dict]:
        if not self.is_configured:
            return []

        role = filters.get("role") or (filters["target_roles"][0] if filters.get("target_roles") else None) or filters.get("title") or filters.get("skill") or "Software Engineer"
        location = filters.get("location") or filters.get("location_preset") or "India"
        is_internship = filters.get("job_type") == "internship" or filters.get("opportunity_type") == "INTERNSHIP"

        keywords = f"{role} intern" if is_internship else role
        url = f"https://jooble.org/api/{self._api_key.strip()}"
        payload = {
            "keywords": keywords,
            "location": location,
            "page": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code in (401, 403):
                    logger.warning("Jooble API key invalid or expired.")
                    return []
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Jooble API request failed: %s", exc)
            return []

        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        return [self._transform(j) for j in jobs[:30] if isinstance(j, dict)]

    def _transform(self, result: dict) -> dict:
        title = (result.get("title") or "").strip()
        company = (result.get("company") or "Unknown Company").strip()
        description = (result.get("snippet") or "").strip()
        location = (result.get("location") or "India").strip()
        apply_url = result.get("link") or ""
        salary_str = (result.get("salary") or "").strip()
        job_type_str = (result.get("type") or "").lower()

        title_lower = title.lower()
        is_internship = "intern" in job_type_str or "intern" in title_lower or "internship" in title_lower
        job_type = "internship" if is_internship else "full_time"
        opportunity_type = "INTERNSHIP" if is_internship else "FULL_TIME"
        fresher_friendly = is_internship or any(kw in title_lower or kw in description.lower() for kw in FRESHER_KEYWORDS)
        experience_min, experience_max = extract_experience_bounds(description, title)

        # Application Deadline
        application_deadline = None
        deadline_match = re.search(
            r"\b(?:apply\s+(?:by|before|until)|deadline|closing\s+date|last\s+date\s+to\s+apply)\s*[:\-]?\s*([A-Za-z0-9,\s\/\-]+(?:\d{4}|\d{2}))\b",
            description,
            re.IGNORECASE,
        )
        if deadline_match:
            application_deadline = deadline_match.group(1).strip()

        # Compensation
        extracted = extract_compensation_details(f"{title} {salary_str} {description}")
        salary_min = extracted.get("salary_min")
        salary_max = extracted.get("salary_max")
        stipend = extracted.get("stipend")
        stipend_min = extracted.get("stipend_min")
        stipend_max = extracted.get("stipend_max")
        stipend_period = extracted.get("stipend_period")
        salary_disclosed = bool(salary_min or stipend or salary_str)
        compensation_type = extracted.get("compensation_type")
        compensation_text = salary_str if salary_str else extracted.get("compensation_text")

        posted_days_ago = 0
        pub_date = result.get("updated")
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                posted_days_ago = max(0, (datetime.now(timezone.utc) - dt).days)
            except (ValueError, TypeError):
                pass

        skills = extract_skills_from_text(f"{title} {description}")
        job_id = str(result.get("id") or hash(title + company))

        draft = {
            "title": title,
            "company": company,
            "apply_url": apply_url,
            "posted_days_ago": posted_days_ago,
            "description": description,
        }
        vres = verify_opportunity_sync(draft)

        return {
            "id": f"jooble_{job_id}",
            "source": "jooble",
            "title": title,
            "company": company,
            "industry": "Technology",
            "description": description,
            "jd_text": description,
            "skills_required": skills[:6],
            "skills_nice_to_have": skills[6:12],
            "responsibilities": [],
            "qualifications": [],
            "experience_min": experience_min,
            "experience_max": experience_max,
            "job_type": job_type,
            "opportunity_type": opportunity_type,
            "candidate_suitability": "STUDENT" if is_internship else ("FRESHER" if fresher_friendly else "EXPERIENCED"),
            "student_eligible": is_internship,
            "fresher_eligible": fresher_friendly,
            "location": location,
            "is_remote": "remote" in location.lower() or "remote" in description.lower(),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_disclosed": salary_disclosed,
            "salary_currency": "INR",
            "stipend": stipend,
            "stipend_min": stipend_min,
            "stipend_max": stipend_max,
            "stipend_currency": "INR",
            "stipend_period": stipend_period,
            "compensation_type": compensation_type,
            "compensation_text": compensation_text,
            "internship_duration_months": 3 if is_internship else None,
            "fresher_friendly": fresher_friendly,
            "posted_days_ago": posted_days_ago,
            "posted_at": pub_date if pub_date else None,
            "registration_closing_date": application_deadline,
            "application_deadline": application_deadline,
            "end_date": application_deadline,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "source_job_id": job_id,
            "source_url": apply_url,
            "apply_url": apply_url,
            "verification_status": vres.status.value,
            "verified_at": vres.verified_at,
            "last_verified_at": vres.verified_at,
            "verification_reason": vres.reason,
            "verification_method": "jooble_aggregator_adapter",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type.value == "DIRECT_REQUISITION"),
            "country": "India",
        }
