"""
Tests for Phase 13D - Experience Match Undisclosed Safety and Candidate Matching.
"""
from __future__ import annotations
import pytest

from app.core.embeddings.tfidf_provider import TfidfEmbeddingProvider
from app.modules.matching.engine import _experience_match, compute_match

embedder = TfidfEmbeddingProvider()

def test_experience_match_undisclosed_returns_neutral():
    # Both None -> undisclosed experience, return 50
    assert _experience_match(0.0, None, None) == 50
    assert _experience_match(2.5, None, None) == 50
    assert _experience_match(5.0, None, None) == 50

def test_experience_match_with_lower_bound_only():
    # job_min = 2, job_max = None
    assert _experience_match(2.0, 2, None) == 100
    assert _experience_match(3.0, 2, None) == 100
    # candidate has 0 years -> gap is 2 years -> 100 - 50 = 50
    assert _experience_match(0.0, 2, None) == 50

def test_experience_match_with_both_bounds():
    # job_min = 1, job_max = 3
    assert _experience_match(2.0, 1, 3) == 100
    assert _experience_match(0.0, 1, 3) == 75

def test_compute_match_with_undisclosed_experience_no_crash():
    candidate = {
        "skills": ["Python", "FastAPI"],
        "target_roles": ["Software Engineer"],
        "experience_years": 0,
        "preferred_locations": ["Bengaluru"],
        "remote_preference": "any",
    }
    # Real direct ATS job with undisclosed experience (both None)
    job = {
        "title": "Software Engineer",
        "skills_required": ["Python", "FastAPI", "Docker"],
        "experience_min": None,
        "experience_max": None,
        "location": "Bengaluru, India",
        "is_remote": False,
        "salary_disclosed": False,
        "salary_max": None,
        "job_type": "full_time",
        "industry": "Technology",
    }
    match = compute_match(candidate, job, embedder, category="FRESHER")
    assert match.experience_score == 50
    assert isinstance(match.overall_score, int)
    assert 0 <= match.overall_score <= 100
