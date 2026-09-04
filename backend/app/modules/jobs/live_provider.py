"""
Live job listings via the Adzuna API (https://developer.adzuna.com).

Implements the same JobProvider protocol as CuratedJobProvider, so
everything downstream (matching, ATS scoring, skill gaps, dashboard)
works identically whether a job came from curated seed data or a real
API — none of that code needs to know or care which.

Why Adzuna specifically: it has a genuinely free tier, supports
country-scoped search (country="in" for India, matching this
project's LPA/location-specific design), and — critically — returns a
real redirect_url per listing, which directly fixes the "no direct
link to apply" problem with the curated dataset.

IMPORTANT — this was built and unit-tested against a fixture matching
Adzuna's documented response shape, but could NOT be tested against
the live API from the development sandbox this was built in (no
general internet access there). Verify this actually works against
the real API on your machine before relying on it — see the README
for the exact steps.
"""
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import Settings
from app.modules.jobs.skill_vocabulary import extract_skills_from_text

logger = logging.getLogger("roleradar.jobs.adzuna")

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

FRESHER_KEYWORDS = ["fresher", "entry level", "entry-level", "graduate", "trainee", "junior"]


class AdzunaConfigError(Exception):
    pass


class AdzunaJobProvider:
    def __init__(self, settings: Settings):
        if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
            raise AdzunaConfigError(
                "ADZUNA_APP_ID and ADZUNA_APP_KEY must be set in .env to use the live job source. "
                "Sign up for free at https://developer.adzuna.com/signup."
            )
        self._settings = settings

    async def search(self, filters: dict) -> list[dict]:
        """
        filters supports:
          - skills: list[str] -- OR-matched via Adzuna's `what_or` param,
            the primary way real results get personalized to a candidate
          - skill: str -- single-keyword fallback (kept for callers that
            pass one search term directly)
          - location: str -- maps to `where`
          - job_type: str -- "internship" appends an intern-related term
            so results skew toward internship listings, since Adzuna has
            no first-class internship filter
        """
        params = {
            "app_id": self._settings.ADZUNA_APP_ID,
            "app_key": self._settings.ADZUNA_APP_KEY,
            "results_per_page": self._settings.ADZUNA_RESULTS_PER_QUERY,
            "content-type": "application/json",
        }

        role = filters.get("role") or (filters["target_roles"][0] if filters.get("target_roles") else None) or filters.get("title")
        skills = filters.get("skills") or ([filters["skill"]] if filters.get("skill") else [])

        if filters.get("job_type") == "internship":
            if role:
                params["what"] = f"{role} intern"
            else:
                params["what"] = "internship"
            skills = list(skills) + ["intern", "internship"]
        elif role:
            params["what"] = role

        if skills:
            # Adzuna's what_or: space-separated terms are OR-matched,
            # ensuring results match the candidate's actual skills
            clean_skills = [s.strip() for s in skills if s and s.strip()]
            if clean_skills:
                params["what_or"] = " ".join(clean_skills[:8])

        if filters.get("location"):
            params["where"] = filters["location"]

        url = f"{ADZUNA_BASE_URL}/{self._settings.ADZUNA_COUNTRY}/search/1"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Fail safe, never crash the jobs page because a live
            # external API is slow, down, or rate-limited (Feature 27).
            logger.warning("Adzuna request failed, continuing without live results: %s", exc)
            return []

        return [self._transform(result) for result in data.get("results", [])]

    def _transform(self, result: dict) -> dict:
        title = result.get("title", "").strip()
        description = result.get("description", "").strip()
        company = result.get("company", {}).get("display_name", "Unknown Company")
        location = result.get("location", {}).get("display_name", "")

        skills = extract_skills_from_text(f"{title} {description}")
        title_lower = title.lower()
        job_type = "internship" if "intern" in title_lower else "full_time"
        is_remote = "remote" in description.lower() or "remote" in location.lower()
        fresher_friendly = any(kw in title_lower or kw in description.lower() for kw in FRESHER_KEYWORDS)

        salary_min_raw = result.get("salary_min")
        salary_max_raw = result.get("salary_max")
        salary_disclosed = salary_min_raw is not None
        # Adzuna returns annual salary in the local currency's smallest
        # unit convention for the country; for India this is annual INR,
        # so we convert to LPA (lakhs per annum) to match this project's
        # existing LPA-based filtering.
        salary_min = round(salary_min_raw / 100_000, 1) if salary_min_raw else None
        salary_max = round(salary_max_raw / 100_000, 1) if salary_max_raw else None

        posted_days_ago = 0
        created = result.get("created")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                posted_days_ago = max(0, (datetime.now(timezone.utc) - created_dt).days)
            except ValueError:
                pass

        apply_url = result.get("redirect_url", "")

        from app.modules.jobs.verification import verify_opportunity_sync
        draft = {
            "title": title,
            "company": company,
            "apply_url": apply_url,
            "posted_days_ago": posted_days_ago,
            "description": description,
        }
        vres = verify_opportunity_sync(draft)

        return {
            "id": f"adzuna_{result.get('id', '')}",
            "source": "adzuna",
            "title": title,
            "company": company,
            "industry": result.get("category", {}).get("label", "Unspecified"),
            "description": description,
            "jd_text": description,
            "skills_required": skills[:6],
            "skills_nice_to_have": skills[6:12],
            "responsibilities": [],
            "experience_min": 0,
            "experience_max": 99,
            "job_type": job_type,
            "location": location,
            "is_remote": is_remote,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_disclosed": salary_disclosed,
            "stipend_min": None,
            "internship_duration_months": None,
            "fresher_friendly": fresher_friendly,
            "posted_days_ago": posted_days_ago,
            "posted_at": created if created else None,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "source_job_id": str(result.get("id", "")),
            "source_url": apply_url,
            "apply_url": apply_url,
            "verification_status": vres.status.value,
            "verified_at": vres.verified_at,
            "last_verified_at": vres.verified_at,
            "verification_reason": vres.reason,
            "verification_method": "live_provider_adapter",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type.value == "DIRECT_REQUISITION"),
        }
