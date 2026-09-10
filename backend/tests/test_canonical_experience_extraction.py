"""
Regression tests for Canonical Experience Extraction, Normalization, and Persistence.
Verifies that explicit experience ranges and plus-notations from employer descriptions
are accurately extracted without false positives or architecture redesign.
"""
import pytest
from app.modules.jobs.taxonomy import (
    analyze_job_description,
    _extract_experience_from_text,
)


def test_required_experience_formats():
    test_matrix = [
        ("Experience: 3+ to 7 yrs", 3.0, 7.0),
        ("Experience: 3-7 years", 3.0, 7.0),
        ("Experience: 3 to 7 years", 3.0, 7.0),
        ("Experience: 3+ years", 3.0, None),
        ("Experience: 3+ yrs", 3.0, None),
        ("Exp: 2+ yrs", 2.0, None),
        ("Total Experience: 5–8 years", 5.0, 8.0),
        ("3+ to 7 yrs", 3.0, 7.0),
        ("3-7 years", 3.0, 7.0),
        ("3 to 7 years", 3.0, 7.0),
        ("3+ years", 3.0, None),
        ("minimum 3 years", 3.0, None),
        ("at least 2 years", 2.0, None),
        ("5–8 years", 5.0, 8.0),
        ("0–2 years", 0.0, 2.0),
        ("2+ years", 2.0, None),
        ("up to 5 years", 0.0, 5.0),
        ("5 years of experience", 5.0, None),
        ("7 years of professional experience", 7.0, None),
    ]

    for text, expected_min, expected_max in test_matrix:
        min_y, max_y, raw = _extract_experience_from_text(text)
        assert min_y == expected_min, f"Failed min for '{text}': got {min_y}, expected {expected_min}"
        assert max_y == expected_max, f"Failed max for '{text}': got {max_y}, expected {expected_max}"
        assert raw is not None, f"Expected raw matching text for '{text}'"


def test_false_positive_experience_cases():
    false_positives = [
        "Blueberry is seeking an experienced Full Stack Professional to join our team",
        "We are looking for senior developers and lead engineers",
        "Founded 25 years ago in California",
        "Established company with history of innovation",
        "Over 100 years of combined team experience",
        "Firm with 20 years in business",
        "Class of 2024 graduates welcome to apply",
        "Batch of 2023 engineering graduates",
        "3 months notice period required",
        "6-month internship duration with certificate",
        "Project duration is 12 weeks",
    ]

    for text in false_positives:
        min_y, max_y, _ = _extract_experience_from_text(text)
        assert min_y is None, f"False positive min triggered for '{text}': got {min_y}"
        assert max_y is None, f"False positive max triggered for '{text}': got {max_y}"


def test_blueberry_full_stack_job_description_analysis():
    jd_snippet = """
## Company Description
Blueberry Digital Labs is a leading integrated digital technology Company.

## Job Description
Job position: Full-time
Location: Waverock SEZ, Gachibowli, Hyderabad
Department: Technical
Experience: 3+ to 7 yrs

JOB DESCRIPTION

Job Summary:
Blueberry is seeking an experienced Full Stack Professional to join our innovative team in Hyderabad.

Required skills:
● Expertise in Complete Mean, Node js, Mongo DB, Angular js and Express js
● Expertise in PHP, jQuery, MySQL, Symfony, OOPS

## Qualifications
B-Tech, M-Tech, MCA from reputed Colleges
"""
    reqs = analyze_job_description(jd_snippet, "Full Stack Developer")
    assert reqs.min_years_experience == 3.0, f"Expected 3.0, got {reqs.min_years_experience}"
    assert reqs.max_years_experience == 7.0, f"Expected 7.0, got {reqs.max_years_experience}"
    assert "3+ to 7 yrs" in (reqs.experience_requirements or "")


@pytest.mark.asyncio
async def test_blueberry_full_stack_mongodb_and_api():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings
    from app.modules.jobs import services
    from app.db.mongo import Collections

    try:
        settings = get_settings()
        client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=2000)
        db = client[settings.MONGO_DB_NAME]
        # Quick ping to verify connectivity
        await client.admin.command("ping")
    except Exception as exc:
        pytest.skip(f"MongoDB not available: {exc}")

    job_id = "smartrecruiters_blueberrylabsprivatelimited_113819707"
    doc = await db[Collections.JOBS].find_one({"id": job_id})
    if doc is None:
        pytest.skip(f"Opportunity {job_id} not present in database")

    # Run canonical service resolution
    reqs = await services.get_canonical_job_requirements(db, doc)
    assert reqs.min_years_experience == 3.0
    assert reqs.max_years_experience == 7.0

    # Verify MongoDB persistence
    updated_doc = await db[Collections.JOBS].find_one({"id": job_id})
    assert updated_doc["experience_min"] == 3
    assert updated_doc["experience_max"] == 7

    # Verify eligibility computation reflects canonical bounds
    from app.modules.jobs.eligibility import evaluate_eligibility
    elig = evaluate_eligibility(
        candidate_profile={"experience_years": 5},
        master_resume=None,
        job=updated_doc,
    )
    assert elig.required_experience_min == 3
    assert elig.required_experience_max == 7
    assert elig.status.value in ("ELIGIBLE", "LIKELY_ELIGIBLE")
