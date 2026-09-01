"""
Multi-Signal Candidate Experience & Career Profile Classifier.
Classifies candidate based on multiple holistic signals (roles, dates, project depth,
education status, title seniority, leadership, research, and domain shifts) rather than years alone.
"""
from __future__ import annotations

import datetime
from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field

from app.modules.resume.models import CandidateProfile, ClaimType

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}


class CareerClassification(str, Enum):
    STUDENT = "STUDENT"
    FRESHER = "FRESHER"
    INTERN = "INTERN"
    ENTRY_LEVEL = "ENTRY_LEVEL"
    EARLY_CAREER = "EARLY_CAREER"
    PROFESSIONAL = "PROFESSIONAL"
    SENIOR = "SENIOR"
    SENIOR_PROFESSIONAL = "SENIOR_PROFESSIONAL"
    LEAD = "LEAD"
    LEADERSHIP = "LEADERSHIP"
    MANAGER = "MANAGER"
    DIRECTOR = "DIRECTOR"
    EXECUTIVE = "EXECUTIVE"
    ACADEMIC = "ACADEMIC"
    RESEARCH = "RESEARCH"
    CAREER_SWITCHER = "CAREER_SWITCHER"
    OTHER = "OTHER"


class CareerClassificationResult(BaseModel):
    classification: CareerClassification
    career_profile: CareerClassification | None = None
    career_stage: CareerClassification | None = None
    experience_level: str = "MID"
    experience_depth: str = "STANDARD"
    project_depth: str = "STANDARD"
    technical_breadth: str = "BALANCED"
    skill_count: int = 0
    internship_presence: bool = False
    leadership_evidence: bool = False
    leadership_score: float = 0.0
    research_orientation: bool = False
    research_score: float = 0.0
    management_orientation: bool = False
    management_score: float = 0.0
    career_transition_indicators: list[str] = Field(default_factory=list)
    content_density: dict[str, Any] = Field(default_factory=dict)
    professional_role_count: int = 0
    career_continuity: str = "CONTINUOUS"
    confidence: float = 0.90
    is_ambiguous: bool = False
    reasoning: list[str] = Field(default_factory=list)
    years_of_experience: float = 0.0
    is_student: bool = False
    has_leadership_evidence: bool = False


CandidateAnalysisResult = CareerClassificationResult


SENIOR_TITLE_KEYWORDS = {"senior", "sr.", "sr", "lead", "staff", "principal", "architect", "expert"}
LEADERSHIP_TITLE_KEYWORDS = {"director", "vp", "vice president", "head", "manager", "chief", "cto", "cio", "founder", "co-founder", "executive"}
MANAGEMENT_TITLE_KEYWORDS = {"manager", "engineering manager", "program manager", "product manager", "director", "head of"}
ACADEMIC_KEYWORDS = {"phd", "ph.d", "postdoctoral", "postdoc", "research scientist", "fellow", "professor", "adjunct", "lecturer", "pi"}
JUNIOR_TITLE_KEYWORDS = {"intern", "trainee", "student", "graduate", "junior", "jr.", "jr", "associate", "apprentice"}
TIERED_SENIOR_RE = re.compile(r"\b(?:software\s+engineer\s*[-–—]?\s*(?:3|iii|4|iv|5|v)|se[- ]?3|swe[- ]?3|engineer[- ]?3|level[- ]?(?:3|4|5|6)|l3|l4|l5|l6)\b", re.IGNORECASE)


def parse_date_point(token: str, default_to_now: bool = False) -> tuple[int, int] | None:
    token_clean = token.strip().lower()
    now = datetime.date.today()
    if re.search(r"\b(present|current|ongoing|now)\b", token_clean):
        return (now.year, now.month)

    m_my = re.search(r"\b([a-z]{3,9})\.?\s+(\d{4})\b", token_clean)
    if m_my:
        m_str, y_str = m_my.group(1), m_my.group(2)
        month = MONTH_MAP.get(m_str[:3], 6)
        return (int(y_str), month)

    m_num = re.search(r"\b(\d{1,2})[/.-](\d{4})\b", token_clean)
    if m_num:
        return (int(m_num.group(2)), int(m_num.group(1)))

    m_yr = re.search(r"\b(19\d{2}|20\d{2})\b", token_clean)
    if m_yr:
        yr = int(m_yr.group(1))
        return (yr, 1 if not default_to_now else 12)

    return None


