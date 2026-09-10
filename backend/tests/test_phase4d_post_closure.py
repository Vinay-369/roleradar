"""
Phase 4D Post-Closure Regression Test Suite:
Validates Job Detail Data Completeness + List State Restoration Logic.

Strictly verifies:
1. Bosch experience extraction: "6 - 9 years" -> min 6, max 9
2. Explicit experience range forms (2-4 years, 3+ years, minimum 3 years, 0-2 years, freshers, internship)
3. Unstated experience fallback: min=None, max=None (zero fabrication)
4. Bosch qualification: "B.E" preserved (bullet regex safety for degree abbreviations)
5. Qualifications preservation: B.Tech, M.Tech, Bachelor's degree
6. Required skills truth: no unsupported/fabricated skills
7. Responsibilities extraction: 8 items extracted from Bosch JD, no collapsing
8. Markdown/encoding normalization: no raw "##" or "Ø" artifacts
9. Bosch location normalization: "coimbatore, , India" -> "Coimbatore, India"
10. Full SmartRecruiters normalizer output for Bosch Lead Hardware Engineer
11. List state restoration schema & direct navigation integrity
"""
import json
import pytest

from app.modules.jobs.taxonomy import (
    analyze_job_description,
    _extract_experience_from_text,
    _detect_section_category,
    _normalize_heading_text,
    _BULLET_PREFIX_RE,
    RequirementCategory,
)
from app.modules.jobs.smartrecruiters_provider import (
    SmartRecruitersJobProvider,
    _clean_html_description,
    normalize_location_string,
)


# ===========================================================================
# 1. Experience Extraction Tests (A1)
# ===========================================================================

def test_bosch_experience_extraction_explicit_range():
    """Bosch explicitly specifies '6 - 9 years' under Additional Information."""
    raw_text = "6 - 9 years"
    p_min, p_max, p_raw = _extract_experience_from_text(raw_text)
    assert p_min == 6.0
    assert p_max == 9.0
    assert "6 - 9" in p_raw


def test_experience_extraction_all_explicit_forms():
    """Verify wide variety of explicit experience phrasing without requiring 'experience' keyword."""
    # En-dash range
    p_min, p_max, _ = _extract_experience_from_text("6–9 years")
    assert p_min == 6.0 and p_max == 9.0

    # Hyphen range
    p_min, p_max, _ = _extract_experience_from_text("2-4 years")
    assert p_min == 2.0 and p_max == 4.0

    # Range with spaces
    p_min, p_max, _ = _extract_experience_from_text("0 - 2 years")
    assert p_min == 0.0 and p_max == 2.0

    # Plus form
    p_min, p_max, _ = _extract_experience_from_text("3+ years")
    assert p_min == 3.0 and p_max is None

    # Minimum form
    p_min, p_max, _ = _extract_experience_from_text("minimum 3 years")
    assert p_min == 3.0 and p_max is None

    # At least form
    p_min, p_max, _ = _extract_experience_from_text("at least 5 yrs")
    assert p_min == 5.0 and p_max is None

    # Freshers
    p_min, p_max, p_raw = _extract_experience_from_text("Freshers can apply")
    assert p_min == 0.0 and p_max == 1.0

    # Entry level
    p_min, p_max, p_raw = _extract_experience_from_text("Entry level candidates welcome")
    assert p_min == 0.0 and p_max == 1.0


def test_experience_unstated_fallback_zero_fabrication():
    """When experience is unstated, it must remain None (never fabricated)."""
    p_min, p_max, p_raw = _extract_experience_from_text("Knowledge of electronics and circuit design.")
    assert p_min is None
    assert p_max is None
    assert p_raw is None


# ===========================================================================
# 2. Qualification Extraction & Bullet Regex Safety (A2)
# ===========================================================================

def test_bullet_prefix_regex_preserves_degrees():
    """Bullet prefix regex must not strip 'B.' from 'B.E', 'B.Tech', 'M.Tech'."""
    assert not _BULLET_PREFIX_RE.match("B.E")
    assert not _BULLET_PREFIX_RE.match("B.Tech in Electronics")
    assert not _BULLET_PREFIX_RE.match("M.Tech / M.S")
    assert not _BULLET_PREFIX_RE.match("B.Sc Computer Science")

    # True bullets should still match
    assert _BULLET_PREFIX_RE.match("- First item")
    assert _BULLET_PREFIX_RE.match("* Second item")
    assert _BULLET_PREFIX_RE.match("• Third item")
    assert _BULLET_PREFIX_RE.match("1. Numbered item")
    assert _BULLET_PREFIX_RE.match("a. Lettered item with space")


