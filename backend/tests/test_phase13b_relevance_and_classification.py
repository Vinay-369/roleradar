"""
Test Suite: Phase 13B - India Opportunity Relevance & Fresher Classification Hardening.

Covers:
India Relevance:
A. Bengaluru, India + no India in description -> true
B. Bangalore, India + no India in description -> true
C. San Francisco, United States + description mentions Bangalore -> false
D. Dubai, UAE + description mentions India -> false
E. London, UK + description mentions Bangalore -> false
F. Remote alone -> false (no fabricated relevance)
G. Multi-location India -> true
H. Multi-location foreign -> false
I. Mixed India + foreign -> true (India location semantics)

Country Integrity:
J. US location -> United States
K. India location -> India
L. Remote unknown -> None

Seniority & Fresher Classification:
M. SDE II -> not fresher eligible
N. SDE III -> not fresher eligible
O. SDE IV -> not fresher eligible
P. Software Engineer III -> not fresher eligible
Q. Senior Software Engineer -> not fresher eligible
R. Staff Engineer -> not fresher eligible
S. Principal Engineer -> not fresher eligible
T. Lead Engineer -> not fresher eligible
U. Engineering Manager -> not fresher eligible
V. Explicit 0-1 year Associate Engineer -> fresher eligible
W. Explicit 0-1 year Graduate Engineer Trainee -> fresher eligible

Phase 13A Real-World Regressions:
1. InMobi Cairo, Egypt (boilerplate Bangalore) -> is_india_opportunity == False, country == "Egypt"
2. Airbnb Manila, Philippines (boilerplate Bangalore) -> is_india_opportunity == False, country == "Philippines"
3. InMobi SDE III (Lucknow) -> is_india_opportunity == True, country == "India", fresher_eligible == False
4. Postman Enterprise Account Executive (Bengaluru) -> is_india_opportunity == True, country == "India", fresher_eligible == False
"""
import pytest
from app.modules.jobs.location_normalization import (
    extract_country_from_location,
    is_india_opportunity,
)
from app.modules.jobs.classification import (
    classify_opportunity,
    CandidateSuitabilitySignal,
    OpportunityType,
)


