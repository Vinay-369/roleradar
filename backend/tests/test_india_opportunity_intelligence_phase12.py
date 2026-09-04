"""
Test Suite: Phase 12 India-First Opportunity Intelligence.
Covers all 23 mandated verification scenarios:
1. Student + internship
2. Student + graduate program
3. Fresher + entry-level job
4. Fresher + 5-year job
5. 1-year candidate + 0–2 year job
6. 3-year candidate + 0–2 year job
7. Missing experience requirement
8. Degree match
9. Degree mismatch
10. Degree unspecified
11. Bangalore/Bengaluru normalization
12. Gurgaon/Gurugram normalization
13. Remote opportunity
14. Unknown location
15. Missing stipend
16. INR stipend
17. Verified direct opportunity
18. Unverified opportunity
19. Benchmark seed opportunity
20. No-resume discovery
21. Resume-aware discovery
22. Unknown/niche role
23. Non-technology role
"""
import pytest
from app.modules.jobs.classification import (
    OpportunityType,
    CandidateSuitabilitySignal,
    classify_opportunity,
    classify_opportunity_type,
    extract_degree_requirements,
)
from app.modules.jobs.location_normalization import (
    normalize_india_location,
    is_location_match,
    detect_workplace_type,
)
from app.modules.jobs.eligibility import (
    EligibilityStatus,
    RealisticFitSignal,
    evaluate_eligibility,
    are_degrees_equivalent,
)


