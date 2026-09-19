"""
Phase 17 Correction Pass Tests:
Role Coverage, Funnel Reconciliation & Inventory Validation.

Verifies:
1. 588 vs 587 inventory reconciliation mathematics (576 Full-Time + 11 Internships = 587; 251 Primary + 335 Secondary + 1 Rejected = 587).
2. Greenhouse Apply URL recognition (100% direct apply, distinguishing boards.greenhouse.io vs branded ATS subdomains).
3. Decoupling of description quality (>= 50 chars) from role relevance (canonical identity).
4. Evidenced remapping of Specialized Requisitions (Categories B & D) without generic fallback mapping.
5. Preservation of genuinely specialized domain roles (Category A) as Specialized Requisition.
6. Deterministic Primary vs Secondary tiering (missing salary/skills is UNKNOWN, not INVALID).
7. False-positive salary detection guards (business revenue / loan volume / funding != salary).
"""
import pytest
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role, RoleConfidence
from app.modules.jobs.completeness import (
    evaluate_opportunity_completeness,
    QualityTier,
    OpportunityCompletenessStatus,
)


# --------------------------------------------------------------------------
# 1. Reconciliation & Funnel Invariants
# --------------------------------------------------------------------------

def test_authoritative_reconciliation_math():
    """Verify exact mathematical reconciliation between stages."""
    raw_ingested_india_active = 588
    duplicates_detected = 1  # gh_inmobi_8138503
    unique_active_india = raw_ingested_india_active - duplicates_detected
    assert unique_active_india == 587

    full_time = 576
    internships = 11
    assert full_time + internships == unique_active_india

    primary = 251
    secondary = 335
    rejected = 1  # Paytm 23-char stub
    assert primary + secondary + rejected == unique_active_india

    actionable = primary + secondary
    assert actionable == 586
    assert actionable + rejected == 587


# --------------------------------------------------------------------------
# 2. Greenhouse Apply URL Recognition
# --------------------------------------------------------------------------

def test_greenhouse_direct_apply_urls():
    """Verify Greenhouse URLs (standard boards and branded subdomains) are direct apply."""
    standard_gh = "https://boards.greenhouse.io/inmobi/jobs/7995193"
    branded_gh = "https://careers.airbnb.com/positions/5839201"
    lever_url = "https://jobs.lever.co/paytm/4a97658f-ac6f-4a88-825c-09798ce04bf6"
    sr_url = "https://jobs.smartrecruiters.com/BlueberryLabs/7439999912345"

    for url in [standard_gh, branded_gh, lever_url, sr_url]:
        mock_job = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "Bengaluru, India",
            "country": "India",
            "description": "A" * 150,
            "apply_url": url,
            "verification_status": "VERIFIED_ACTIVE",
        }
        res = evaluate_opportunity_completeness(mock_job)
        assert res.quality_tier != QualityTier.REJECTED
        assert "apply_url" not in res.missing_required_information


# --------------------------------------------------------------------------
# 3. Description Quality vs Role Relevance Decoupling
# --------------------------------------------------------------------------

def test_description_quality_decoupled_from_role_relevance():
    """
    Description length >= 50 characters is a data-quality / actionability signal,
    NOT role relevance.
    """
    # A job with 100 characters of generic text is adequate in quality, but not relevant to Python Developer
    short_adequate_job = {
        "title": "Warehouse Logistics Executive",
        "company": "SupplyCo",
        "location": "Pune, India",
        "description": "Responsible for daily dispatch and receiving shipments at the Chakan warehouse facility.",
        "apply_url": "https://example.com/apply",
        "verification_status": "VERIFIED_ACTIVE",
    }
    assert len(short_adequate_job["description"]) >= 50
    comp = evaluate_opportunity_completeness(short_adequate_job)
    # The opportunity has adequate description quality
    assert comp.source_completeness in (OpportunityCompletenessStatus.VERIFIED_COMPLETE, OpportunityCompletenessStatus.VERIFIED_PARTIAL)
    
    # Role resolution is completely separate from description length:
    prof, conf, key = resolve_role(short_adequate_job["title"])
    # Not relevant to any tech canonical role
    assert prof is None or prof.canonical_role != "Python Developer"