def parse_interval(date_str: str) -> tuple[tuple[int, int], tuple[int, int]] | None:
    if not date_str:
        return None

    parts = re.split(r"[-–—to]+", date_str, flags=re.IGNORECASE)
    if len(parts) >= 2:
        start = parse_date_point(parts[0], default_to_now=False)
        end = parse_date_point(parts[1], default_to_now=True)
        if start and end:
            if (start[0] * 12 + start[1]) > (end[0] * 12 + end[1]):
                start, end = end, start
            return (start, end)
        elif start:
            now = datetime.date.today()
            return (start, (now.year, now.month))
    elif len(parts) == 1:
        pt = parse_date_point(parts[0], default_to_now=False)
        if pt:
            return (pt, (pt[0], 12))
    return None


def merge_date_intervals(intervals: list[tuple[tuple[int, int], tuple[int, int]]]) -> list[tuple[int, int]]:
    """Converts (start, end) date intervals to merged non-overlapping integer month spans."""
    if not intervals:
        return []
    month_ranges = sorted([(s[0] * 12 + s[1], e[0] * 12 + e[1]) for s, e in intervals])
    merged = [month_ranges[0]]
    for cur_s, cur_e in month_ranges[1:]:
        prev_s, prev_e = merged[-1]
        if cur_s <= prev_e:
            merged[-1] = (prev_s, max(prev_e, cur_e))
        else:
            merged.append((cur_s, cur_e))
    return merged


def calculate_experience_duration(date_strings: list[str]) -> float:
    """Calculates non-overlapping years of experience across arbitrary date intervals without hardcoded years."""
    intervals = []
    for d in date_strings:
        inv = parse_interval(d)
        if inv:
            intervals.append(inv)

    if not intervals:
        return 0.0

    merged = merge_date_intervals(intervals)
    total_months = sum(e - s + 1 for s, e in merged)
    return round(max(0.0, total_months / 12.0), 1)


def _parse_year_span(date_str: str) -> tuple[int | None, int | None]:
    """Extracts start year and end year from date string e.g. '2023 - 2027', '2019 - Present', '2022'."""
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", date_str)]
    if not years:
        return None, None
    now_yr = datetime.date.today().year
    if len(years) == 1:
        if re.search(r"\b(present|current|ongoing)\b", date_str, re.IGNORECASE):
            return years[0], now_yr
        return years[0], years[0]
    return min(years), max(years)


