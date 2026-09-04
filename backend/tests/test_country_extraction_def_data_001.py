"""
Test Suite: DEF-DATA-001 - Opportunity country extraction and India-first separation.

Tests scenarios A through J:
A. Bengaluru, India -> India
B. Bangalore, India -> India
C. San Francisco, CA, United States -> United States
D. Dubai, United Arab Emirates -> United Arab Emirates
E. London, United Kingdom -> United Kingdom
F. Multi-location US listing -> United States
G. Remote alone -> None
H. Unknown location -> None
I. Missing location / None -> None
J. India-first relevance remains separate from actual country
"""
import pytest
from app.modules.jobs.location_normalization import (
    extract_country_from_location,
    is_india_opportunity,
    normalize_india_location,
)
from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
from app.modules.matching.services import build_india_metadata


class TestCountryExtractionDefData001:

    # A. Bengaluru, India
    def test_scenario_a_bengaluru_india(self):
        assert extract_country_from_location("Bengaluru, India") == "India"
        assert extract_country_from_location("Bengaluru-VTP, India") == "India"

    # B. Bangalore, India
    def test_scenario_b_bangalore_india(self):
        assert extract_country_from_location("Bangalore, India") == "India"
        assert extract_country_from_location("Bangalore - Whitefield, India") == "India"
        assert extract_country_from_location("Bangalore, Karnataka") == "India"

    # C. San Francisco, CA, United States
    def test_scenario_c_san_francisco_us(self):
        assert extract_country_from_location("San Francisco, CA, United States") == "United States"
        assert extract_country_from_location("Austin, Texas, United States") == "United States"
        assert extract_country_from_location("New York, NY, USA") == "United States"
        assert extract_country_from_location("United States") == "United States"

    # D. Dubai, United Arab Emirates
    def test_scenario_d_dubai_uae(self):
        assert extract_country_from_location("Dubai, United Arab Emirates") == "United Arab Emirates"
        assert extract_country_from_location("Dubai, Dubai, United Arab Emirates") == "United Arab Emirates"
        assert extract_country_from_location("Abu Dhabi, UAE") == "United Arab Emirates"

    # E. London, United Kingdom
    def test_scenario_e_london_uk(self):
        assert extract_country_from_location("London, United Kingdom") == "United Kingdom"
        assert extract_country_from_location("Edinburgh, Scotland, UK") == "United Kingdom"

    # F. Multi-location US listing
    def test_scenario_f_multi_location_us_listing(self):
        loc = "Berkeley, California, United States; San Francisco, California, United States"
        assert extract_country_from_location(loc) == "United States"
        loc2 = "San Francisco, CA • New York, NY • United States"
        assert extract_country_from_location(loc2) == "United States"

    # G. Remote alone -> None
    def test_scenario_g_remote_alone(self):
        assert extract_country_from_location("Remote") is None
        assert extract_country_from_location("remote") is None
        assert extract_country_from_location("Fully Remote") is None
        assert extract_country_from_location("Work from anywhere") is None

    # H. Unknown location -> None
    def test_scenario_h_unknown_location(self):
        assert extract_country_from_location("Unknown") is None
        assert extract_country_from_location("Not specified") is None
        assert extract_country_from_location("N/A") is None
        assert extract_country_from_location("Flexible") is None

    # I. Missing location / None -> None
    def test_scenario_i_missing_location(self):
        assert extract_country_from_location(None) is None
        assert extract_country_from_location("") is None
        assert extract_country_from_location("   ") is None

    # J. India-first relevance remains separate from actual country
    def test_scenario_j_india_relevance_remains_separate(self):
        # US job
        us_loc = "Berkeley, California, United States"
        assert extract_country_from_location(us_loc) == "United States"
        assert is_india_opportunity(us_loc) is False

        # India job
        in_loc = "Bengaluru, Karnataka, India"
        assert extract_country_from_location(in_loc) == "India"
        assert is_india_opportunity(in_loc) is True

        # Unknown remote job
        remote_loc = "Remote"
        assert extract_country_from_location(remote_loc) is None
        assert is_india_opportunity(remote_loc) is False

        # Remote - US
        remote_us = "Remote - US"
        assert extract_country_from_location(remote_us) == "United States"
        assert is_india_opportunity(remote_us) is False

        # Remote - India
        remote_in = "Remote - India"
        assert extract_country_from_location(remote_in) == "India"
        assert is_india_opportunity(remote_in) is True

    # Greenhouse provider normalization derivation
    def test_greenhouse_provider_normalizes_country(self):
        provider = GreenhouseJobProvider.__new__(GreenhouseJobProvider)
        raw_us = {
            "id": 101,
            "title": "Software Engineer",
            "location": {"name": "San Francisco, CA, United States"},
            "content": "Python developer role",
            "absolute_url": "https://boards.greenhouse.io/test/jobs/101",
        }
        norm_us = provider.normalize_greenhouse_job(raw_us, "testcorp")
        assert norm_us["country"] == "United States"
        assert norm_us["location"] == "San Francisco, CA, United States"

        raw_in = {
            "id": 102,
            "title": "Backend Dev",
            "location": {"name": "Bengaluru-VTP, India"},
            "content": "Go engineer role",
            "absolute_url": "https://boards.greenhouse.io/test/jobs/102",
        }
        norm_in = provider.normalize_greenhouse_job(raw_in, "groww")
        assert norm_in["country"] == "India"
        assert norm_in["location"] == "Bengaluru-VTP, India"

        raw_remote = {
            "id": 103,
            "title": "Data Analyst",
            "location": {"name": "Remote"},
            "content": "SQL analyst role",
            "absolute_url": "https://boards.greenhouse.io/test/jobs/103",
        }
        norm_remote = provider.normalize_greenhouse_job(raw_remote, "testcorp")
        assert norm_remote["country"] is None
        assert norm_remote["location"] == "Remote"

    # Metadata builder respects extracted country without hardcoded India
    def test_build_india_metadata_country_integrity(self):
        us_job = {
            "title": "Staff Engineer",
            "location": "San Francisco, CA, United States",
            "job_type": "full_time",
        }
        meta_us = build_india_metadata(us_job, None, None, None)
        assert meta_us["country"] == "United States"

        in_job = {
            "title": "Junior Engineer",
            "location": "Bengaluru, India",
            "job_type": "full_time",
        }
        meta_in = build_india_metadata(in_job, None, None, None)
        assert meta_in["country"] == "India"

        remote_job = {
            "title": "Frontend Engineer",
            "location": "Remote",
            "job_type": "full_time",
        }
        meta_remote = build_india_metadata(remote_job, None, None, None)
        assert meta_remote["country"] is None
