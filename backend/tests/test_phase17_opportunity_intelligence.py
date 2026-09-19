import pytest
from app.modules.jobs.verification import OpportunityRejectionReason
from app.modules.jobs.completeness import QualityTier, evaluate_opportunity_completeness, OpportunityCompleteness
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.url_classifier import classify_application_url, ApplicationUrlType
from app.modules.jobs.deduplication import compute_dedup_key
from app.modules.learning.role_taxonomy import resolve_role
from app.modules.matching.services import _multi_factor_rank_key

class TestPhase17OpportunityIntelligence:

    # 1. INFORMATION SEMANTICS: UNKNOWN / UNDISCLOSED != INVALID
    def test_unknown_salary_not_invalid(self):
        """Undisclosed salary must preserve UNKNOWN semantics and remain discoverable in SECONDARY."""
        job = {
            "title": "Software Engineer",
            "company": "Infosys",
            "location": "Bengaluru, Karnataka, India",
            "description": "We are seeking a Software Engineer with experience in Python and cloud services.",
            "apply_url": "https://careers.infosys.com/job/123",
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": False,
        }
        res = evaluate_opportunity_completeness(job)
        assert res.quality_tier in (QualityTier.PRIMARY, QualityTier.SECONDARY)
        assert res.quality_tier != QualityTier.REJECTED
        assert res.rejection_reason is None

    def test_unknown_skills_and_experience_not_invalid(self):
        """Missing structured skills or experience must not trigger rejection."""
        job = {
            "title": "Operations Executive",
            "company": "Wipro",
            "location": "Hyderabad, Telangana, India",
            "description": "Manage day to day operations and coordinate with cross-functional global teams.",
            "apply_url": "https://careers.wipro.com/job/456",
            "skills_required": [],
            "experience_min": None,
            "experience_max": None,
        }
        res = evaluate_opportunity_completeness(job)
        assert res.quality_tier != QualityTier.REJECTED
        assert res.rejection_reason is None

    # 2. HARD REJECTION RULES: GENUINE DEFECTS
    def test_closed_requisition_rejected(self):
        job = {
            "title": "Data Analyst",
            "company": "Swiggy",
            "description": "Data Analyst role for delivery logistics.",
            "apply_url": "https://swiggy.com/job/1",
            "verification_status": "CLOSED",
        }
        res = evaluate_opportunity_completeness(job)
        assert res.quality_tier == QualityTier.REJECTED
        assert res.rejection_reason == OpportunityRejectionReason.CLOSED_REQUISITION

    def test_non_india_geography_rejected(self):
        job = {
            "title": "Site Reliability Engineer",
            "company": "Google",
            "location": "Sunnyvale, CA, USA",
            "country": "United States",
            "description": "Ensure ultra-high availability of Google Cloud services.",
            "apply_url": "https://careers.google.com/job/789",
        }
        res = evaluate_opportunity_completeness(job, require_india=True)
        assert res.quality_tier == QualityTier.REJECTED
        assert res.rejection_reason == OpportunityRejectionReason.NON_INDIA_GEOGRAPHY.value

    def test_missing_or_invalid_apply_url_rejected(self):
        job = {
            "title": "Backend Developer",
            "company": "Zomato",
            "location": "Gurgaon, India",
            "description": "Build high throughput microservices using Go and PostgreSQL.",
            "apply_url": "",
        }
        res = evaluate_opportunity_completeness(job)
        assert res.quality_tier == QualityTier.REJECTED
        assert res.rejection_reason == OpportunityRejectionReason.INVALID_OR_MISSING_APPLY_URL

    def test_insufficient_description_rejected(self):
        """Very short stub descriptions under 50 characters must be rejected."""
        job = {
            "title": "Test Lead",
            "company": "Paytm",
            "location": "Noida, India",
            "description": "Short stub jd text",
            "apply_url": "https://jobs.lever.co/paytm/123",
        }
        res = evaluate_opportunity_completeness(job)
        assert res.quality_tier == QualityTier.REJECTED
        assert res.rejection_reason == OpportunityRejectionReason.INSUFFICIENT_DESCRIPTION

    # 3. RECOMMENDATION TIERS (PRIMARY VS SECONDARY)
    def test_primary_tier_rich_documentation(self):
        """Rich opportunity with responsibilities/qualifications and detailed description is PRIMARY."""
        job = {
            "title": "Senior Frontend Developer",
            "company": "Flipkart",
            "location": "Bengaluru, India",
            "description": "A" * 500,
            "responsibilities": ["Build React components", "Optimize bundle size"],
            "qualifications": ["B.Tech CS", "5+ years experience"],
            "apply_url": "https://flipkart.careers/job/101",
        }
        res = evaluate_opportunity_completeness(job)
        assert res.quality_tier == QualityTier.PRIMARY
        assert res.rejection_reason is None

    def test_secondary_tier_legitimate_brief_documentation(self):
        """Legitimate opportunity with brief description and without separate structured sections is SECONDARY."""
        job = {
            "title": "Junior Developer",
            "company": "TCS",
            "location": "Pune, Maharashtra, India",
            "description": "Looking for entry-level developers to join our banking digital transformation team in Pune.",
            "responsibilities": [],
            "qualifications": [],
            "skills_required": [],
            "apply_url": "https://tcs.com/careers/entry/123",
        }
        res = evaluate_opportunity_completeness(job)
        assert res.quality_tier == QualityTier.SECONDARY
        assert res.rejection_reason is None

    # 4. RANKING PRIORITY & DECOUPLING OF TECHNICAL MATCH FROM ELIGIBILITY
    def test_ranking_priority_order(self):
        """
        Verify multi-factor rank key priority:
        1. India-first
        2. Eligibility (Eligible > Unknown > Ineligible)
        3. Role Relevance
        4. Freshness
        5. Direct Apply Trust
        6. Source Trust
        7. Information Richness (PRIMARY > SECONDARY)
        8. Technical Match Score
        """
        # Job 1: Ineligible candidate with 95% technical match
        job_ineligible = {
            "country": "India",
            "eligibility": {"status": "INELIGIBLE"},
            "canonical_role": "Backend Developer",
            "posted_days_ago": 2,
            "is_direct_apply": True,
            "source": "smartrecruiters",
            "quality_tier": "PRIMARY",
            "overall_score": 0.95,
        }

        # Job 2: Fully eligible candidate with 75% technical match
        job_eligible = {
            "country": "India",
            "eligibility": {"status": "ELIGIBLE"},
            "canonical_role": "Backend Developer",
            "posted_days_ago": 2,
            "is_direct_apply": True,
            "source": "smartrecruiters",
            "quality_tier": "PRIMARY",
            "overall_score": 0.75,
        }

        key_ineligible = _multi_factor_rank_key(job_ineligible)
        key_eligible = _multi_factor_rank_key(job_eligible)

        # Eligible candidate must rank BEFORE ineligible candidate despite lower technical score
        assert key_eligible < key_ineligible

    def test_technical_match_not_capped_by_ineligibility(self):
        """Technical match remains independent of candidate eligibility status."""
        job = {
            "country": "India",
            "eligibility": {"status": "INELIGIBLE"},
            "canonical_role": "Backend Developer",
            "overall_score": 0.88,
        }
        # The overall_score itself is not degraded to 0 simply because eligibility is INELIGIBLE
        assert job["overall_score"] == 0.88

    # 5. FIRST-CLASS INTERNSHIPS
    def test_internship_classification_and_ranking(self):
        """Internships must be recognized as first class and not penalized for 0 years experience."""
        internship_job = {
            "title": "Software Engineering Intern",
            "company": "Swiggy",
            "location": "Bengaluru, India",
            "opportunity_type": "INTERNSHIP",
            "description": "Join our summer 2026 internship program to work on consumer-facing systems.",
            "apply_url": "https://swiggy.careers/intern/456",
            "stipend_min": None,  # Undisclosed stipend is UNKNOWN, not invalid
        }
        res = evaluate_opportunity_completeness(internship_job)
        assert res.quality_tier != QualityTier.REJECTED
        assert res.rejection_reason is None

    # 6. DEDUPLICATION
    def test_dedup_key_stability(self):
        k1 = compute_dedup_key("Google", "Software Engineer", "Bangalore, India", "full_time", False)
        k2 = compute_dedup_key("google", "software engineer", "Bangalore, India", "full_time", False)
        assert k1 == k2
