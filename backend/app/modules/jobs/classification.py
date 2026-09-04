"""
Opportunity and Candidate Suitability Classification Layer.
Classifies opportunities into OpportunityType (FULL_TIME, INTERNSHIP, GRADUATE_PROGRAM, APPRENTICESHIP, CONTRACT, OTHER)
and derives CandidateSuitabilitySignal (STUDENT, FRESHER, EARLY_CAREER, EXPERIENCED, UNKNOWN).
Uses structured metadata and semantic signals without hardcoding company or candidate names.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field


class OpportunityType(str, Enum):
    FULL_TIME = "FULL_TIME"
    INTERNSHIP = "INTERNSHIP"
    GRADUATE_PROGRAM = "GRADUATE_PROGRAM"
    APPRENTICESHIP = "APPRENTICESHIP"
    CONTRACT = "CONTRACT"
    OTHER = "OTHER"


class CandidateSuitabilitySignal(str, Enum):
    STUDENT = "STUDENT"
    FRESHER = "FRESHER"
    EARLY_CAREER = "EARLY_CAREER"
    EXPERIENCED = "EXPERIENCED"
    UNKNOWN = "UNKNOWN"


class OpportunityClassification(BaseModel):
    opportunity_type: OpportunityType
    suitability: CandidateSuitabilitySignal
    student_eligible: bool
    fresher_eligible: bool
    degree_requirements: list[str] = Field(default_factory=list)
    graduation_year_requirements: list[int] = Field(default_factory=list)
    experience_min: int | None = None
    experience_max: int | None = None


# Known degree recognition patterns
DEGREE_PATTERNS = [
    ("B.Tech", re.compile(r"\b(?:b\.?\s*tech|bachelor\s+of\s+technology)\b", re.IGNORECASE)),
    ("B.E.", re.compile(r"\b(?:b\.?\s*e\.?|bachelor\s+of\s+engineering)\b", re.IGNORECASE)),
    ("M.Tech", re.compile(r"\b(?:m\.?\s*tech|master\s+of\s+technology)\b", re.IGNORECASE)),
    ("MCA", re.compile(r"\b(?:m\.?\s*c\.?\s*a\.?|master\s+of\s+computer\s+applications?)\b", re.IGNORECASE)),
    ("BCA", re.compile(r"\b(?:b\.?\s*c\.?\s*a\.?|bachelor\s+of\s+computer\s+applications?)\b", re.IGNORECASE)),
    ("B.Sc", re.compile(r"\b(?:b\.?\s*sc\.?|bachelor\s+of\s+science)\b", re.IGNORECASE)),
    ("M.Sc", re.compile(r"\b(?:m\.?\s*sc\.?|master\s+of\s+science)\b", re.IGNORECASE)),
    ("MBA", re.compile(r"\b(?:m\.?\s*b\.?\s*a\.?|master\s+of\s+business\s+administration)\b", re.IGNORECASE)),
    ("B.Com", re.compile(r"\b(?:b\.?\s*com|bachelor\s+of\s+commerce)\b", re.IGNORECASE)),
    ("Ph.D", re.compile(r"\b(?:ph\.?\s*d\.?|doctorate)\b", re.IGNORECASE)),
]


def extract_degree_requirements(text: str) -> list[str]:
    """
    Extracts canonical degree identifiers from opportunity description or qualifications.
    """
    if not text:
        return []

    found = []
    for deg_name, pattern in DEGREE_PATTERNS:
        if pattern.search(text):
            found.append(deg_name)
    return found


def extract_graduation_years(text: str) -> list[int]:
    """
    Extracts explicit target graduation years (e.g. 2024, 2025, 2026, 2027 graduates).
    """
    if not text:
        return []

    years = set()
    matches = re.finditer(r"\b(?:batch\s+of\s+|graduating\s+in\s+|class\s+of\s+)?(202[3-9]|2030)\b", text, re.IGNORECASE)
    for m in matches:
        # Avoid matching years that are clearly company founding dates or copyright
        full_line = text[max(0, m.start() - 30):min(len(text), m.end() + 30)].lower()
        if any(w in full_line for w in ["copyright", "founded", "established", "since", "all rights reserved"]):
            continue
        years.add(int(m.group(1)))
    return sorted(list(years))


def classify_opportunity_type(
    title: str,
    description: str = "",
    job_type_hint: str = "",
) -> OpportunityType:
    """
    Classifies opportunity type based on semantic signals across title and description.
    """
    title_lower = (title or "").lower().strip()
    desc_lower = (description or "").lower()

    # 1. Apprenticeship
    if re.search(r"\b(?:apprentice|apprenticeship)\b", title_lower):
        return OpportunityType.APPRENTICESHIP

    # 2. Graduate Trainee / Campus Hire Programs
    if re.search(r"\b(?:graduate\s+engineer\s+trainee|management\s+trainee|graduate\s+trainee|\bget\b|\bmt\b|campus\s+hire|campus\s+recruitment|new\s+grad|fresh\s+graduate)\b", title_lower):
        return OpportunityType.GRADUATE_PROGRAM

    # 3. Internship
    if job_type_hint.lower() == "internship" or re.search(r"\b(?:intern|internship|trainee|co-op|summer\s+analyst|student\s+worker)\b", title_lower):
        return OpportunityType.INTERNSHIP

    # 4. Contract / Freelance
    if re.search(r"\b(?:contract|contractor|freelance|consultant|fixed\s+term)\b", title_lower):
        return OpportunityType.CONTRACT

    # Check description for strong internship or graduate program markers if title was generic
    if re.search(r"\b(?:this\s+internship|summer\s+internship|6\s+months?\s+internship)\b", desc_lower[:500]):
        return OpportunityType.INTERNSHIP

    if re.search(r"\b(?:graduate\s+program|campus\s+hiring\s+program)\b", desc_lower[:500]):
        return OpportunityType.GRADUATE_PROGRAM

    return OpportunityType.FULL_TIME


SENIOR_TITLE_PATTERN = re.compile(
    r"\b(?:"
    r"senior|sr\.?|lead|principal|staff|architect|director|vp|vice\s+president|"
    r"head\s+of|expert|manager|supervisor|chief|fellow|"
    r"(?:sde|swe|software\s+engineer|developer|engineer|analyst|consultant|specialist|designer|qa|data\s+scientist)\s*(?:[-_/]\s*)?(?:iii|iv|v|3|4|5)|"
    r"(?:iii|iv|v)\b"
    r")\b",
    re.IGNORECASE,
)

MID_LEVEL_TITLE_PATTERN = re.compile(
    r"\b(?:"
    r"(?:sde|swe|software\s+engineer|developer|engineer|analyst|consultant|specialist|qa|data\s+scientist)\s*(?:[-_/]\s*)?(?:ii|2)|"
    r"\bii\b|"
    r"mid|intermediate"
    r")\b",
    re.IGNORECASE,
)

FRESHER_TITLE_PATTERN = re.compile(
    r"\b(?:"
    r"fresher|freshers|entry\s+level|trainee|"
    r"graduate\s+engineer\s+trainee|management\s+trainee|\bget\b|\bmt\b|campus\s+hire|new\s+grad|fresh\s+graduate|"
    r"junior\s+(?:software\s+)?engineer|associate\s+(?:software\s+)?engineer|"
    r"junior\s+developer|associate\s+developer"
    r")\b",
    re.IGNORECASE,
)


def classify_candidate_suitability(
    title: str,
    description: str = "",
    experience_min: int | None = None,
    experience_max: int | None = None,
    opp_type: OpportunityType = OpportunityType.FULL_TIME,
) -> CandidateSuitabilitySignal:
    """
    Derives candidate suitability signal (STUDENT, FRESHER, EARLY_CAREER, EXPERIENCED, UNKNOWN).
    Applies conservative rules to avoid false positives on senior/mid engineering titles.
    """
    title_lower = (title or "").lower().strip()
    desc_lower = (description or "").lower()

    # 1. Student suitability
    if opp_type == OpportunityType.INTERNSHIP:
        return CandidateSuitabilitySignal.STUDENT

    # 2. Senior title indicators (Checked first to prevent 'Senior Associate' or 'Trainee Manager' from matching fresher)
    if SENIOR_TITLE_PATTERN.search(title_lower):
        return CandidateSuitabilitySignal.EXPERIENCED

    # 3. Explicit high experience boundaries
    if experience_min is not None and experience_min >= 4:
        return CandidateSuitabilitySignal.EXPERIENCED

    # 4. Mid-level / Level II engineering indicators
    if MID_LEVEL_TITLE_PATTERN.search(title_lower):
        return CandidateSuitabilitySignal.EARLY_CAREER

    if experience_min is not None and 1 < experience_min <= 3:
        return CandidateSuitabilitySignal.EARLY_CAREER

    # 5. Graduate program / apprenticeship programs
    if opp_type in (OpportunityType.GRADUATE_PROGRAM, OpportunityType.APPRENTICESHIP):
        return CandidateSuitabilitySignal.FRESHER

    # 6. Explicit fresher title indicators (when not senior or mid-level)
    if FRESHER_TITLE_PATTERN.search(title_lower):
        return CandidateSuitabilitySignal.FRESHER

    # 7. Explicit low experience boundaries (0 to 1 year)
    if experience_min is not None and experience_min <= 1:
        if experience_max is None or experience_max <= 2:
            return CandidateSuitabilitySignal.FRESHER if experience_min == 0 else CandidateSuitabilitySignal.EARLY_CAREER
        return CandidateSuitabilitySignal.EARLY_CAREER

    # 8. Description semantic signals
    if re.search(r"\b(?:no\s+prior\s+experience\s+required|0\s*-\s*1\s+years?|freshers\s+can\s+apply|fresh\s+graduates?\s+welcome)\b", desc_lower[:800]):
        return CandidateSuitabilitySignal.FRESHER

    if re.search(r"\b(?:5\+|\d+\+?\s+years?\s+of\s+experience|senior\s+level)\b", desc_lower[:800]):
        return CandidateSuitabilitySignal.EXPERIENCED

    return CandidateSuitabilitySignal.UNKNOWN


def classify_opportunity(
    title: str,
    description: str = "",
    experience_min: int | None = None,
    experience_max: int | None = None,
    job_type_hint: str = "",
) -> OpportunityClassification:
    """
    Performs comprehensive deterministic opportunity classification.
    """
    opp_type = classify_opportunity_type(title, description, job_type_hint)
    suitability = classify_candidate_suitability(title, description, experience_min, experience_max, opp_type)

    student_eligible = opp_type in (OpportunityType.INTERNSHIP, OpportunityType.APPRENTICESHIP) or suitability == CandidateSuitabilitySignal.STUDENT
    fresher_eligible = (
        suitability not in (CandidateSuitabilitySignal.EXPERIENCED, CandidateSuitabilitySignal.EARLY_CAREER)
        and (
            opp_type in (OpportunityType.GRADUATE_PROGRAM, OpportunityType.APPRENTICESHIP, OpportunityType.INTERNSHIP)
            or suitability in (CandidateSuitabilitySignal.FRESHER, CandidateSuitabilitySignal.STUDENT)
            or (experience_min is not None and experience_min <= 1 and (experience_max is None or experience_max <= 2))
        )
    )

    degrees = extract_degree_requirements(description)
    grad_years = extract_graduation_years(description)

    return OpportunityClassification(
        opportunity_type=opp_type,
        suitability=suitability,
        student_eligible=student_eligible,
        fresher_eligible=fresher_eligible,
        degree_requirements=degrees,
        graduation_year_requirements=grad_years,
        experience_min=experience_min,
        experience_max=experience_max,
    )
