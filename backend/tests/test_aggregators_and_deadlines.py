import pytest
from app.modules.jobs.jsearch_provider import JSearchJobProvider
from app.modules.jobs.public_aggregators import (
    RemotiveJobProvider,
    ArbeitnowJobProvider,
    JoobleJobProvider,
    extract_deadline_from_text,
)
from app.modules.jobs.schemas import JobOut
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.taxonomy import extract_experience_bounds, normalize_provider_experience
from app.modules.jobs.url_classifier import ApplicationUrlType


def test_extract_deadline_from_text():
    sample_text = (
        "We are hiring a Software Engineering Intern. "
        "Application deadline: 15-Nov-2026. Please apply before 15 November 2026."
    )
    deadline = extract_deadline_from_text(sample_text)
    assert deadline is not None
    assert "15-Nov-2026" in deadline or "15 November 2026" in deadline


def test_jsearch_normalization_salary_and_deadline():
    provider = JSearchJobProvider()
    raw = {
        "job_id": "js_test_123",
        "job_title": "Full Stack Developer",
        "employer_name": "Acme Corp",
        "job_description": "Building next gen cloud apps with Python and React.",
        "job_city": "Bengaluru",
        "job_country": "IN",
        "job_is_remote": False,
        "job_min_salary": 1800000,
        "job_max_salary": 2500000,
        "job_salary_currency": "INR",
        "job_salary_period": "YEAR",
        "job_offer_expiration_datetime_utc": "2026-12-31T23:59:59.000Z",
        "job_apply_link": "https://example.com/apply/123",
        "job_posted_at_timestamp": 1727350000,
        "job_employment_type": "FULLTIME",
    }
    normalized = provider.normalize_job(raw)
    assert normalized is not None
    assert normalized["job_type"] == "full_time"
    assert normalized["salary_min"] == 18.0
    assert normalized["salary_max"] == 25.0
    assert normalized["experience_max"] is None
    # Provider normalizes ISO format: .000Z → +00:00
    assert normalized["application_deadline"] is not None
    assert "2026-12-31" in normalized["application_deadline"]
    assert normalized["registration_closing_date"] == normalized["application_deadline"]
    assert normalized["end_date"] is not None
    assert "2026-12-31" in normalized["end_date"]


def test_jsearch_normalization_internship_and_stipend():
    provider = JSearchJobProvider()
    raw = {
        "job_id": "js_test_456",
        "job_title": "Frontend Engineer Intern",
        "employer_name": "Startup Inc",
        "job_description": "Exciting summer internship. Last date to apply: 30 Oct 2026.",
        "job_city": "Hyderabad",
        "job_country": "IN",
        "job_is_remote": True,
        "job_min_salary": 35000,
        "job_max_salary": 45000,
        "job_salary_currency": "INR",
        "job_salary_period": "MONTH",
        "job_apply_link": "https://example.com/apply/456",
        "job_posted_at_timestamp": 1727350000,
        "job_employment_type": "INTERN",
    }
    normalized = provider.normalize_job(raw)
    assert normalized is not None
    assert normalized["job_type"] == "internship"
    assert normalized["opportunity_type"] == "INTERNSHIP"
    assert normalized["stipend"] == 35000
    assert normalized["stipend_min"] == 35000
    assert normalized["stipend_max"] == 45000
    assert normalized["experience_max"] is None
    assert normalized["student_eligible"] is True
    assert normalized["fresher_friendly"] is True
    assert normalized["is_remote"] is True
    # Deadline extracted from text
    assert normalized["application_deadline"] is not None
    assert "30 Oct 2026" in normalized["application_deadline"]
    assert normalized["registration_closing_date"] == normalized["application_deadline"]


def test_remotive_normalization():
    provider = RemotiveJobProvider()
    raw = {
        "id": 9991,
        "title": "Backend Python Developer",
        "company_name": "Global Remote Co",
        "description": "<p>We are hiring! Salary range: $60,000 - $80,000. Apply by: 25/11/2026</p>",
        "candidate_required_location": "Worldwide",
        "salary": "$60,000 - $80,000",
        "job_type": "full_time",
        "url": "https://remotive.com/job/9991",
        "publication_date": "2026-09-25T10:00:00",
        "tags": ["python", "django", "postgresql"],
    }
    normalized = provider.normalize_job(raw)
    assert normalized is not None
    assert normalized["company"] == "Global Remote Co"
    assert normalized["is_remote"] is True
    assert normalized["compensation_text"] == "$60,000 - $80,000"
    assert normalized["application_deadline"] is not None