def analyze_candidate_profile(
    profile: CandidateProfile,
    raw_text: str = "",
) -> CandidateAnalysisResult:
    """
    Analyzes candidate profile holistically and deterministically.
    Produces comprehensive multi-signal classification without rigid over-fitting.
    """
    reasons: list[str] = []
    now_yr = datetime.date.today().year

    # 1. Analyze Education for student / ongoing degree signals & academic background
    is_student = False
    has_phd_or_academic = False
    degree_names = []
    for edu in profile.education:
        degree_lower = edu.degree.lower()
        degree_names.append(degree_lower)
        if any(w in degree_lower for w in ["ph.d", "phd", "doctorate", "postdoctoral", "fellow"]):
            has_phd_or_academic = True
        if edu.dates:
            s_yr, e_yr = _parse_year_span(edu.dates)
            if e_yr and e_yr > now_yr:
                is_student = True
                reasons.append(f"Education dates {edu.dates} indicate ongoing studies (graduating {e_yr}).")
                break
        if re.search(r"202[7-9]|203\d", edu.degree + " " + (edu.dates or "")):
            is_student = True
            reasons.append(f"Degree string '{edu.degree}' indicates future graduation.")
            break

    # 2. Analyze Experience & non-overlapping dates
    has_full_time = False
    senior_titles = 0
    leadership_titles = 0
    management_titles = 0
    junior_titles = 0
    all_date_strs: list[str] = []

    summary_lower = (profile.summary or "").lower()
    if any(w in summary_lower for w in ["senior software engineer", "senior engineer", "lead engineer", "staff engineer"]):
        senior_titles += 1
    if any(w in summary_lower for w in ["director", "engineering manager", "head of engineering", "vp"]):
        leadership_titles += 1

    for exp in profile.experience:
        all_roles_for_entity = [exp.role] + [p.title for p in exp.progression]
        for r_title in all_roles_for_entity:
            role_lower = r_title.lower()
            if any(w in role_lower for w in LEADERSHIP_TITLE_KEYWORDS):
                leadership_titles += 1
            if any(w in role_lower for w in MANAGEMENT_TITLE_KEYWORDS):
                management_titles += 1
            if any(w in role_lower for w in SENIOR_TITLE_KEYWORDS) or TIERED_SENIOR_RE.search(role_lower):
                senior_titles += 1
            elif any(w in role_lower for w in JUNIOR_TITLE_KEYWORDS):
                junior_titles += 1
            elif any(w in role_lower for w in ACADEMIC_KEYWORDS):
                has_phd_or_academic = True
            else:
                has_full_time = True

        if exp.dates:
            all_date_strs.append(exp.dates)
        for p in exp.progression:
            if p.dates:
                all_date_strs.append(p.dates)

    years_exp = calculate_experience_duration(all_date_strs)
    if years_exp == 0.0 and len(profile.experience) > 0:
        years_exp = round(len(profile.experience) * 1.0, 1)

    # 3. Analyze Leadership, Research, and Management Evidence
    leadership_evs = [
        ev for ev in profile.evidence_units
        if ev.claim_type == ClaimType.LEADERSHIP or
        any(w in ev.normalized_text.lower().split() for w in ["managed", "directed", "spearheaded", "mentored", "hired", "budgeted", "led", "supervised"])
    ]
    leadership_score = min(1.0, round((len(leadership_evs) * 0.25) + (leadership_titles * 0.35), 2))
    has_leadership = leadership_score >= 0.35 or leadership_titles > 0

    research_count = len(profile.publications) + len(profile.research)
    research_evs = [ev for ev in profile.evidence_units if any(w in ev.normalized_text.lower() for w in ["publication", "paper", "grant", "novel algorithm", "peer-reviewed", "conference"])]
    research_score = min(1.0, round((research_count * 0.3) + (len(research_evs) * 0.2) + (0.4 if has_phd_or_academic else 0.0), 2))
    has_research = research_score >= 0.35

    management_evs = [ev for ev in profile.evidence_units if any(w in ev.normalized_text.lower() for w in ["team of", "engineers", "budget", "hiring", "headcount", "kpis", "okrs"])]
    management_score = min(1.0, round((management_titles * 0.4) + (len(management_evs) * 0.2), 2))
    has_management = management_score >= 0.35 or management_titles > 0

    # 4. Career Transition Indicators
    career_transitions: list[str] = []
    if degree_names:
        non_cs = any(any(k in d for k in ["mechanical", "civil", "chemical", "biology", "commerce", "arts", "economics", "finance"]) for d in degree_names)
        has_swe = any("engineer" in exp.role.lower() or "developer" in exp.role.lower() for exp in profile.experience)
        if non_cs and has_swe:
            career_transitions.append("Transitioned from non-computing academic background into Software Engineering.")

    # 5. Technical Breadth & Content Density
    total_skills = len(profile.skills)
    for s_cat in profile.skills_categorized:
        if hasattr(s_cat, "skills"):
            total_skills += len(s_cat.skills)
        elif isinstance(s_cat, dict):
            total_skills += len(s_cat.get("skills", []))
    for exp in profile.experience:
        for ev in exp.evidence_units:
            total_skills += len(ev.technologies)

    unique_skills = set(profile.skills)
    for exp in profile.experience:
        for ev in exp.evidence_units:
            unique_skills.update(ev.technologies)
    skill_count = len(unique_skills)

    if skill_count <= 4:
        tech_breadth = "NARROW"
    elif skill_count <= 12:
        tech_breadth = "BALANCED"
    else:
        tech_breadth = "WIDE"

    total_words = sum(len(ev.text.split()) for ev in profile.evidence_units)
    quantified_count = sum(1 for ev in profile.evidence_units if ev.metrics or ev.claim_type == ClaimType.METRIC)
    content_density = {
        "total_evidence_units": len(profile.evidence_units),
        "total_words": total_words,
        "quantified_evidence_count": quantified_count,
        "avg_words_per_evidence": round(total_words / max(1, len(profile.evidence_units)), 1),
    }

    # 6. Experience & Project Depth
    if years_exp == 0:
        exp_depth = "NONE"
    elif years_exp < 2:
        exp_depth = "SHALLOW"
    elif years_exp < 4.0:
        exp_depth = "MODERATE"
    elif years_exp < 8.0:
        exp_depth = "DEEP"
    else:
        exp_depth = "EXTENSIVE"

    proj_count = len(profile.projects)
    if proj_count == 0:
        proj_depth = "NONE"
    elif proj_count == 1:
        proj_depth = "LIGHT"
    elif proj_count <= 3:
        proj_depth = "STRONG"
    else:
        proj_depth = "EXTENSIVE"

    has_internship = (
        len(profile.internships) > 0
        or any("intern" in exp.role.lower() for exp in profile.experience)
        or junior_titles > 0
    )

    if is_student:
        continuity = "STUDENT"
    elif years_exp <= 1.0:
        continuity = "EARLY_STAGE"
    else:
        continuity = "CONTINUOUS"

    # 7. Multi-Signal Career Classification Matrix
    is_ambiguous = False
    if is_student:
        if len(profile.experience) == 0 and len(profile.projects) >= 1:
            classification = CareerClassification.STUDENT
            exp_level = "STUDENT"
            reasons.append(f"Student with {len(profile.projects)} projects and active degree.")
        else:
            classification = CareerClassification.FRESHER
            exp_level = "FRESHER/STUDENT"
            reasons.append("Ongoing education detected; classified as Fresher/Student.")
        confidence = 0.95
    elif has_research and research_score >= 0.55:
        classification = CareerClassification.RESEARCH if has_phd_or_academic else CareerClassification.ACADEMIC
        exp_level = "ACADEMIC/RESEARCH"
        reasons.append(f"Strong research and publication profile with score {research_score}.")
        confidence = 0.90
    elif (leadership_titles >= 1 or has_management) and years_exp >= 7.0:
        classification = CareerClassification.LEADERSHIP
        exp_level = "LEADERSHIP"
        reasons.append(f"Leadership/management track with {years_exp} estimated years of experience.")
        confidence = 0.90
    elif (senior_titles >= 1 or years_exp >= 8.0):
        classification = CareerClassification.SENIOR_PROFESSIONAL
        exp_level = "SENIOR"
        reasons.append(f"Senior titles ({senior_titles}) and {years_exp} estimated years of experience.")
        confidence = 0.90
    elif years_exp >= 4.5 and junior_titles == 0 and not is_student:
        classification = CareerClassification.PROFESSIONAL
        exp_level = "PROFESSIONAL"
        reasons.append(f"Mid-level professional with {years_exp} estimated years of experience across {len(profile.experience)} roles.")
        confidence = 0.85
    elif years_exp >= 1.0 or (has_full_time and len(profile.experience) >= 1) or junior_titles > 0:
        classification = CareerClassification.EARLY_CAREER
        exp_level = "EARLY_CAREER"
        reasons.append(f"Early career engineer with {years_exp} estimated years of experience.")
        confidence = 0.85
    elif len(profile.experience) >= 1 or len(profile.internships) >= 1:
        classification = CareerClassification.ENTRY_LEVEL
        exp_level = "ENTRY_LEVEL"
        reasons.append(f"Entry-level profile with {len(profile.experience)} roles / internships and {len(profile.projects)} projects.")
        confidence = 0.85
    else:
        classification = CareerClassification.FRESHER
        exp_level = "FRESHER/STUDENT"
        reasons.append(f"Fresher profile with {len(profile.projects)} academic/technical projects and no full-time experience.")
        confidence = 0.90

    return CandidateAnalysisResult(
        classification=classification,
        career_profile=classification,
        career_stage=classification,
        experience_level=exp_level,
        experience_depth=exp_depth,
        project_depth=proj_depth,
        technical_breadth=tech_breadth,
        skill_count=skill_count,
        internship_presence=has_internship,
        leadership_evidence=has_leadership,
        leadership_score=leadership_score,
        research_orientation=has_research,
        research_score=research_score,
        management_orientation=has_management,
        management_score=management_score,
        career_transition_indicators=career_transitions,
        content_density=content_density,
        professional_role_count=len(profile.experience),
        career_continuity=continuity,
        confidence=confidence,
        is_ambiguous=is_ambiguous,
        reasoning=reasons,
        years_of_experience=years_exp,
        is_student=is_student,
        has_leadership_evidence=has_leadership,
    )


# Backward compatibility alias
classify_candidate_profile = analyze_candidate_profile