class TestPhase13BRelevanceAndClassification:

    # --- INDIA RELEVANCE TESTS ---

    def test_scenario_a_bengaluru_india_clean(self):
        loc = "Bengaluru, India"
        desc = "We build high performance distributed storage systems using Go and Rust."
        assert is_india_opportunity(loc, desc) is True

    def test_scenario_b_bangalore_india_clean(self):
        loc = "Bangalore, India"
        desc = "Seeking full stack software engineers."
        assert is_india_opportunity(loc, desc) is True

    def test_scenario_c_san_francisco_with_bangalore_boilerplate(self):
        loc = "San Francisco, California, United States"
        desc = "Postman is an API platform with offices in San Francisco, Bangalore, and London."
        assert is_india_opportunity(loc, desc) is False

    def test_scenario_d_dubai_with_india_boilerplate(self):
        loc = "Dubai, United Arab Emirates"
        desc = "Our team collaborates with engineering hubs across India and North America."
        assert is_india_opportunity(loc, desc) is False

    def test_scenario_e_london_with_bangalore_boilerplate(self):
        loc = "London, United Kingdom"
        desc = "Join our London engineering center. Postman has offices in Bangalore and SF."
        assert is_india_opportunity(loc, desc) is False

    def test_scenario_f_remote_alone(self):
        assert is_india_opportunity("Remote", "Any description") is False
        assert is_india_opportunity("Work from anywhere", "Any description") is False
        assert is_india_opportunity(None, "Any description") is False

    def test_scenario_g_multi_location_india(self):
        loc = "Bengaluru, India; Hyderabad, India"
        assert is_india_opportunity(loc, "") is True

    def test_scenario_h_multi_location_foreign(self):
        loc = "San Francisco, California, United States; New York, NY, United States"
        desc = "Company has development centers in Bangalore and Gurgaon."
        assert is_india_opportunity(loc, desc) is False

    def test_scenario_i_mixed_india_and_foreign(self):
        loc = "London, United Kingdom; Bengaluru, India"
        assert is_india_opportunity(loc, "") is True

    # --- COUNTRY INTEGRITY TESTS ---

    def test_scenario_j_us_country(self):
        loc = "San Francisco, California, United States"
        assert extract_country_from_location(loc) == "United States"

    def test_scenario_k_india_country(self):
        loc = "Bengaluru, Karnataka, India"
        assert extract_country_from_location(loc) == "India"

    def test_scenario_l_remote_unknown_country(self):
        assert extract_country_from_location("Remote") is None
        assert extract_country_from_location("Not specified") is None
        assert extract_country_from_location(None) is None

    # --- SENIORITY & FRESHER CLASSIFICATION TESTS ---

    def test_scenario_m_sde_ii_not_fresher(self):
        cl = classify_opportunity("SDE II", "Backend developer", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EARLY_CAREER
        assert cl.fresher_eligible is False

    def test_scenario_n_sde_iii_not_fresher(self):
        cl = classify_opportunity("SDE III", "Senior infrastructure engineer", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_o_sde_iv_not_fresher(self):
        cl = classify_opportunity("SDE IV - Data Engineer", "Lead architectural design", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_p_software_engineer_iii_not_fresher(self):
        cl = classify_opportunity("Software Engineer III", "Build core banking services", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_q_senior_software_engineer_not_fresher(self):
        cl = classify_opportunity("Senior Software Engineer", "Python backend", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_r_staff_engineer_not_fresher(self):
        cl = classify_opportunity("Staff Engineer", "Distributed systems architect", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_s_principal_engineer_not_fresher(self):
        cl = classify_opportunity("Principal Engineer", "Technical leadership", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_t_lead_engineer_not_fresher(self):
        cl = classify_opportunity("Lead Cloud Security Engineer", "Lead cloud posture", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_u_engineering_manager_not_fresher(self):
        cl = classify_opportunity("Engineering Manager - Community Support", "Manage team", experience_min=None, experience_max=None)
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_scenario_v_explicit_associate_engineer_fresher(self):
        cl = classify_opportunity(
            "Associate Engineer",
            "Entry level engineering role for 2025 graduates.",
            experience_min=0,
            experience_max=1,
        )
        assert cl.suitability == CandidateSuitabilitySignal.FRESHER
        assert cl.fresher_eligible is True

    def test_scenario_w_explicit_graduate_engineer_trainee_fresher(self):
        cl = classify_opportunity(
            "Graduate Engineer Trainee (GET)",
            "Campus recruitment program.",
            experience_min=0,
            experience_max=0,
        )
        assert cl.opportunity_type == OpportunityType.GRADUATE_PROGRAM
        assert cl.suitability == CandidateSuitabilitySignal.FRESHER
        assert cl.fresher_eligible is True

    # --- PHASE 13A REAL REGRESSIONS ---

    def test_phase13a_regression_inmobi_cairo_egypt(self):
        loc = "Egypt"
        desc = "InMobi is headquartered in Bangalore, India. Account Manager role based in Cairo."
        assert extract_country_from_location(loc) == "Egypt"
        assert is_india_opportunity(loc, desc) is False

    def test_phase13a_regression_airbnb_manila_philippines(self):
        loc = "Manila, Philippines"
        desc = "Customer support operations for APAC. Airbnb operates across India, Japan, Korea."
        assert extract_country_from_location(loc) == "Philippines"
        assert is_india_opportunity(loc, desc) is False

    def test_phase13a_regression_inmobi_sde3_lucknow(self):
        loc = "Lucknow"
        cl = classify_opportunity("SDE III - Salesforce", "Develop enterprise features", experience_min=None, experience_max=None)
        assert extract_country_from_location(loc) == "India"
        assert is_india_opportunity(loc, "") is True
        assert cl.suitability == CandidateSuitabilitySignal.EXPERIENCED
        assert cl.fresher_eligible is False

    def test_phase13a_regression_postman_account_executive(self):
        loc = "Bengaluru, Karnataka, India"
        cl = classify_opportunity("Enterprise Account Executive", "Drive revenue with strategic accounts", experience_min=None, experience_max=None)
        assert extract_country_from_location(loc) == "India"
        assert is_india_opportunity(loc, "") is True
        # Without explicit 0-1 yr requirement or junior title, sales role is UNKNOWN and not fresher eligible
        assert cl.suitability == CandidateSuitabilitySignal.UNKNOWN
        assert cl.fresher_eligible is False