def test_remotive_does_not_invent_registration_closing_date():
    normalized = RemotiveJobProvider().normalize_job({
        "id": 9992,
        "title": "Backend Engineer",
        "company_name": "Remote Co",
        "description": "Build APIs with Python.",
        "publication_date": "2026-09-25T10:00:00",
        "url": "https://remotive.com/job/9992",
    })
    assert normalized["registration_closing_date"] is None
    assert normalized["application_deadline"] is None


def test_arbeitnow_normalization():
    provider = ArbeitnowJobProvider()
    raw = {
        "slug": "arbeitnow-qa-intern-123",
        "title": "Software QA Intern",
        "company_name": "TechLabs",
        "description": "Looking for enthusiastic QA Intern. Hands-on testing. Deadline: 2026-11-30",
        "location": "Berlin / Remote",
        "remote": True,
        "tags": ["testing", "python", "internship"],
        "url": "https://arbeitnow.com/view/arbeitnow-qa-intern-123",
        "created_at": 1727350000,
    }
    normalized = provider.normalize_job(raw)
    assert normalized is not None
    assert normalized["job_type"] == "internship"
    assert normalized["fresher_friendly"] is True
    assert normalized["is_remote"] is True
    assert normalized["application_deadline"] is not None
    assert "2026-11-30" in normalized["application_deadline"]


def test_jooble_normalization():
    provider = JoobleJobProvider(api_key="mock_key")
    raw = {
        "id": "jooble_987",
        "title": "Data Analyst Intern",
        "company": "Analytics Hub",
        "location": "Bengaluru, Karnataka",
        "snippet": "Exciting internship for freshers. ₹25,000 per month stipend. Closing date: 2026-10-20.",
        "salary": "₹25,000 - ₹30,000 a month",
        "link": "https://jooble.org/desc/987",
        "type": "Internship",
        "updated": "2026-09-26T00:00:00",
    }
    normalized = provider.normalize_job(raw)
    assert normalized is not None
    assert normalized["job_type"] == "internship"
    assert normalized["stipend"] == 25000
    assert normalized["stipend_min"] == 25000
    # stipend_max derived from text range — at minimum should not be less than stipend_min
    assert normalized["stipend_max"] is None or normalized["stipend_max"] >= 25000
    assert normalized["application_deadline"] is not None
    assert "2026-10-20" in normalized["application_deadline"]
    assert normalized["registration_closing_date"] == normalized["application_deadline"]


def test_job_out_schema_deadline():
    payload = {
        "id": "test_schema_1",
        "source": "jsearch",
        "title": "ML Engineer",
        "company": "Deep Labs",
        "industry": "Technology",
        "description": "Build and train ML models.",
        "skills_required": ["Python", "PyTorch"],
        "skills_nice_to_have": [],
        "job_type": "full_time",
        "location": "Bengaluru",
        "is_remote": False,
        "salary_min": None,
        "salary_max": None,
        "salary_disclosed": False,
        "stipend_min": None,
        "internship_duration_months": None,
        "fresher_friendly": False,
        "apply_url": "https://example.com/apply",
        "application_deadline": "2026-12-15T00:00:00Z",
        "registration_closing_date": "2026-12-15T00:00:00Z",
        "end_date": "2026-12-15T00:00:00Z",
    }
    job_out = JobOut(**payload)
    assert job_out.application_deadline == "2026-12-15T00:00:00Z"
    assert job_out.registration_closing_date == "2026-12-15T00:00:00Z"
    assert job_out.end_date == "2026-12-15T00:00:00Z"
    dumped = job_out.model_dump()
    assert dumped["application_deadline"] == "2026-12-15T00:00:00Z"
    assert dumped["end_date"] == "2026-12-15T00:00:00Z"


