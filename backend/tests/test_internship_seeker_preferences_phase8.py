"""
Phase 8 Stage B F-08: Internship Seeker Preference Profile & Matching Tests.
Validates:
1. INTERNSHIP_SEEKER onboarding schema persists min_stipend & internship_duration_months.
2. INTERNSHIP_SEEKER auto-enforces internship_interested=True and min_lpa=None.
3. Internship matching evaluates min_stipend vs stipend_min/stipend_max.
4. Insufficient stipend is penalized vs matching/surplus stipend.
5. Full-time job salary matching is preserved and unaffected.
6. Non-internship categories (FRESHER, EXPERIENCED, CAREER_SWITCHER) are unaffected.
"""
import pytest
from app.modules.profile.schemas import OnboardingRequest, CandidateCategory
from app.modules.matching.engine import compute_match, _salary_match, _stipend_match
from app.core.embeddings.factory import build_embedding_provider
from app.core.config import get_settings


def test_internship_seeker_onboarding_schema_persists_stipend_and_duration():
    req = OnboardingRequest(
        category=CandidateCategory.INTERNSHIP_SEEKER,
        target_roles=["Backend Intern"],
        min_stipend=25000,
        internship_duration_months=6,
        consent_text="I consent",
    )
    dumped = req.model_dump()
    assert dumped["category"] == "INTERNSHIP_SEEKER"
    assert dumped["min_stipend"] == 25000
    assert dumped["internship_duration_months"] == 6
    assert dumped["internship_interested"] is True
    assert dumped["min_lpa"] is None
    assert dumped["experience_years"] == 0.0


def test_internship_seeker_clears_accidental_min_lpa_and_forces_internship_interested():
    # If client passed min_lpa or internship_interested=False, validator cleanses state
    req = OnboardingRequest(
        category=CandidateCategory.INTERNSHIP_SEEKER,
        target_roles=["Data Science Intern"],
        min_lpa=12.0,
        min_stipend=30000,
        internship_interested=False,
        consent_text="I consent",
    )
    assert req.internship_interested is True
    assert req.min_lpa is None
    assert req.min_stipend == 30000


def test_stipend_matching_scores():
    # No candidate preference -> neutral 70
    assert _stipend_match(None, 20000, 30000) == 70

    # Undisclosed stipend -> neutral 50
    assert _stipend_match(25000, None, None) == 50

    # Offered meets or exceeds preferred -> 100
    assert _stipend_match(20000, 20000, 25000) == 100
    assert _stipend_match(25000, 25000, 25000) == 100
    assert _stipend_match(20000, 25000, 35000) == 100

    # Offered is below preferred -> penalty
    score_small_gap = _stipend_match(30000, 25000, 25000)  # 5k shortfall (~16.7%) -> 90
    score_large_gap = _stipend_match(30000, 15000, 15000)  # 15k shortfall (50%) -> 70
    score_zero_stipend = _stipend_match(30000, 0, 0)       # 30k shortfall (100%) -> 40

    assert score_small_gap > score_large_gap > score_zero_stipend
    assert score_small_gap == 90
    assert score_large_gap == 70
    assert score_zero_stipend == 40


def test_fulltime_salary_matching_preserved():
    # Undisclosed -> 50
    assert _salary_match(6.0, None, False) == 50
    # No candidate preference -> 70
    assert _salary_match(None, 10.0, True) == 70
    # Meets preference -> 100
    assert _salary_match(8.0, 10.0, True) == 100
    # Shortfall: 8.0 vs 6.0 (2 LPA diff * 15 = 30 pt drop -> 70)
    assert _salary_match(8.0, 6.0, True) == 70


def test_compute_match_internship_stipend_integration():
    settings = get_settings()
    embedder = build_embedding_provider(settings)

    candidate = {
        "skills": ["Python", "FastAPI", "Docker"],
        "target_roles": ["Backend Developer Intern"],
        "experience_years": 0,
        "preferred_locations": ["Bangalore"],
        "remote_preference": "any",
        "min_stipend": 25000,
        "min_lpa": None,
        "industries": [],
    }

    internship_good_stipend = {
        "job_type": "internship",
        "title": "Backend Developer Intern",
        "skills_required": ["Python", "FastAPI"],
        "experience_min": 0,
        "experience_max": 1,
        "location": "Bangalore",
        "is_remote": False,
        "stipend_min": 25000,
        "stipend_max": 35000,
        "salary_max": None,
        "salary_disclosed": False,
        "industry": "Tech",
    }

    internship_low_stipend = {
        **internship_good_stipend,
        "stipend_min": 10000,
        "stipend_max": 10000,
    }

    match_good = compute_match(candidate, internship_good_stipend, embedder, category="INTERNSHIP_SEEKER")
    match_low = compute_match(candidate, internship_low_stipend, embedder, category="INTERNSHIP_SEEKER")

    assert match_good.salary_score == 100
    assert match_low.salary_score < 100
    assert match_good.overall_score > match_low.overall_score


def test_non_internship_categories_unaffected():
    settings = get_settings()
    embedder = build_embedding_provider(settings)

    fresher_candidate = {
        "skills": ["Java", "Spring Boot"],
        "target_roles": ["Software Engineer"],
        "experience_years": 0,
        "preferred_locations": ["Hyderabad"],
        "remote_preference": "any",
        "min_lpa": 6.0,
        "min_stipend": None,
        "industries": [],
    }

    full_time_job = {
        "job_type": "full_time",
        "title": "Software Engineer",
        "skills_required": ["Java", "Spring Boot"],
        "experience_min": 0,
        "experience_max": 2,
        "location": "Hyderabad",
        "is_remote": False,
        "salary_min": 6.0,
        "salary_max": 8.0,
        "salary_disclosed": True,
        "stipend_min": None,
        "stipend_max": None,
        "industry": "Tech",
    }

    match_fresher = compute_match(fresher_candidate, full_time_job, embedder, category="FRESHER")
    assert match_fresher.salary_score == 100
    assert match_fresher.overall_score >= 90