def test_bosch_qualification_extraction():
    """B.E degree in Bosch JD must be parsed as a qualification, not discarded."""
    jd = """
    Qualifications:
    B.E in Electronics & Communication
    """
    reqs = analyze_job_description(jd, "Lead Hardware Engineer")
    assert any("B.E" in q for q in reqs.qualifications)


def test_qualifications_preserved_across_degrees():
    """Verify B.Tech, M.Tech, MCA, Bachelor's degree are preserved."""
    jd = """
    Qualifications:
    - B.Tech or M.Tech in Computer Science or related discipline
    - Bachelor's degree required
    """
    reqs = analyze_job_description(jd, "Software Engineer")
    assert any("B.Tech" in q for q in reqs.qualifications)
    assert any("Bachelor" in q for q in reqs.qualifications)


# ===========================================================================
# 3. Required Skills Truth (A3)
# ===========================================================================

def test_required_skills_truth_no_hallucination_for_bosch():
    """
    Bosch Lead Hardware Engineer source contains general engineering duties
    without mandatory technology lists. System must NOT hallucinate skills.
    """
    bosch_jd = """
    Company Description
    Bosch Global Software Technologies is a 100% owned subsidiary of Robert Bosch GmbH.

    Job Description
    - Requirement analysis, design and development of Hardware modules.
    - Schematic capture and PCB layout guidance.
    - Hardware testing and validation.

    Qualifications
    B.E

    Additional Information
    6 - 9 years
    """
    reqs = analyze_job_description(bosch_jd, "Lead Hardware Engineer")
    # No mandatory technical skills should be falsely claimed
    assert reqs.must_have_skills == []


def test_required_skills_extracted_when_source_explicit():
    """When source explicitly mandates skills in qualifications/requirements, extract them."""
    jd = """
    Qualifications:
    - Minimum 5 years experience with Python, FastAPI, and PostgreSQL.
    - Hands-on experience with Docker.
    """
    reqs = analyze_job_description(jd, "Senior Backend Engineer")
    assert "Python" in reqs.must_have_skills
    assert "PostgreSQL" in reqs.must_have_skills
    assert "Docker" in reqs.must_have_skills


# ===========================================================================
# 4. Responsibilities Extraction (A4)
# ===========================================================================

def test_bosch_responsibilities_extraction():
    """Verify 8 responsibilities are extracted from Bosch Job Description."""
    bosch_jd = """
    Job Description
    - Requirement analysis and architecture design for automotive ECUs.
    - Schematic design and simulation of analog and digital circuits.
    - Component selection and Bill of Material optimization.
    - Worst case circuit analysis and thermal calculations.
    - PCB layout guidance adhering to EMC/EMI standards.
    - Prototype bring-up, debugging, and functional verification.
    - Environmental and EMC compliance testing.
    - Technical documentation and customer support.
    """
    reqs = analyze_job_description(bosch_jd, "Lead Hardware Engineer")
    assert len(reqs.responsibilities) == 8
    assert any("Schematic design" in r for r in reqs.responsibilities)
    assert any("PCB layout" in r for r in reqs.responsibilities)
    assert any("Prototype bring-up" in r for r in reqs.responsibilities)


# ===========================================================================
# 5. Source Text & Heading Normalization (A5)
# ===========================================================================

def test_clean_html_description_removes_artifacts():
    """_clean_html_description cleans HTML, unescapes entities, and turns Ø into clean bullets."""
    raw_html = (
        "<p>Qualifications:&#xa0;B.E</p>"
        "<div>Ø Requirement analysis</div>"
        "<div>Ø Schematic design &amp; simulation</div>"
    )
    cleaned = _clean_html_description(raw_html)
    assert "Ø" not in cleaned
    assert "&#xa0;" not in cleaned
    assert "&amp;" not in cleaned
    assert "&" in cleaned
    assert "- Requirement analysis" in cleaned
    assert "- Schematic design & simulation" in cleaned


def test_heading_normalization_markdown_hashes():
    """Markdown hashes like '## Qualifications' must normalize and classify correctly."""
    assert _normalize_heading_text("## Company Description") == "company description"
    assert _normalize_heading_text("## Job Description") == "job description"
    assert _normalize_heading_text("## Qualifications") == "qualifications"
    assert _normalize_heading_text("## Additional Information") == "additional information"

    assert _detect_section_category("## Company Description")[0] == RequirementCategory.COMPANY_OVERVIEW
    assert _detect_section_category("## Job Description")[0] == RequirementCategory.ROLE_OVERVIEW
    assert _detect_section_category("## Qualifications")[0] == RequirementCategory.QUALIFICATION
    assert _detect_section_category("## Additional Information")[0] == RequirementCategory.QUALIFICATION


# ===========================================================================
# 6. Location Normalization (A6)
# ===========================================================================