def test_public_feed_allows_only_verified_direct_ats_sources():
    provider = CuratedJobProvider(None)
    query = provider._build_mongo_query({
        "active_discovery_only": True,
        "direct_apply_only": True,
        "include_benchmarks": True,
    })
    status_clause = next(
        clause for clause in query["$and"]
        if clause.get("verification_status") == "VERIFIED_ACTIVE"
    )
    assert status_clause["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert status_clause["source"] == {"$in": ("ashby", "greenhouse", "lever", "smartrecruiters")}

    default_query = provider._build_mongo_query({"include_benchmarks": True})
    default_status_clause = next(
        clause for clause in default_query["$and"]
        if clause.get("verification_status") == "VERIFIED_ACTIVE"
    )
    assert default_status_clause["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert default_status_clause["source"] == {"$in": ("ashby", "greenhouse", "lever", "smartrecruiters")}


def test_internship_filter_excludes_non_internship_roles():
    provider = CuratedJobProvider(None)
    query = provider._build_mongo_query({"job_type": "internship"})

    internship_clause = next(
        clause for clause in query["$and"]
        if "$or" in clause and any("opportunity_type" in branch for branch in clause["$or"])
    )
    assert internship_clause["$or"] == [
        {"opportunity_type": {"$in": ["INTERNSHIP", "internship"]}},
        {"title": {"$regex": r"\b(intern|internship|co-?op)\b", "$options": "i"}},
    ]
    assert "job_type" not in query or query["job_type"] != "internship"


def test_max_posted_days_filters_using_posted_or_first_seen_date():
    provider = CuratedJobProvider(None)
    query = provider._build_mongo_query({"max_posted_days": 60})

    freshness_clause = next(
        clause for clause in query["$and"]
        if "$or" in clause and any("posted_at" in branch for branch in clause["$or"])
    )
    assert any(
        branch.get("posted_days_ago") == {"$lte": 60}
        for branch in freshness_clause["$or"]
    )
    assert freshness_clause["$or"][0]["posted_at"]["$gte"]
    assert freshness_clause["$or"][1]["first_seen_at"]["$gte"]


@pytest.mark.parametrize(
    ("workplace_type", "expected_types"),
    [
        ("remote", {"REMOTE", "remote"}),
        ("hybrid", {"HYBRID", "hybrid"}),
        ("on_site", {"ON_SITE", "ONSITE", "on_site", "onsite"}),
    ],
)
def test_workplace_filter_includes_normalized_workplace_types(workplace_type, expected_types):
    provider = CuratedJobProvider(None)
    query = provider._build_mongo_query({"workplace_type": workplace_type})
    workplace_clause = next(
        clause for clause in query["$and"]
        if "$or" in clause and any("workplace_type" in branch for branch in clause["$or"])
    )
    values = {
        value
        for branch in workplace_clause["$or"]
        if "workplace_type" in branch
        for value in branch["workplace_type"].get("$in", [])
    }
    assert values == expected_types
    if workplace_type == "on_site":
        legacy_fallback = next(
            branch["$and"]
            for branch in workplace_clause["$or"]
            if "$and" in branch
        )
        exclusions = next(
            clause["workplace_type"]["$nin"]
            for clause in legacy_fallback
            if "workplace_type" in clause
        )
        assert {"HYBRID", "hybrid", "REMOTE", "remote"} <= set(exclusions)
        assert {"location": {"$not": {"$regex": "remote|hybrid", "$options": "i"}}} in legacy_fallback


@pytest.mark.asyncio
async def test_salary_sort_prioritizes_disclosed_compensation(monkeypatch):
    provider = CuratedJobProvider(None)
    captured_sort = None

    async def capture_find_jobs(db, mongo_filter, limit, skip, sort):
        nonlocal captured_sort
        captured_sort = sort
        return []

    monkeypatch.setattr("app.modules.jobs.providers.repo.find_jobs", capture_find_jobs)
    await provider.search({"sort_by": "salary"})
    assert captured_sort[0] == ("salary_disclosed", -1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sort_by", "expected_first"),
    [
        ("recent", ("posted_days_ago", 1)),
        ("stipend", ("stipend", -1)),
    ],
)
async def test_opportunity_sort_options_use_requested_order(monkeypatch, sort_by, expected_first):
    provider = CuratedJobProvider(None)
    captured_sort = None

    async def capture_find_jobs(db, mongo_filter, limit, skip, sort):
        nonlocal captured_sort
        captured_sort = sort
        return []

    monkeypatch.setattr("app.modules.jobs.providers.repo.find_jobs", capture_find_jobs)
    await provider.search({"sort_by": sort_by})
    assert captured_sort[0] == expected_first


def test_legacy_provider_experience_uses_jd_bounds_instead_of_placeholder():
    job = {
        "source": "ashby",
        "title": "Software Engineering Intern",
        "description": "This role requires 5+ years of relevant experience.",
        "experience_min": 0,
        "experience_max": 2,
    }
    normalize_provider_experience(job)
    assert job["experience_min"] == 5
    assert job["experience_max"] is None


def test_legacy_provider_experience_stays_unknown_without_jd_requirement():
    job = {
        "source": "lever",
        "title": "Software Engineering Intern",
        "description": "Open to current students studying computer science.",
        "experience_min": 0,
        "experience_max": 2,
    }
    normalize_provider_experience(job)
    assert job["experience_min"] is None
    assert job["experience_max"] is None


def test_entry_level_label_does_not_infer_numeric_experience():
    assert extract_experience_bounds("Entry-level role; freshers welcome.") == (None, None)