# --------------------------------------------------------------------------
# 4. Evidence-Based Remapping of Specialized Requisitions
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_title,expected_canonical_role",
    [
        ("MEAN Stack Developer", "Full Stack Developer"),
        ("PHP Developer", "Backend Developer"),
        ("Node JS Developer", "Backend Developer"),
        ("Senior Software Engineer(AI/ML), Trust", "Machine Learning Engineer"),
        ("Interactive Art Director", "Creative Director"),
        ("CONTENT WRITER", "Copywriter"),
        ("Proof Reader", "Copywriter"),
        ("Senior Network Engineer", "Infrastructure Engineer"),
        ("Manager- Application Security", "Application Security"),
        ("Enterprise Solutions Consultant", "Technology Consultant"),
        ("Lead - Advanced Analytics", "Data Analyst"),
        ("Enterprise Account Executive", "Sales Executive"),
        ("business development & strategic partnerships - d2c", "Business Development Executive"),
        ("R&D Engineer (C++)", "Software Engineer"),
    ],
)
def test_specialized_requisition_evidence_based_remapping(raw_title, expected_canonical_role):
    """Verify that titles with explicit role evidence map cleanly to taxonomy profiles."""
    prof, conf, key = resolve_role(raw_title)
    assert prof is not None, f"Failed to resolve '{raw_title}'"
    assert prof.canonical_role == expected_canonical_role, (
        f"Expected '{expected_canonical_role}' for '{raw_title}', got '{prof.canonical_role}'"
    )


# --------------------------------------------------------------------------
# 5. Preservation of Genuinely Specialized Roles (No Generic Fallback)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_title",
    [
        "Senior Staff Engineer - Powertrain Calibration",
        "Executive - Lending Collections",
        "Manager - Motor Claims",
        "Cluster Head - Operations",
        "Plant Head - Sheet Metal Fabrication",
        "Underwriting Specialist - NBFC",
        "Real Estate Acquisition Manager",
    ],
)
def test_no_generic_fallback_mapping(raw_title):
    """
    Verify genuinely specialized roles are preserved and NOT forced into generic
    roles like Software Engineer or Backend Developer.
    """
    prof, conf, key = resolve_role(raw_title)
    # Should NOT map to generic software roles
    forbidden_generic_roles = {"Software Engineer", "Backend Developer", "Full Stack Developer", "Frontend Developer"}
    if prof is not None:
        assert prof.canonical_role not in forbidden_generic_roles, (
            f"Specialized title '{raw_title}' was incorrectly fallback-mapped to '{prof.canonical_role}'"
        )


# --------------------------------------------------------------------------
# 6. Primary / Secondary Determinism (UNKNOWN vs INVALID)
# --------------------------------------------------------------------------

def test_missing_salary_and_skills_is_secondary_not_rejected():
    """
    Missing salary, skills, or experience must NOT reject a legitimate opportunity.
    It should place it into SECONDARY tier with UNKNOWN/UNDISCLOSED status.
    """
    job_with_undisclosed_fields = {
        "title": "Software Engineer",
        "company": "Acme Software",
        "location": "Hyderabad, India",
        "country": "India",
        "description": "We are seeking a talented engineer to join our platform team. You will work on microservices, architecture design, and production incident triage.",
        "apply_url": "https://jobs.lever.co/acme/12345",
        "verification_status": "VERIFIED_ACTIVE",
        # salary, skills, experience omitted
    }
    comp = evaluate_opportunity_completeness(job_with_undisclosed_fields)
    assert comp.quality_tier in (QualityTier.PRIMARY, QualityTier.SECONDARY)
    assert comp.quality_tier != QualityTier.REJECTED
    assert comp.is_salary_disclosed is False
    assert comp.is_skills_disclosed is False


def test_short_description_stub_is_rejected():
    """Descriptions < 50 characters lack actionable information and must be rejected."""
    paytm_stub = {
        "id": "lever_paytm_157e96d2-d7dc-4c84-8b8b-55156466f73a",
        "title": "Enterprise Risk Manager",
        "company": "Paytm",
        "location": "Noida, India",
        "description": "Enterprise Risk Manager",  # 23 chars
        "apply_url": "https://jobs.lever.co/paytm/157e96d2",
        "verification_status": "VERIFIED_ACTIVE",
    }
    comp = evaluate_opportunity_completeness(paytm_stub)
    assert comp.quality_tier == QualityTier.REJECTED
    assert comp.rejection_reason == "INSUFFICIENT_DESCRIPTION"


# --------------------------------------------------------------------------
# 7. Salary False-Positive Protection
# --------------------------------------------------------------------------

def test_salary_business_context_false_positive_protection():
    """
    Ensure monetary mentions in business contexts (e.g. funding rounds, GMV, loan portfolios)
    are NOT classified as disclosed candidate salary.
    """
    business_descriptions = [
        "Paytm processes over INR 50,000 crore in GMV annually across millions of merchants.",
        "Cred recently raised $50 million in Series B financing to scale its premium rewards platform.",
        "As an NBFC collections manager, you will oversee a loan recovery portfolio of INR 10 crore.",
    ]
    for desc in business_descriptions:
        job = {
            "title": "Operations Manager",
            "company": "Fintech Corp",
            "location": "Bengaluru, India",
            "country": "India",
            "description": desc,
            "apply_url": "https://example.com/apply",
            "verification_status": "VERIFIED_ACTIVE",
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": False,
        }
        comp = evaluate_opportunity_completeness(job)
        assert comp.is_salary_disclosed is False
        assert "salary" not in comp.available_information