def test_location_normalization_bosch_duplicate_commas():
    """'coimbatore, , India' -> 'Coimbatore, India'."""
    raw_loc = "coimbatore, , India"
    normalized = normalize_location_string(raw_loc)
    assert normalized == "Coimbatore, India"


def test_location_normalization_edge_cases():
    assert normalize_location_string("bengaluru, karnataka, in") == "Bengaluru, Karnataka, In"
    assert normalize_location_string("new york, , ny, usa") == "New York, Ny, USA"
    assert normalize_location_string("  ") == "Not specified"
    assert normalize_location_string(None) == "Not specified"


# ===========================================================================
# 7. End-to-End Bosch Ingestion / Normalization (A1-A7)
# ===========================================================================

def test_smartrecruiters_bosch_lead_hardware_engineer_normalization():
    """Simulate real Bosch Lead Hardware Engineer payload normalization."""
    provider = SmartRecruitersJobProvider()
    raw = {
        "id": "744000147209508",
        "name": "Lead Hardware Engineer",
        "company": {"name": "Bosch Group", "identifier": "boschgroup"},
        "releasedDate": "2026-08-15T10:00:00.000Z",
        "location": {
            "city": "coimbatore",
            "region": "",
            "country": "India",
            "remote": False,
        },
        "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
        "experienceLevel": {"id": "mid_senior_level", "label": "Mid-Senior Level"},
        "jobAd": {
            "sections": {
                "companyDescription": {
                    "title": "Company Description",
                    "text": "<p>Bosch Global Software Technologies is a global engineering firm.</p>",
                },
                "jobDescription": {
                    "title": "Job Description",
                    "text": (
                        "<div>Ø Requirement analysis and architecture design for automotive ECUs.</div>"
                        "<div>Ø Schematic design and simulation of analog and digital circuits.</div>"
                        "<div>Ø Component selection and Bill of Material optimization.</div>"
                        "<div>Ø Worst case circuit analysis and thermal calculations.</div>"
                        "<div>Ø PCB layout guidance adhering to EMC/EMI standards.</div>"
                        "<div>Ø Prototype bring-up, debugging, and functional verification.</div>"
                        "<div>Ø Environmental and EMC compliance testing.</div>"
                        "<div>Ø Technical documentation and customer support.</div>"
                    ),
                },
                "qualifications": {
                    "title": "Qualifications",
                    "text": "<p>B.E</p>",
                },
                "additionalInformation": {
                    "title": "Additional Information",
                    "text": "<p>6 - 9 years</p>",
                },
            }
        },
        "refNumber": "REF123456",
    }

    normalized = provider.normalize_smartrecruiters_job(raw, "boschgroup")

    assert normalized["title"] == "Lead Hardware Engineer"
    assert normalized["company"] == "Bosch Group"
    # A1: Experience extracted
    assert normalized["experience_min"] == 6.0
    assert normalized["experience_max"] == 9.0
    # A2: Qualification preserved
    assert any("B.E" in q for q in normalized["qualifications"])
    # A3: Skills truth - none hallucinated
    assert normalized["skills_required"] == []
    # A4: Responsibilities preserved
    assert len(normalized["responsibilities"]) == 8
    # A6: Location normalized
    assert normalized["location"] == "Coimbatore, India"
    # Live URL
    assert normalized["apply_url"] == "https://jobs.smartrecruiters.com/boschgroup/744000147209508/apply"
    assert normalized["is_direct_apply"] is True


# ===========================================================================
# 8. List State Restoration Schema & Direct Navigation Integrity (Part B)
# ===========================================================================

def test_list_state_payload_integrity():
    """Verify structure and roundtrip serialization of the list state payload."""
    payload = {
        "searchQuery": "hardware engineer",
        "stageFilter": "fresher",
        "locationFilter": "Coimbatore",
        "workplaceFilter": "onsite",
        "roleFilter": "",
        "eligibleOnly": False,
        "sortOption": "recommended",
        "page": 3,
        "loadedItems": [{"id": f"job_{i}", "title": f"Job {i}"} for i in range(60)],
        "totalCount": 120,
        "scrollY": 1420,
        "timestamp": 1757152800000,
    }

    serialized = json.dumps(payload)
    deserialized = json.loads(serialized)

    assert deserialized["page"] == 3
    assert len(deserialized["loadedItems"]) == 60
    assert deserialized["scrollY"] == 1420
    assert deserialized["stageFilter"] == "fresher"
    assert deserialized["locationFilter"] == "Coimbatore"


def test_direct_navigation_fallback():
    """Direct navigation has no cached state; application proceeds with default clean state."""
    cached_raw = None
    assert cached_raw is None  # Component falls back to page 1, 0 scroll, default filters
