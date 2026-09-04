"""
Deterministic Eligibility and Realistic Fit Evaluation Layer.
Evaluates candidate eligibility based on hard constraints (experience, education, location, opportunity type)
strictly separated from semantic matching scores.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field

from app.modules.jobs.location_normalization import (
    is_location_match,
    normalize_india_location,
)
from app.modules.jobs.classification import (
    OpportunityType,
    CandidateSuitabilitySignal,
    classify_opportunity,
    SENIOR_TITLE_PATTERN,
)


class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    LIKELY_ELIGIBLE = "LIKELY_ELIGIBLE"
    EXPERIENCE_MISMATCH = "EXPERIENCE_MISMATCH"
    DEGREE_MISMATCH = "DEGREE_MISMATCH"
    GRADUATION_MISMATCH = "GRADUATION_MISMATCH"
    LOCATION_MISMATCH = "LOCATION_MISMATCH"
    OPPORTUNITY_NOT_SUFFICIENTLY_SPECIFIED = "OPPORTUNITY_NOT_SUFFICIENTLY_SPECIFIED"
    UNKNOWN = "UNKNOWN"


class RealisticFitSignal(str, Enum):
    GOOD_FIT = "GOOD_FIT"
    POSSIBLE_FIT = "POSSIBLE_FIT"
    SKILL_GAP = "SKILL_GAP"
    EXPERIENCE_GAP = "EXPERIENCE_GAP"
    UNKNOWN = "UNKNOWN"


class EligibilityResult(BaseModel):
    status: EligibilityStatus
    reasons: list[str] = Field(default_factory=list)
    checks: dict[str, str] = Field(default_factory=dict)
    realistic_fit: RealisticFitSignal = RealisticFitSignal.UNKNOWN
    fit_explanation: str = ""
    candidate_experience_years: float | None = None
    required_experience_min: int | None = None
    required_experience_max: int | None = None


# Degree equivalence groupings
DEGREE_EQUIVALENCE_GROUPS = [
    {
        "b.tech", "b.e.", "bachelor of technology", "bachelor of engineering",
        "b tech", "b e", "bachelor in technology", "bachelor in engineering", "b.tech in cse", "b.e cse"
    },
    {
        "m.tech", "master of technology", "m tech", "master in technology", "m.e.", "m.s.", "master of science"
    },
    {
        "mca", "master of computer applications", "master in computer applications"
    },
    {
        "bca", "bachelor of computer applications", "bachelor in computer applications"
    },
    {
        "b.sc", "bachelor of science", "b sc"
    },
    {
        "mba", "master of business administration"
    },
]


def _normalize_degree_token(d: str) -> str:
    cleaned = d.lower().strip()
    cleaned = re.sub(r"[^\w\s.]", "", cleaned)
    return cleaned


def are_degrees_equivalent(cand_degree: str, required_degree: str) -> bool:
    """
    Checks if a candidate degree satisfies a required degree using equivalence clusters.
    """
    c_norm = _normalize_degree_token(cand_degree)
    r_norm = _normalize_degree_token(required_degree)

    if c_norm == r_norm or r_norm in c_norm or c_norm in r_norm:
        return True

    for group in DEGREE_EQUIVALENCE_GROUPS:
        cand_matches = any(g in c_norm for g in group)
        req_matches = any(g in r_norm for g in group)
        if cand_matches and req_matches:
            return True

    return False


def evaluate_eligibility(
    candidate_profile: dict[str, Any] | None,
    master_resume: dict[str, Any] | None,
    job: dict[str, Any],
    skill_score: int | None = None,
) -> EligibilityResult:
    """
    Deterministically computes candidate eligibility for a canonical opportunity.
    Does not invent eligibility or fabricate scores.
    """
    checks: dict[str, str] = {
        "experience": "UNKNOWN",
        "education": "UNKNOWN",
        "location": "UNKNOWN",
        "opportunity_type": "UNKNOWN",
    }
    reasons: list[str] = []

    # Derive candidate parameters
    cand_category = "UNKNOWN"
    cand_exp_years: float | None = None
    cand_degrees: list[str] = []
    cand_preferred_locs: list[str] = []

    if candidate_profile:
        cand_category = candidate_profile.get("category", "UNKNOWN").upper()
        if candidate_profile.get("experience_years") is not None:
            cand_exp_years = float(candidate_profile.get("experience_years"))
        cand_preferred_locs = candidate_profile.get("preferred_locations", []) or []

    if master_resume and "parsed" in master_resume:
        parsed = master_resume["parsed"]
        # Extract degrees from education entities
        for edu in parsed.get("education", []):
            if isinstance(edu, dict):
                deg = edu.get("degree")
                if deg:
                    cand_degrees.append(deg)
            elif hasattr(edu, "degree") and edu.degree:
                cand_degrees.append(edu.degree)

        # If candidate experience_years was not explicit, estimate from structured experience
        if cand_exp_years is None and parsed.get("experience"):
            cand_exp_years = float(len(parsed["experience"]))
        elif cand_exp_years is None and cand_category in ("STUDENT", "FRESHER", "INTERNSHIP_SEEKER"):
            cand_exp_years = 0.0

    # Determine candidate seniority indicators
    is_student_cand = (
        cand_category in ("STUDENT", "INTERNSHIP_SEEKER")
        or (candidate_profile and bool(candidate_profile.get("is_student")))
        or (cand_exp_years is not None and cand_exp_years == 0.0 and cand_category != "EXPERIENCED")
    )
    is_fresher_cand = (
        is_student_cand
        or cand_category == "FRESHER"
        or (cand_exp_years is not None and cand_exp_years <= 1.0 and cand_category != "EXPERIENCED")
    )
    is_early_career_cand = (
        not is_student_cand
        and (cand_exp_years is not None and cand_exp_years < 4.0 and cand_category != "EXPERIENCED")
    )

    # Job parameters
    title = job.get("title", "")
    description = job.get("description", "")
    exp_min = job.get("experience_min")
    exp_max = job.get("experience_max")
    job_type = job.get("job_type", "full_time")
    job_loc = job.get("location")
    is_remote = job.get("is_remote", False)

    classification = classify_opportunity(title, description, exp_min, exp_max, job_type)

    title_lower = title.lower().strip()
    is_senior_role = (
        classification.suitability == CandidateSuitabilitySignal.EXPERIENCED
        or bool(SENIOR_TITLE_PATTERN.search(title_lower))
    )

    # -------------------------------------------------------------
    # 1. Experience Check (P0-02 Safety Rules)
    # -------------------------------------------------------------
    if exp_min is not None and exp_min > 0:
        if cand_exp_years is not None:
            if cand_exp_years < (exp_min - 0.5):
                checks["experience"] = "FAIL"
                reasons.append(f"Requires {exp_min}+ years experience (You have ~{int(cand_exp_years)} year{'s' if cand_exp_years != 1 else ''})")
            else:
                checks["experience"] = "PASS"
                reasons.append("Experience requirement satisfied")
        else:
            checks["experience"] = "UNKNOWN"
    elif exp_min is not None and exp_min == 0:
        checks["experience"] = "PASS"
        reasons.append("Fresher / entry-level compatible")
    elif is_senior_role:
        # P0-02 Invariant: A candidate being a student, intern seeker, or fresher must NEVER bypass seniority mismatch!
        if is_student_cand:
            checks["experience"] = "FAIL"
            reasons.append("Opportunity indicates senior/experienced scope (incompatible with student/intern profile)")
        elif is_fresher_cand:
            checks["experience"] = "FAIL"
            reasons.append("Opportunity indicates senior/experienced scope (incompatible with fresher profile)")
        elif is_early_career_cand:
            checks["experience"] = "FAIL"
            reasons.append(f"Opportunity indicates senior/experienced scope (typically requires 4–5+ years; you have ~{round(cand_exp_years or 0, 1)} years)")
        else:
            checks["experience"] = "PASS" if (cand_exp_years is not None and cand_exp_years >= 4.0) else "UNKNOWN"
            if checks["experience"] == "PASS":
                reasons.append("Experience aligns with senior scope")
            else:
                reasons.append("Senior opportunity with undisclosed numeric experience requirement")
    elif classification.opportunity_type == OpportunityType.INTERNSHIP:
        checks["experience"] = "PASS"
        reasons.append("Internship opportunity suited for students")
    elif classification.suitability in (CandidateSuitabilitySignal.FRESHER, CandidateSuitabilitySignal.STUDENT) or classification.fresher_eligible:
        checks["experience"] = "PASS"
        reasons.append("Opportunity is student / fresher compatible")
    else:
        # Generic role with unspecified experience
        checks["experience"] = "UNKNOWN"

    # -------------------------------------------------------------
    # 2. Education Check
    # -------------------------------------------------------------
    req_degrees = classification.degree_requirements
    if req_degrees:
        if cand_degrees:
            matched_deg = False
            for req in req_degrees:
                for cand_d in cand_degrees:
                    if are_degrees_equivalent(cand_d, req):
                        matched_deg = True
                        break
                if matched_deg:
                    break

            if matched_deg:
                checks["education"] = "PASS"
                reasons.append(f"Degree qualifications match ({', '.join(req_degrees)})")
            else:
                checks["education"] = "FAIL"
                reasons.append(f"Opportunity specifies {', '.join(req_degrees)} qualification")
        else:
            checks["education"] = "UNKNOWN"
    else:
        checks["education"] = "UNKNOWN"

    # -------------------------------------------------------------
    # 3. Location Check
    # -------------------------------------------------------------
    loc_match = is_location_match(cand_preferred_locs, job_loc, is_remote)
    if loc_match is True:
        checks["location"] = "PASS"
        if is_remote:
            reasons.append("Remote friendly")
        else:
            reasons.append(f"Location aligns with preferences ({job_loc})")
    elif loc_match is False:
        checks["location"] = "FAIL"
        reasons.append(f"Location ({job_loc}) differs from preferred locations")
    else:
        checks["location"] = "UNKNOWN"

    # -------------------------------------------------------------
    # 4. Opportunity Type / Category Check
    # -------------------------------------------------------------
    if classification.opportunity_type == OpportunityType.INTERNSHIP:
        if is_student_cand or cand_category in ("STUDENT", "INTERNSHIP_SEEKER", "FRESHER", "UNKNOWN"):
            checks["opportunity_type"] = "PASS"
            reasons.append("Internship opportunity suited for students")
        else:
            checks["opportunity_type"] = "PASS"
    elif classification.opportunity_type == OpportunityType.GRADUATE_PROGRAM:
        if is_student_cand or cand_category in ("STUDENT", "FRESHER"):
            checks["opportunity_type"] = "PASS"
            reasons.append("Graduate program tailored for campus/new grads")
        else:
            checks["opportunity_type"] = "PASS"
    elif classification.opportunity_type == OpportunityType.FULL_TIME and is_senior_role and is_student_cand:
        checks["opportunity_type"] = "FAIL"
        reasons.append("Full-time experienced role incompatible with student internship search")
    else:
        checks["opportunity_type"] = "PASS"

    # -------------------------------------------------------------
    # 5. Overall Eligibility Synthesis
    # -------------------------------------------------------------
    has_exp_fail = checks["experience"] == "FAIL"
    has_edu_fail = checks["education"] == "FAIL"
    has_loc_fail = checks["location"] == "FAIL"

    if has_exp_fail:
        overall_status = EligibilityStatus.EXPERIENCE_MISMATCH
    elif has_edu_fail:
        overall_status = EligibilityStatus.DEGREE_MISMATCH
    elif has_loc_fail and not is_remote:
        overall_status = EligibilityStatus.LOCATION_MISMATCH
    elif all(v == "PASS" for v in checks.values() if v != "UNKNOWN") and any(v == "PASS" for v in checks.values()):
        if any(v == "UNKNOWN" for v in checks.values()):
            overall_status = EligibilityStatus.LIKELY_ELIGIBLE
        else:
            overall_status = EligibilityStatus.ELIGIBLE
    elif all(v == "UNKNOWN" for v in checks.values()):
        overall_status = EligibilityStatus.OPPORTUNITY_NOT_SUFFICIENTLY_SPECIFIED
    else:
        overall_status = EligibilityStatus.UNKNOWN

    # -------------------------------------------------------------
    # 6. Realistic Fit Synthesis
    # -------------------------------------------------------------
    if overall_status == EligibilityStatus.EXPERIENCE_MISMATCH:
        fit = RealisticFitSignal.EXPERIENCE_GAP
        explanation = "The role requires more experience than your verified profile reflects."
    elif overall_status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE):
        if skill_score is not None:
            if skill_score >= 50:
                fit = RealisticFitSignal.GOOD_FIT
                explanation = "Your experience and core skill requirements align well."
            else:
                fit = RealisticFitSignal.SKILL_GAP
                explanation = "You meet the experience criteria but have key skill gaps for this requisition."
        else:
            fit = RealisticFitSignal.GOOD_FIT
            explanation = "Your profile aligns with the foundational eligibility requirements."
    elif overall_status == EligibilityStatus.DEGREE_MISMATCH:
        fit = RealisticFitSignal.POSSIBLE_FIT
        explanation = "Specific degree requirements may limit direct eligibility."
    else:
        fit = RealisticFitSignal.UNKNOWN
        explanation = "Not enough information to determine realistic fit."

    return EligibilityResult(
        status=overall_status,
        reasons=reasons,
        checks=checks,
        realistic_fit=fit,
        fit_explanation=explanation,
        candidate_experience_years=cand_exp_years,
        required_experience_min=exp_min,
        required_experience_max=exp_max,
    )
