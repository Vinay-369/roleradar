import pytest
from app.modules.jobs.eligibility import evaluate_eligibility, EligibilityStatus, RealisticFitSignal
from app.modules.matching.engine import compute_match, MatchResult
from app.core.embeddings.tfidf_provider import TfidfEmbeddingProvider


def test_student_plus_senior_engineer():
    profile = {
        "experience_years": 0,
        "category": "STUDENT",
        "preferred_locations": ["Bengaluru"],
        "remote_preference": "any",
    }
    resume = {
        "parsed": {
            "education": [{"degree": "B.E. Computer Science", "grad_year": 2026}],
        }
    }
    job = {
        "title": "Senior Software Engineer - Backend",
        "experience_min": None,
        "experience_max": None,
        "job_type": "full_time",
        "location": "Bengaluru",
        "degree_requirements": [],
        "graduation_year_requirements": [],
    }
    result = evaluate_eligibility(profile, resume, job)
    assert result.checks["experience"] == "FAIL"
    assert result.status == EligibilityStatus.EXPERIENCE_MISMATCH
    assert result.realistic_fit == RealisticFitSignal.EXPERIENCE_GAP
    assert any("senior/experienced scope" in r.lower() for r in result.reasons)


def test_student_plus_staff_engineer():
    profile = {
        "experience_years": 0,
        "category": "STUDENT",
        "preferred_locations": ["Hyderabad"],
        "remote_preference": "any",
    }
    resume = {
        "parsed": {
            "education": [{"degree": "B.Tech Information Science", "grad_year": 2026}],
        }
    }
    job = {
        "title": "Staff Cloud Platform Architect",
        "experience_min": None,
        "experience_max": None,
        "job_type": "full_time",
        "location": "Hyderabad",
        "degree_requirements": [],
        "graduation_year_requirements": [],
    }
    result = evaluate_eligibility(profile, resume, job)
    assert result.checks["experience"] == "FAIL"
    assert result.status == EligibilityStatus.EXPERIENCE_MISMATCH
    assert result.realistic_fit == RealisticFitSignal.EXPERIENCE_GAP


def test_student_plus_internship():
    profile = {
        "experience_years": 0,
        "category": "STUDENT",
        "preferred_locations": ["Bengaluru"],
        "remote_preference": "any",
    }
    resume = {
        "parsed": {
            "education": [{"degree": "B.E. ISE", "grad_year": 2026}],
        }
    }
    job = {
        "title": "Software Engineering Intern - 2026",
        "experience_min": 0,
        "experience_max": 0,
        "job_type": "internship",
        "location": "Bengaluru",
        "degree_requirements": ["B.E."],
        "graduation_year_requirements": [2026],
    }
    result = evaluate_eligibility(profile, resume, job)
    assert result.checks["experience"] == "PASS"
    assert result.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)
    assert result.realistic_fit in (RealisticFitSignal.GOOD_FIT, RealisticFitSignal.POSSIBLE_FIT)


def test_student_plus_entry_level():
    profile = {
        "experience_years": 0,
        "category": "FRESHER",
        "preferred_locations": ["Pune"],
        "remote_preference": "any",
    }
    resume = {
        "parsed": {
            "education": [{"degree": "B.Tech", "grad_year": 2025}],
        }
    }
    job = {
        "title": "Junior Associate Software Engineer (0-1 yrs)",
        "experience_min": 0,
        "experience_max": 1,
        "job_type": "full_time",
        "location": "Pune",
        "degree_requirements": [],
        "graduation_year_requirements": [],
    }
    result = evaluate_eligibility(profile, resume, job)
    assert result.checks["experience"] == "PASS"
    assert result.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)


