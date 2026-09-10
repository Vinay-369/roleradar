"""
Tests for Canonical Opportunity Completeness Model and Trustworthy Recommendation Invariants.
"""
import pytest
from app.modules.jobs.completeness import (
    OpportunityCompletenessStatus,
    RecommendationQuality,
    evaluate_opportunity_completeness,
)
from app.modules.jobs.providers import CuratedJobProvider


def test_verified_complete_opportunity():
    opp = {
        "title": "Senior Software Engineer",
        "company": "Swiggy",
        "location": "Bengaluru, Karnataka, India",
        "country": "India",
        "is_india_opportunity": True,
        "opportunity_type": "FULL_TIME",
        "description": "Swiggy is seeking a Senior Software Engineer to design scalable microservices and distributed databases. You will own architecture, deployment, and performance.",
        "responsibilities": ["Design microservices", "Deploy on AWS Kubernetes", "Mentor junior engineers"],
        "qualifications": ["B.Tech or M.Tech in Computer Science", "5+ years backend engineering"],
        "skills_required": ["Python", "Golang", "AWS", "PostgreSQL"],
        "skills_nice_to_have": ["Kafka", "Redis"],
        "verification_status": "VERIFIED_ACTIVE",
        "apply_url": "https://boards.greenhouse.io/swiggy/jobs/12345",
        "is_direct_apply": True,
        "salary_min": 25.0,
        "salary_max": 35.0,
        "experience_min": 5,
        "experience_max": 8,
    }
    eval_res = evaluate_opportunity_completeness(opp)
    assert eval_res.source_completeness == OpportunityCompletenessStatus.VERIFIED_COMPLETE
    assert eval_res.recommendation_quality == RecommendationQuality.HIGH
    assert eval_res.eligible_for_primary_recommendations is True
    assert eval_res.is_salary_disclosed is True
    assert eval_res.is_experience_disclosed is True
    assert eval_res.is_skills_disclosed is True
    assert eval_res.is_responsibilities_disclosed is True
    assert eval_res.is_qualifications_disclosed is True


def test_verified_partial_when_salary_undisclosed():
    """
    Fundamental rule: Missing salary is an employer disclosure state, NOT a data-quality failure.
    The opportunity must remain VERIFIED_PARTIAL or VERIFIED_COMPLETE and eligible for primary recommendations.
    """
    opp = {
        "title": "Backend Developer",
        "company": "Paytm",
        "location": "Noida, Uttar Pradesh, India",
        "country": "India",
        "is_india_opportunity": True,
        "opportunity_type": "FULL_TIME",
        "description": "We are looking for a Backend Developer to join our core payments infrastructure team. You will build high-throughput transaction processing systems.",
        "responsibilities": ["Build transaction APIs", "Ensure 99.99% uptime"],
        "qualifications": ["B.E./B.Tech", "3+ years experience"],
        "skills_required": ["Java", "Spring Boot", "MySQL"],
        "skills_nice_to_have": [],
        "verification_status": "VERIFIED_ACTIVE",
        "apply_url": "https://jobs.lever.co/paytm/abc-123",
        "is_direct_apply": True,
        "salary_min": None,
        "salary_max": None,
        "compensation_text": None,
        "experience_min": 3,
        "experience_max": 5,
    }
    eval_res = evaluate_opportunity_completeness(opp)
    # Undisclosed salary must NOT make it INSUFFICIENT
    assert eval_res.eligible_for_primary_recommendations is True
    assert eval_res.source_completeness in (
        OpportunityCompletenessStatus.VERIFIED_COMPLETE,
        OpportunityCompletenessStatus.VERIFIED_PARTIAL,
    )
    assert eval_res.is_salary_disclosed is False
    assert eval_res.is_skills_disclosed is True


def test_insufficient_when_description_missing_or_stub():
    """
    Opportunities with missing description or only repeating the title must be INSUFFICIENT.
    """
    opp = {
        "title": "Enterprise Risk Manager",
        "company": "Paytm",
        "location": "Noida, India",
        "country": "India",
        "is_india_opportunity": True,
        "opportunity_type": "FULL_TIME",
        "description": "Enterprise Risk Manager",  # Only 23 chars, no actual JD content
        "responsibilities": [],
        "qualifications": [],
        "skills_required": [],
        "verification_status": "VERIFIED_ACTIVE",
        "apply_url": "https://jobs.lever.co/paytm/risk-123",
        "is_direct_apply": True,
    }
    eval_res = evaluate_opportunity_completeness(opp)
    assert eval_res.source_completeness == OpportunityCompletenessStatus.INSUFFICIENT
    assert eval_res.recommendation_quality == RecommendationQuality.LOW
    assert eval_res.eligible_for_primary_recommendations is False
    assert "description" in eval_res.missing_required_information


def test_insufficient_when_invalid_apply_url():
    """
    Opportunities with invalid/missing apply URL must be INSUFFICIENT.
    """
    opp = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "location": "Bengaluru, India",
        "country": "India",
        "is_india_opportunity": True,
        "opportunity_type": "FULL_TIME",
        "description": "Valid job description with plenty of details about what the candidate will do in the engineering team.",
        "responsibilities": ["Write code"],
        "qualifications": ["Degree"],
        "skills_required": ["Python"],
        "verification_status": "VERIFIED_ACTIVE",
        "apply_url": "",  # Empty URL
        "is_direct_apply": False,
    }
    eval_res = evaluate_opportunity_completeness(opp)
    assert eval_res.source_completeness == OpportunityCompletenessStatus.INSUFFICIENT
    assert eval_res.eligible_for_primary_recommendations is False
    assert "apply_url" in eval_res.missing_required_information


def test_internship_completeness_stipend_optional():
    """
    Internship with stipend not disclosed remains eligible and verified.
    """
    opp = {
        "title": "Software Engineering Intern",
        "company": "Blueberry Labs",
        "location": "Hyderabad, Telangana, India",
        "country": "India",
        "is_india_opportunity": True,
        "opportunity_type": "INTERNSHIP",
        "description": "Exciting internship opportunity for students and freshers to learn full stack development and work on live web applications.",
        "responsibilities": ["Assist in frontend development", "Participate in code reviews"],
        "qualifications": ["Pursuing B.Tech/B.E."],
        "skills_required": ["JavaScript", "HTML", "CSS"],
        "skills_nice_to_have": ["React"],
        "verification_status": "VERIFIED_ACTIVE",
        "apply_url": "https://jobs.smartrecruiters.com/blueberry/intern-1",
        "is_direct_apply": True,
        "stipend_min": None,
        "stipend_max": None,
        "compensation_text": None,
        "experience_min": 0,
        "experience_max": 1,
    }
    eval_res = evaluate_opportunity_completeness(opp)
    assert eval_res.eligible_for_primary_recommendations is True
    assert eval_res.is_stipend_disclosed is False
    assert eval_res.is_skills_disclosed is True


def test_mongo_query_filters_out_insufficient():
    """
    CuratedJobProvider._build_mongo_query must exclude INSUFFICIENT records by default.
    """
    provider = CuratedJobProvider(None)
    query = provider._build_mongo_query({})
    and_clauses = query.get("$and", [])
    insufficient_clauses = [
        c for c in and_clauses if c.get("completeness_status") == {"$ne": "INSUFFICIENT"}
    ]
    assert len(insufficient_clauses) == 1