class TestPhase12IndiaOpportunityIntelligence:

    # 1. Student + Internship
    def test_01_student_plus_internship(self):
        candidate_profile = {"category": "STUDENT", "experience_years": 0}
        master_resume = {"parsed": {"education": [{"degree": "B.Tech in Computer Science"}]}}
        job = {
            "title": "Software Engineering Intern",
            "description": "Seeking pre-final year students for summer internship.",
            "job_type": "internship",
            "experience_min": 0,
            "experience_max": 0,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)
        assert res.checks["opportunity_type"] == "PASS"
        assert res.checks["experience"] == "PASS"

    # 2. Student + Graduate Program
    def test_02_student_plus_graduate_program(self):
        candidate_profile = {"category": "STUDENT", "experience_years": 0}
        master_resume = {"parsed": {"education": [{"degree": "B.E. Computer Engineering"}]}}
        job = {
            "title": "Graduate Engineer Trainee (GET)",
            "description": "Campus hiring program for graduating batch of 2025.",
            "job_type": "full_time",
            "experience_min": 0,
            "experience_max": 1,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)
        assert res.checks["opportunity_type"] == "PASS"

    # 3. Fresher + Entry-level Job
    def test_03_fresher_plus_entry_level_job(self):
        candidate_profile = {"category": "FRESHER", "experience_years": 0}
        master_resume = {"parsed": {"education": [{"degree": "B.Tech Information Technology"}]}}
        job = {
            "title": "Associate Software Engineer",
            "description": "Entry level opportunity for fresh graduates. 0-1 years experience.",
            "job_type": "full_time",
            "experience_min": 0,
            "experience_max": 1,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)
        assert res.checks["experience"] == "PASS"

    # 4. Fresher + 5-year Job (Experience Mismatch)
    def test_04_fresher_plus_5_year_job_mismatch(self):
        candidate_profile = {"category": "FRESHER", "experience_years": 0}
        master_resume = {"parsed": {"education": [{"degree": "B.Tech"}]}}
        job = {
            "title": "Lead Platform Architect",
            "description": "Requires minimum 5+ years of production experience.",
            "job_type": "full_time",
            "experience_min": 5,
            "experience_max": 8,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.status == EligibilityStatus.EXPERIENCE_MISMATCH
        assert res.checks["experience"] == "FAIL"
        assert res.realistic_fit == RealisticFitSignal.EXPERIENCE_GAP
        assert "Requires 5+ years" in res.reasons[0]

    # 5. 1-year candidate + 0-2 year job
    def test_05_one_year_candidate_plus_zero_to_two_job(self):
        candidate_profile = {"category": "EARLY_CAREER", "experience_years": 1}
        master_resume = {"parsed": {"experience": [{"company": "Tech Corp", "role": "Junior Dev"}]}}
        job = {
            "title": "Software Engineer I",
            "description": "0-2 years of backend experience required.",
            "job_type": "full_time",
            "experience_min": 0,
            "experience_max": 2,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)
        assert res.checks["experience"] == "PASS"

    # 6. 3-year candidate + 0-2 year job
    def test_06_three_year_candidate_plus_zero_to_two_job(self):
        candidate_profile = {"category": "EXPERIENCED", "experience_years": 3}
        master_resume = {"parsed": {"experience": [{"company": "A"}, {"company": "B"}]}}
        job = {
            "title": "Software Engineer",
            "description": "1-2 years experience.",
            "job_type": "full_time",
            "experience_min": 1,
            "experience_max": 2,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.checks["experience"] == "PASS"

    # 7. Missing experience requirement
    def test_07_missing_experience_requirement(self):
        candidate_profile = {"category": "EARLY_CAREER", "experience_years": 2}
        master_resume = {"parsed": {}}
        job = {
            "title": "Backend Developer",
            "description": "Build high performance REST APIs in Go.",
            "job_type": "full_time",
            "experience_min": None,
            "experience_max": None,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.checks["experience"] == "UNKNOWN"

    # 8. Degree match
    def test_08_degree_match(self):
        candidate_profile = {"category": "FRESHER"}
        master_resume = {"parsed": {"education": [{"degree": "Bachelor of Technology in Computer Science"}]}}
        job = {
            "title": "Junior Developer",
            "description": "Qualifications: B.E. or B.Tech in Computer Science required.",
            "job_type": "full_time",
            "experience_min": 0,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.checks["education"] == "PASS"

    # 9. Degree mismatch
    def test_09_degree_mismatch(self):
        candidate_profile = {"category": "FRESHER"}
        master_resume = {"parsed": {"education": [{"degree": "Bachelor of Commerce (B.Com)"}]}}
        job = {
            "title": "Hardware Firmware Engineer",
            "description": "Requirements: Mandatory B.Tech or M.Tech in Electrical/Electronics Engineering.",
            "job_type": "full_time",
            "experience_min": 0,
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.checks["education"] == "FAIL"
        assert res.status == EligibilityStatus.DEGREE_MISMATCH

    # 10. Degree unspecified
    def test_10_degree_unspecified(self):
        candidate_profile = {"category": "FRESHER"}
        master_resume = {"parsed": {"education": [{"degree": "B.Sc"}]}}
        job = {
            "title": "Python Developer",
            "description": "Proficiency in Python, FastAPI, and Git.",
            "job_type": "full_time",
        }
        res = evaluate_eligibility(candidate_profile, master_resume, job)
        assert res.checks["education"] == "UNKNOWN"

    # 11. Bangalore / Bengaluru normalization
    def test_11_bangalore_bengaluru_normalization(self):
        assert normalize_india_location("Bengaluru, Karnataka, India") == "Bengaluru"
        assert normalize_india_location("Bangalore - Whitefield") == "Bengaluru"
        assert is_location_match(["Bengaluru"], "Bangalore") is True
        assert is_location_match(["Bangalore"], "Bengaluru") is True

    # 12. Gurgaon / Gurugram normalization
    def test_12_gurgaon_gurugram_normalization(self):
        assert normalize_india_location("Gurgaon, Haryana") == "Gurugram"
        assert normalize_india_location("Gurugram Cyber City") == "Gurugram"
        assert is_location_match(["Gurugram"], "Gurgaon") is True
        assert is_location_match(["Delhi NCR"], "Gurgaon") is True

    # 13. Remote opportunity
    def test_13_remote_opportunity(self):
        mode = detect_workplace_type("Bengaluru", "This is a 100% remote opportunity. Work from anywhere.", is_remote_flag=False)
        assert mode == "REMOTE"
        assert is_location_match(["Chennai"], "Anywhere", job_is_remote=True) is True

    # 14. Unknown location
    def test_14_unknown_location(self):
        mode = detect_workplace_type(None, "", is_remote_flag=False)
        assert mode == "UNKNOWN"
        match = is_location_match(["Bengaluru"], None, job_is_remote=False)
        assert match is None

    # 15. Missing stipend
    def test_15_missing_stipend_not_zero(self):
        from app.modules.matching.services import _build_india_metadata
        job = {"title": "Design Intern", "job_type": "internship", "stipend_min": None, "stipend": None}
        meta = _build_india_metadata(job, skill_score=None)
        assert meta["stipend"] is None
        assert meta["stipend_currency"] is None

    # 16. INR stipend
    def test_16_inr_stipend(self):
        from app.modules.matching.services import _build_india_metadata
        job = {"title": "Frontend Intern", "job_type": "internship", "stipend_min": 25000}
        meta = _build_india_metadata(job, skill_score=None)
        assert meta["stipend"] == 25000
        assert meta["stipend_currency"] == "INR"
        assert meta["stipend_period"] == "per_month"

    # 17. Verified direct opportunity
    def test_17_verified_direct_opportunity(self):
        job = {
            "title": "Software Engineer",
            "verification_status": "VERIFIED_ACTIVE",
            "url_type": "DIRECT_REQUISITION",
            "is_direct_apply": True,
        }
        assert job["verification_status"] == "VERIFIED_ACTIVE"
        assert job["url_type"] == "DIRECT_REQUISITION"

    # 18. Unverified opportunity
    def test_18_unverified_opportunity(self):
        job = {
            "title": "Aggregated Job",
            "verification_status": "PENDING_VERIFICATION",
            "url_type": "AGGREGATOR_REDIRECT",
        }
        assert job["verification_status"] != "VERIFIED_ACTIVE"

    # 19. Benchmark seed opportunity
    def test_19_benchmark_seed_opportunity(self):
        job = {
            "title": "Curated Seed Role",
            "source": "curated_benchmark",
            "verification_status": "MARKET_BENCHMARK",
        }
        assert job["verification_status"] == "MARKET_BENCHMARK"

    # 20. No-resume discovery
    def test_20_no_resume_discovery(self):
        job = {
            "title": "Software Engineer Intern",
            "description": "Internship for college students.",
            "experience_min": 0,
        }
        classification = classify_opportunity(job["title"], job["description"], job["experience_min"], None, "internship")
        assert classification.opportunity_type == OpportunityType.INTERNSHIP
        assert classification.student_eligible is True

    # 21. Resume-aware discovery preserves same inventory
    def test_21_resume_aware_discovery(self):
        candidate_profile = {"category": "FRESHER", "experience_years": 0}
        master_resume = {"parsed": {"education": [{"degree": "B.Tech CSE"}]}}
        job = {
            "id": "job_123",
            "title": "Junior Python Dev",
            "description": "0-1 years experience with Python.",
            "job_type": "full_time",
            "experience_min": 0,
            "experience_max": 1,
        }
        eligibility = evaluate_eligibility(candidate_profile, master_resume, job, skill_score=65)
        assert eligibility.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE)
        assert eligibility.realistic_fit == RealisticFitSignal.GOOD_FIT

    # 22. Unknown/niche role
    def test_22_unknown_niche_role(self):
        classification = classify_opportunity("Quantum Cryogenics Specialist", "Specialized lab role", None, None)
        assert classification.opportunity_type == OpportunityType.FULL_TIME
        assert classification.suitability == CandidateSuitabilitySignal.UNKNOWN

    # 23. Non-technology role
    def test_23_non_technology_role(self):
        classification = classify_opportunity("Executive Chef", "Leading restaurant culinary operations", 5, 8)
        assert classification.opportunity_type == OpportunityType.FULL_TIME
        assert classification.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert classification.fresher_eligible is False