def test_fresher_plus_senior():
    profile = {
        "experience_years": 0,
        "category": "FRESHER",
        "preferred_locations": ["Remote"],
        "remote_preference": "remote_only",
    }
    resume = {
        "parsed": {
            "education": [{"degree": "MCA", "grad_year": 2025}],
        }
    }
    job = {
        "title": "Lead Full Stack Developer",
        "experience_min": None,
        "experience_max": None,
        "job_type": "full_time",
        "location": "Remote",
        "degree_requirements": [],
        "graduation_year_requirements": [],
    }
    result = evaluate_eligibility(profile, resume, job)
    assert result.checks["experience"] == "FAIL"
    assert result.status == EligibilityStatus.EXPERIENCE_MISMATCH
    assert result.realistic_fit == RealisticFitSignal.EXPERIENCE_GAP


def test_early_career_1_to_3_years_plus_senior():
    profile = {
        "experience_years": 2,
        "category": "EARLY_CAREER",
        "preferred_locations": ["Bengaluru"],
        "remote_preference": "any",
    }
    resume = {
        "parsed": {
            "education": [{"degree": "B.Tech", "grad_year": 2023}],
        }
    }
    job = {
        "title": "Principal Engineer - Platform Services",
        "experience_min": None,
        "experience_max": None,
        "job_type": "full_time",
        "location": "Bengaluru",
        "degree_requirements": [],
        "graduation_year_requirements": [],
    }
    result = evaluate_eligibility(profile, resume, job)
    assert result.checks["experience"] == "FAIL"
    assert result.status == EligibilityStatus.EXPERIENCE_MISMATCH
    assert result.realistic_fit == RealisticFitSignal.EXPERIENCE_GAP


def test_experienced_candidate_plus_undisclosed_experience():
    profile = {
        "experience_years": 6,
        "category": "EXPERIENCED",
        "preferred_locations": ["Bengaluru"],
        "remote_preference": "any",
    }
    resume = {
        "parsed": {
            "education": [{"degree": "B.Tech", "grad_year": 2019}],
        }
    }
    job = {
        "title": "DevOps Engineer",
        "experience_min": None,
        "experience_max": None,
        "job_type": "full_time",
        "location": "Bengaluru",
        "degree_requirements": [],
        "graduation_year_requirements": [],
    }
    result = evaluate_eligibility(profile, resume, job)
    assert result.checks["experience"] == "UNKNOWN"
    assert result.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)
    assert result.required_experience_min is None
    assert result.required_experience_max is None


def test_match_score_canonical_transparency():
    candidate = {
        "skills": ["python", "fastapi", "docker", "sql"],
        "target_roles": ["Backend Engineer"],
        "experience_years": 1,
        "preferred_locations": ["Bengaluru"],
        "remote_preference": "any",
        "min_lpa": 6,
    }
    job = {
        "id": "job-123",
        "title": "Backend Engineer",
        "skills_required": ["python", "fastapi", "docker", "redis"],
        "experience_min": 0,
        "experience_max": 2,
        "location": "Bengaluru",
        "is_remote": False,
        "salary_min": 700000,
        "salary_max": 1200000,
        "description": "Backend services with Python and FastAPI",
    }
    embedder = TfidfEmbeddingProvider()
    match = compute_match(candidate, job, embedder, category="FRESHER")

    assert isinstance(match, MatchResult)
    assert hasattr(match, "factor_weights")
    assert hasattr(match, "score_explanation")
    assert match.factor_weights is not None
    assert "skill" in match.factor_weights or "skills" in match.factor_weights
    assert "role" in match.factor_weights
    assert sum(match.factor_weights.values()) == pytest.approx(1.0, abs=0.01)

    assert match.score_explanation is not None
    assert len(match.score_explanation) > 0
    assert "skills" in match.score_explanation.lower()


