"""
Canonical Opportunity Completeness Model.
Determines whether an opportunity has sufficient, trustworthy employer-provided
information for recommendation and ranking.

Fundamental rule:
Employer provides information -> RoleRadar must preserve and display it.
Employer does not provide information -> RoleRadar must clearly indicate that it was not disclosed.
Never fabricate, estimate, or infer missing fields.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from app.modules.jobs.url_classifier import ApplicationUrlType
from app.modules.jobs.verification import OpportunityLifecycleStatus, OpportunityRejectionReason


class QualityTier(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    REJECTED = "REJECTED"


class OpportunityCompletenessStatus(str, Enum):
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    VERIFIED_PARTIAL = "VERIFIED_PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class RecommendationQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OpportunityCompleteness(BaseModel):
    source_completeness: OpportunityCompletenessStatus
    recommendation_quality: RecommendationQuality
    quality_tier: QualityTier = QualityTier.PRIMARY
    eligible_for_primary_recommendations: bool
    rejection_reason: str | None = None
    missing_required_information: list[str] = Field(default_factory=list)
    available_information: list[str] = Field(default_factory=list)
    is_salary_disclosed: bool = False
    is_stipend_disclosed: bool = False
    is_experience_disclosed: bool = False
    is_skills_disclosed: bool = False
    is_qualifications_disclosed: bool = False
    is_responsibilities_disclosed: bool = False


def evaluate_opportunity_completeness(opportunity: dict[str, Any], require_india: bool = False) -> OpportunityCompleteness:
    """
    Deterministically evaluates completeness of an opportunity.
    
    Fundamental Requirements for Primary Recommendations:
    - valid title
    - identifiable company
    - valid location
    - valid opportunity type (FULL_TIME or INTERNSHIP)
    - usable employer description (>= 50 chars)
    - valid active/verification status (VERIFIED_ACTIVE)
    - valid direct application URL (DIRECT_REQUISITION and non-empty apply_url)
    
    Note: Missing optional employer fields (salary, stipend, experience, skills,
    qualifications) are employer disclosure states, NOT data-quality failures.
    An opportunity is NEVER rejected or marked INSUFFICIENT simply because
    compensation or experience is undisclosed.
    """
    missing_required: list[str] = []
    available: list[str] = []

    # 1. Fundamental Mandatory Checks
    title = (opportunity.get("title") or "").strip()
    if title:
        available.append("title")
    else:
        missing_required.append("title")

    company = (opportunity.get("company") or "").strip()
    if company and company.lower() not in ("unknown", "not specified", "n/a"):
        available.append("company")
    else:
        missing_required.append("company")

    location = (opportunity.get("location") or "").strip()
    if location and location.lower() not in ("unknown", "not specified"):
        available.append("location")
    else:
        missing_required.append("location")

    opp_type = str(opportunity.get("opportunity_type") or opportunity.get("job_type") or "FULL_TIME").upper()
    if opp_type in ("FULL_TIME", "INTERNSHIP", "PART_TIME", "CONTRACT"):
        available.append("opportunity_type")
    else:
        missing_required.append("opportunity_type")

    # Geography validation
    if require_india:
        country = (opportunity.get("country") or "").strip()
        from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
        is_india = (country.lower() in ("india", "in")) or is_india_opportunity(location) or (extract_country_from_location(location) == "India") if (country or location) else True
        if not is_india:
            missing_required.append("geography")

    ver_status = opportunity.get("verification_status", OpportunityLifecycleStatus.VERIFIED_ACTIVE.value)
    if ver_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value:
        available.append("verification_status")
    else:
        missing_required.append("verification_status")

    desc = (opportunity.get("description") or opportunity.get("jd_text") or "").strip()
    if len(desc) >= 50:
        available.append("description")
    else:
        missing_required.append("description")

    apply_url = (opportunity.get("apply_url") or opportunity.get("direct_apply_url") or "").strip()
    is_valid_url = bool(apply_url and (apply_url.startswith("http://") or apply_url.startswith("https://")))
    if is_valid_url:
        available.append("apply_url")
    else:
        missing_required.append("apply_url")

    # 2. Employer-Provided Optional Field Checks
    # Salary
    has_num_salary = (opportunity.get("salary_min") is not None or opportunity.get("salary_max") is not None)
    has_comp_text = bool((opportunity.get("compensation_text") or "").strip())
    is_sal_disclosed = bool(opportunity.get("salary_disclosed") or has_num_salary or has_comp_text)
    if is_sal_disclosed:
        available.append("salary")

    # Stipend
    has_stipend = (
        opportunity.get("stipend_min") is not None
        or opportunity.get("stipend_max") is not None
        or opportunity.get("stipend") is not None
    )
    if has_stipend:
        available.append("stipend")

    # Experience
    has_exp = (opportunity.get("experience_min") is not None or opportunity.get("experience_max") is not None)
    if has_exp:
        available.append("experience")

    # Skills
    skills = opportunity.get("skills_required") or []
    req_skills = [s for s in skills if isinstance(s, str) and s.strip()]
    if req_skills:
        available.append("skills_required")

    # Preferred Skills
    pref_skills = opportunity.get("skills_nice_to_have") or []
    if pref_skills and len(pref_skills) > 0:
        available.append("skills_nice_to_have")

    # Responsibilities
    resps = opportunity.get("responsibilities") or []
    has_resps = isinstance(resps, list) and len(resps) > 0
    if has_resps:
        available.append("responsibilities")

    # Qualifications
    quals = opportunity.get("qualifications") or []
    has_quals = isinstance(quals, list) and len(quals) > 0
    if has_quals:
        available.append("qualifications")

    # Duration (for internships)
    duration = opportunity.get("internship_duration_months")
    if duration is not None:
        available.append("internship_duration_months")

    # Workplace Type
    wp = opportunity.get("workplace_type")
    if wp and str(wp).lower() not in ("unknown", "none"):
        available.append("workplace_type")

    # 3. Determine Overall Completeness Status & Quality Tier
    rejection_reason = None
    if missing_required:
        status = OpportunityCompletenessStatus.INSUFFICIENT
        quality = RecommendationQuality.LOW
        quality_tier = QualityTier.REJECTED
        eligible = False
        if "geography" in missing_required:
            rejection_reason = OpportunityRejectionReason.NON_INDIA_GEOGRAPHY.value
        elif ver_status in ("CLOSED", OpportunityLifecycleStatus.CLOSED.value, "EXPIRED"):
            rejection_reason = OpportunityRejectionReason.CLOSED_REQUISITION.value
        elif "description" in missing_required:
            rejection_reason = OpportunityRejectionReason.INSUFFICIENT_DESCRIPTION.value
        elif "apply_url" in missing_required:
            rejection_reason = OpportunityRejectionReason.INVALID_OR_MISSING_APPLY_URL.value
        elif ver_status in ("MARKET_BENCHMARK", OpportunityLifecycleStatus.MARKET_BENCHMARK.value):
            rejection_reason = OpportunityRejectionReason.MARKET_BENCHMARK_NOT_LIVE.value
        elif "verification_status" in missing_required:
            rejection_reason = OpportunityRejectionReason.CLOSED_REQUISITION.value
        else:
            rejection_reason = OpportunityRejectionReason.OTHER_INVALID.value
    elif (has_resps or has_quals or req_skills) and (len(desc) >= 150 or (has_resps and has_quals)):
        # High confidence, rich employer documentation
        status = OpportunityCompletenessStatus.VERIFIED_COMPLETE
        quality = RecommendationQuality.HIGH
        quality_tier = QualityTier.PRIMARY
        eligible = True
    else:
        # Good legitimate opportunity: active, actionable direct apply, but brief description or unstructured sections
        status = OpportunityCompletenessStatus.VERIFIED_COMPLETE
        quality = RecommendationQuality.MEDIUM
        quality_tier = QualityTier.SECONDARY
        eligible = True

    return OpportunityCompleteness(
        source_completeness=status,
        recommendation_quality=quality,
        quality_tier=quality_tier,
        eligible_for_primary_recommendations=eligible,
        rejection_reason=rejection_reason,
        missing_required_information=missing_required,
        available_information=available,
        is_salary_disclosed=is_sal_disclosed,
        is_stipend_disclosed=has_stipend,
        is_experience_disclosed=has_exp,
        is_skills_disclosed=bool(req_skills),
        is_qualifications_disclosed=has_quals,
        is_responsibilities_disclosed=has_resps,
    )