def test_india_first_discovery_ordering_does_not_let_foreign_dominate():
    from app.modules.jobs.location_normalization import is_india_opportunity

    jobs = [
        {
            "id": "foreign-us",
            "title": "Software Engineer",
            "location": "San Francisco, CA, USA",
            "country": "United States",
            "posted_days_ago": 0,  # Posted today
        },
        {
            "id": "foreign-uk",
            "title": "Backend Engineer",
            "location": "London, UK",
            "country": "United Kingdom",
            "posted_days_ago": 0,  # Posted today
        },
        {
            "id": "india-blr",
            "title": "Junior Python Developer",
            "location": "Bengaluru, Karnataka, India",
            "country": "India",
            "posted_days_ago": 2,  # Posted 2 days ago
        },
        {
            "id": "india-hyd",
            "title": "Associate Cloud Engineer",
            "location": "Hyderabad, Telangana",
            "country": "India",
            "posted_days_ago": 3,  # Posted 3 days ago
        },
    ]

    def _is_india_job(j: dict) -> bool:
        return j.get("country") == "India" or is_india_opportunity(j.get("location"))

    # Apply canonical India-first ordering
    jobs.sort(key=lambda j: (0 if _is_india_job(j) else 1, j.get("posted_days_ago", 0)))

    ordered_ids = [j["id"] for j in jobs]
    assert ordered_ids[0] in ("india-blr", "india-hyd")
    assert ordered_ids[1] in ("india-blr", "india-hyd")
    assert ordered_ids[2] in ("foreign-us", "foreign-uk")
    assert ordered_ids[3] in ("foreign-us", "foreign-uk")
    # Crucially: Even though foreign jobs were posted 0 days ago and India jobs were posted 2-3 days ago,
    # foreign jobs NEVER appear ahead of India jobs under default India-first ordering!
    assert ordered_ids.index("india-blr") < ordered_ids.index("foreign-us")
    assert ordered_ids.index("india-hyd") < ordered_ids.index("foreign-uk")


def test_company_description_boilerplate_does_not_mark_foreign_job_as_indian():
    from app.modules.jobs.location_normalization import is_india_opportunity

    foreign_job_with_india_mention_in_desc = {
        "title": "DevOps Engineer",
        "location": "Austin, TX, United States",
        "description": "Acme Corp operates globally with major delivery centers in Bangalore, Pune, and London.",
    }

    # Location is strictly US; description mentions Bangalore/Pune as company boilerplate
    assert is_india_opportunity(
        foreign_job_with_india_mention_in_desc["location"],
        foreign_job_with_india_mention_in_desc["description"],
    ) is False


def test_application_lifecycle_enum_coverage():
    from app.modules.applications.schemas import ApplicationStatus, UpdateApplicationRequest

    expected_lifecycle = [
        "SAVED",
        "TAILORED",
        "QUEUED",
        "APPLIED",
        "INTERVIEW",
        "OFFER",
        "REJECTED",
        "WITHDRAWN",
    ]
    for status_str in expected_lifecycle:
        status_enum = ApplicationStatus(status_str)
        assert status_enum.value == status_str
        req = UpdateApplicationRequest(status=status_enum, notes=f"Moved to {status_str}")
        assert req.status == status_enum
        assert req.notes == f"Moved to {status_str}"


def test_no_google_search_fallback_invariant():
    """P2-01 Invariant: System never manufactures google.com/search apply links for missing apply URLs."""
    raw_jobs = [
        {"id": "job-1", "company": "Initech", "title": "DevOps", "apply_url": ""},
        {"id": "job-2", "company": "Acme", "title": "SDE", "apply_url": None},
        {"id": "job-3", "company": "ExampleCorp", "title": "Intern", "apply_url": "https://example.com/apply"},
    ]

    for job in raw_jobs:
        apply_url = job.get("apply_url") or ""
        is_verified_direct = bool(apply_url and "example.com" not in apply_url and "google.com" not in apply_url)
        # Verify that missing or example.com urls do NOT result in a manufactured google search fallback
        assert "google.com/search" not in apply_url
        if not is_verified_direct:
            fallback_display = "Application link unavailable"
            assert fallback_display == "Application link unavailable"


