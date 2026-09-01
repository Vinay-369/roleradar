"""
Deterministic Resume Strategy & ATS Template Selection Engine (Phase 17).
Maps candidate career stage, target job context, content density, and evidence priorities
to structured ATS section ordering, content emphasis, bullet budgets, and ATS-safe template families.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field

from app.modules.resume.classification import (
    CareerClassification,
    CareerClassificationResult,
    classify_candidate_profile,
    analyze_candidate_profile,
)
from app.modules.resume.models import CandidateProfile, ClaimType


class CareerStage(str, Enum):
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


class TemplateFamily(str, Enum):
    ATS_FRESHER = "ATS_FRESHER"
    ATS_PROFESSIONAL = "ATS_PROFESSIONAL"
    ATS_SENIOR = "ATS_SENIOR"
    ATS_CLASSIC_FALLBACK = "ATS_CLASSIC_FALLBACK"


class ContentDensity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class StrategyName(str, Enum):
    FRESHER_STUDENT = "FRESHER/STUDENT"
    ENTRY_LEVEL = "ENTRY_LEVEL"
    EARLY_CAREER = "EARLY_CAREER"
    PROFESSIONAL = "PROFESSIONAL"
    SENIOR = "SENIOR"
    LEADERSHIP = "LEADERSHIP"
    ACADEMIC_RESEARCH = "ACADEMIC/RESEARCH"
    CAREER_SWITCHER = "CAREER_SWITCHER"


STANDARD_ATS_HEADINGS: dict[str, str] = {
    "summary": "PROFESSIONAL SUMMARY",
    "skills": "TECHNICAL SKILLS",
    "experience": "PROFESSIONAL EXPERIENCE",
    "internships": "INTERNSHIPS",
    "projects": "PROJECTS",
    "education": "EDUCATION",
    "certifications": "CERTIFICATIONS",
    "achievements": "HONORS & AWARDS",
    "publications": "PUBLICATIONS & RESEARCH",
    "research": "RESEARCH EXPERIENCE",
    "languages": "LANGUAGES",
}


class TemplateSelection(BaseModel):
    template_family: TemplateFamily
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    template_variant: str = "classic"
    is_fallback: bool = False


class TemplateStrategy(BaseModel):
    strategy_name: StrategyName = StrategyName.PROFESSIONAL
    candidate_type: str = "experienced"
    template_variant: str = "classic"
    template_name: str = "classic_ats"
    section_order: list[str] = Field(
        default_factory=lambda: ["summary", "skills", "experience", "projects", "education", "certifications", "achievements", "languages"]
    )
    included_sections: list[str] = Field(
        default_factory=lambda: ["summary", "skills", "experience", "projects", "education", "certifications", "achievements"]
    )
    primary_emphasis: str = "TECHNICAL_DELIVERY"
    project_emphasis: bool = False
    experience_emphasis: bool = True
    max_recommended_bullets_per_role: int = 4
    max_recommended_projects: int = 3
    max_recommended_project_bullets: int = 3
    highlight_education_top: bool = False
    include_summary: bool = True
    summary_style: str = "TECHNICAL"
    page_budget: int = 1
    standard_ats_headings: dict[str, str] = Field(default_factory=lambda: dict(STANDARD_ATS_HEADINGS))


class ResumeStrategy(TemplateStrategy):
    """
    Rich canonical Resume Strategy representation.
    Decides WHAT to show, WHERE to show it, and HOW MUCH content budget to assign.
    """
    career_stage: CareerStage = CareerStage.PROFESSIONAL
    target_role: str | None = ""
    target_seniority: str | None = ""
    template_family: TemplateFamily = TemplateFamily.ATS_PROFESSIONAL
    page_budget: int = Field(default=1, ge=1, le=3)
    section_order: list[str] = Field(default_factory=list)
    section_priority: dict[str, float] = Field(default_factory=dict)
    evidence_priority: dict[str, float] = Field(default_factory=dict)
    skill_priority: list[str] = Field(default_factory=list)
    project_priority: list[str] = Field(default_factory=list)
    summary_strategy: str = "TECHNICAL"
    experience_strategy: str = "EXPERIENCE_DOMINANT"
    bullet_budget: dict[str, int] = Field(default_factory=dict)
    project_budget: int = 2
    content_density: ContentDensity = ContentDensity.MEDIUM
    compression_strategy: str = "BALANCED"
    confidence: float = 0.90
    reason_codes: list[str] = Field(default_factory=list)


def calculate_content_density(
    profile: CandidateProfile | dict[str, Any],
    years_of_experience: float = 0.0,
) -> ContentDensity:
    """
    Deterministically computes the content density (LOW, MEDIUM, HIGH)
    from candidate evidence, entities, roles, and project depth.
    """
    ev_count = len(getattr(profile, "evidence_units", [])) if hasattr(profile, "evidence_units") else len(profile.get("evidence_units", []))
    exp_count = len(getattr(profile, "experience", [])) if hasattr(profile, "experience") else len(profile.get("experience", []))
    proj_count = len(getattr(profile, "projects", [])) if hasattr(profile, "projects") else len(profile.get("projects", []))
    skills_count = len(getattr(profile, "skills", [])) if hasattr(profile, "skills") else len(profile.get("skills", []))
    edu_count = len(getattr(profile, "education", [])) if hasattr(profile, "education") else len(profile.get("education", []))
    cert_count = len(getattr(profile, "certifications", [])) if hasattr(profile, "certifications") else len(profile.get("certifications", []))

    density_score = ev_count + (skills_count * 0.2) + (proj_count * 1.5) + (exp_count * 2.0) + edu_count + cert_count

    if density_score > 22.0 or ev_count > 16 or (exp_count >= 3 and years_of_experience >= 7.0):
        return ContentDensity.HIGH
    elif density_score < 9.0 and ev_count < 7 and exp_count <= 1 and proj_count <= 1:
        return ContentDensity.LOW
    else:
        return ContentDensity.MEDIUM


def select_template_family(
    career_stage: CareerStage,
    content_density: ContentDensity,
    years_of_experience: float = 0.0,
    role_count: int = 0,
    project_count: int = 0,
) -> TemplateSelection:
    """
    Selects the deterministic ATS template family with confidence and audit reason codes.
    """
    # 1. ATS_FRESHER (Student, Fresher, Intern, Entry Level)
    if career_stage in (CareerStage.STUDENT, CareerStage.FRESHER, CareerStage.INTERN, CareerStage.ENTRY_LEVEL):
        reasons = ["fresher_entry_level_profile", "education_and_projects_prioritized", "single_page_budget"]
        if project_count >= 2:
            reasons.append("project_heavy_portfolio")
        return TemplateSelection(
            template_family=TemplateFamily.ATS_FRESHER,
            confidence=0.95,
            reason_codes=reasons,
            template_variant="modern",
            is_fallback=False,
        )

    # 2. ATS_SENIOR (Senior, Lead, Leadership, Manager, Director, Executive)
    if career_stage in (CareerStage.SENIOR, CareerStage.SENIOR_PROFESSIONAL, CareerStage.LEAD, CareerStage.LEADERSHIP, CareerStage.MANAGER, CareerStage.DIRECTOR, CareerStage.EXECUTIVE):
        reasons = ["senior_leadership_profile", "architectural_and_team_impact", "leadership_competencies_promoted"]
        if years_of_experience >= 8.0:
            reasons.append("extensive_industry_tenure")
        return TemplateSelection(
            template_family=TemplateFamily.ATS_SENIOR,
            confidence=0.95,
            reason_codes=reasons,
            template_variant="executive",
            is_fallback=False,
        )

    # 3. ATS_PROFESSIONAL (Early Career, Professional, Career Switcher, Academic/Research)
    if career_stage in (CareerStage.EARLY_CAREER, CareerStage.PROFESSIONAL, CareerStage.CAREER_SWITCHER, CareerStage.ACADEMIC, CareerStage.RESEARCH):
        reasons = ["experienced_professional_profile", "production_delivery_and_metrics_dominant"]
        if career_stage == CareerStage.CAREER_SWITCHER:
            reasons = ["career_switcher_profile", "transferable_skills_and_projects_promoted"]
        elif career_stage in (CareerStage.ACADEMIC, CareerStage.RESEARCH):
            reasons = ["academic_research_profile", "publications_and_research_promoted"]
        return TemplateSelection(
            template_family=TemplateFamily.ATS_PROFESSIONAL,
            confidence=0.92,
            reason_codes=reasons,
            template_variant="classic" if career_stage != CareerStage.CAREER_SWITCHER else "modern",
            is_fallback=False,
        )

    # 4. ATS_CLASSIC_FALLBACK
    return TemplateSelection(
        template_family=TemplateFamily.ATS_CLASSIC_FALLBACK,
        confidence=0.70,
        reason_codes=["uncertain_classification_fallback", "standard_ats_linear_hierarchy"],
        template_variant="classic",
        is_fallback=True,
    )


def compute_project_priorities(
    projects: list[Any],
    jd_requirements: Any = None,
    evidence_map: Any = None,
) -> list[str]:
    """
    Ranks candidate's verified projects by JD keyword alignment, metrics, and evidence depth.
    Never invents projects or claims.
    """
    if not projects:
        return []

    jd_skills = set()
    if jd_requirements:
        skills_raw = getattr(jd_requirements, "required_skills", []) or getattr(jd_requirements, "skills", [])
        if isinstance(skills_raw, list):
            for s in skills_raw:
                if isinstance(s, str):
                    jd_skills.add(s.lower())
                elif hasattr(s, "name"):
                    jd_skills.add(str(s.name).lower())

    scored_projects: list[tuple[float, str]] = []
    for idx, p in enumerate(projects):
        p_title = getattr(p, "title", "") or getattr(p, "name", "") or f"Project {idx+1}"
        p_techs = [t.lower() for t in getattr(p, "technologies", [])]
        bullets = [getattr(ev, "text", str(ev)) for ev in getattr(p, "evidence_units", [])] or getattr(p, "bullets", [])
        
        # Calculate overlap
        overlap_count = sum(1 for t in p_techs if any(t in s or s in t for s in jd_skills))
        metrics_count = sum(1 for b in bullets if bool(re.search(r"\b\d+(?:\.\d+)?%|\$\d+|\b\d+[kKmMbB]\b", b)))
        score = (overlap_count * 3.0) + (metrics_count * 2.0) + (len(bullets) * 1.0)
        scored_projects.append((score, p_title))

    # Sort descending by score
    scored_projects.sort(key=lambda x: x[0], reverse=True)
    return [title for _, title in scored_projects]


def compute_skill_priorities(
    candidate_skills: list[str],
    jd_requirements: Any = None,
    evidence_units: list[Any] | None = None,
) -> list[str]:
    """
    Orders candidate's VERIFIED skills by JD relevance and source evidence strength.
    INVARIANT: Never places a JD skill into skill_priority unless the candidate owns it.
    """
    if not candidate_skills:
        return []

    jd_skills = set()
    if jd_requirements:
        skills_raw = getattr(jd_requirements, "required_skills", []) or getattr(jd_requirements, "skills", [])
        if isinstance(skills_raw, list):
            for s in skills_raw:
                if isinstance(s, str):
                    jd_skills.add(s.lower())
                elif hasattr(s, "name"):
                    jd_skills.add(str(s.name).lower())

    # Calculate frequency in candidate evidence
    ev_texts = " ".join([getattr(ev, "text", str(ev)).lower() for ev in (evidence_units or [])])

    scored_skills: list[tuple[float, str]] = []
    for s in candidate_skills:
        s_clean = str(s).strip()
        if not s_clean:
            continue
        s_lower = s_clean.lower()
        is_jd_match = any(s_lower == js or s_lower in js or js in s_lower for js in jd_skills)
        ev_freq = ev_texts.count(s_lower)
        score = (3.0 if is_jd_match else 0.5) + min(ev_freq * 0.5, 2.0)
        scored_skills.append((score, s_clean))

    scored_skills.sort(key=lambda x: x[0], reverse=True)
    return [skill for _, skill in scored_skills]


def compute_bullet_budgets(
    experience: list[Any],
    page_budget: int,
    content_density: ContentDensity,
) -> dict[str, int]:
    """
    Determines recommended bullet limits per work experience role based on recency and page budget.
    """
    budgets: dict[str, int] = {}
    if not experience:
        return budgets

    for idx, exp in enumerate(experience):
        exp_id = getattr(exp, "id", f"exp_{idx}")
        if page_budget == 1:
            if idx == 0:
                budgets[exp_id] = 4 if content_density == ContentDensity.LOW else 3
            elif idx == 1:
                budgets[exp_id] = 3 if content_density != ContentDensity.HIGH else 2
            else:
                budgets[exp_id] = 2
        else:  # page_budget >= 2
            if idx == 0:
                budgets[exp_id] = 5
            elif idx <= 2:
                budgets[exp_id] = 4
            else:
                budgets[exp_id] = 3

    return budgets


def build_resume_strategy(
    profile: CandidateProfile,
    candidate_analysis: CareerClassificationResult | None = None,
    jd_requirements: Any = None,
    evidence_map: Any = None,
    target_role: str = "",
) -> ResumeStrategy:
    """
    Authoritative synthesis of Resume Strategy from CandidateProfile, CandidateAnalysis,
    JDRequirements, and Evidence Ledger.
    """
    # 1. Candidate Analysis & Classification
    if candidate_analysis is None:
        candidate_analysis = classify_candidate_profile(profile)

    c_val = candidate_analysis.classification.value if hasattr(candidate_analysis.classification, "value") else str(candidate_analysis.classification)
    
    # Map to CareerStage Enum
    try:
        career_stage = CareerStage(c_val)
    except ValueError:
        if c_val == "SENIOR_PROFESSIONAL":
            career_stage = CareerStage.SENIOR
        else:
            career_stage = CareerStage.PROFESSIONAL

    years = candidate_analysis.years_of_experience or 0.0
    role_count = len(getattr(profile, "experience", []))
    proj_count = len(getattr(profile, "projects", []))

    # 2. Content Density
    density = calculate_content_density(profile, years)

    # 3. Template Family Selection
    selection = select_template_family(career_stage, density, years, role_count, proj_count)

    # 4. Page Budget
    if selection.template_family == TemplateFamily.ATS_FRESHER:
        page_budget = 1
    elif selection.template_family == TemplateFamily.ATS_SENIOR:
        page_budget = 2 if density != ContentDensity.LOW or years >= 7.0 or role_count >= 3 else 1
    elif selection.template_family == TemplateFamily.ATS_PROFESSIONAL:
        page_budget = 2 if (density == ContentDensity.HIGH or years >= 6.0 or role_count >= 3) else 1
    else:  # ATS_CLASSIC_FALLBACK
        page_budget = 2 if density == ContentDensity.HIGH else 1

    # 5. Determine Base Section Ordering
    if career_stage in (CareerStage.STUDENT, CareerStage.FRESHER, CareerStage.INTERN):
        base_order = ["summary", "education", "skills", "projects", "internships", "experience", "certifications", "achievements", "languages"]
        strat_name = StrategyName.FRESHER_STUDENT
        cand_type = "student/fresher"
        primary_emp = "PROJECTS_AND_COURSEWORK"
        proj_emp, exp_emp = True, False
        sum_style = "OBJECTIVE_FOUNDATIONAL"
    elif career_stage == CareerStage.ENTRY_LEVEL:
        base_order = ["summary", "skills", "experience", "projects", "education", "certifications", "achievements", "languages"]
        strat_name = StrategyName.ENTRY_LEVEL
        cand_type = "entry-level"
        primary_emp = "PRACTICAL_EXPERIENCE_AND_PROJECTS"
        proj_emp, exp_emp = True, True
        sum_style = "EARLY_CAREER"
    elif career_stage == CareerStage.EARLY_CAREER:
        base_order = ["summary", "skills", "experience", "projects", "education", "certifications", "achievements", "languages"]
        strat_name = StrategyName.EARLY_CAREER
        cand_type = "experienced"
        primary_emp = "CORE_ENGINEERING_AND_OWNERSHIP"
        proj_emp, exp_emp = False, True
        sum_style = "TECHNICAL"
    elif career_stage in (CareerStage.LEAD, CareerStage.LEADERSHIP, CareerStage.MANAGER, CareerStage.DIRECTOR, CareerStage.EXECUTIVE):
        base_order = ["summary", "skills", "experience", "projects", "achievements", "education", "certifications", "languages"]
        strat_name = StrategyName.LEADERSHIP
        cand_type = "senior/professional"
        primary_emp = "EXECUTIVE_LEADERSHIP_AND_STRATEGY"
        proj_emp, exp_emp = False, True
        sum_style = "EXECUTIVE"
    elif career_stage in (CareerStage.SENIOR, CareerStage.SENIOR_PROFESSIONAL):
        base_order = ["summary", "skills", "experience", "projects", "achievements", "education", "certifications", "languages"]
        strat_name = StrategyName.SENIOR
        cand_type = "senior/professional"
        primary_emp = "SYSTEM_ARCHITECTURE_AND_IMPACT"
        proj_emp, exp_emp = False, True
        sum_style = "SENIOR_TECHNICAL"
    elif career_stage in (CareerStage.ACADEMIC, CareerStage.RESEARCH):
        base_order = ["summary", "education", "publications", "research", "skills", "experience", "projects", "certifications", "languages"]
        strat_name = StrategyName.ACADEMIC_RESEARCH
        cand_type = "academic/research"
        primary_emp = "PUBLICATIONS_AND_RESEARCH"
        proj_emp, exp_emp = True, False
        sum_style = "ACADEMIC"
    elif career_stage == CareerStage.CAREER_SWITCHER:
        base_order = ["summary", "skills", "projects", "experience", "education", "certifications", "achievements", "languages"]
        strat_name = StrategyName.CAREER_SWITCHER
        cand_type = "career-switcher"
        primary_emp = "TRANSFERABLE_SKILLS_AND_PORTFOLIO"
        proj_emp, exp_emp = True, False
        sum_style = "CAREER_TRANSITION"
    else:
        base_order = ["summary", "skills", "experience", "projects", "education", "certifications", "achievements", "languages"]
        strat_name = StrategyName.PROFESSIONAL
        cand_type = "experienced"
        primary_emp = "PRODUCTION_DELIVERY_AND_METRICS"
        proj_emp, exp_emp = False, True
        sum_style = "TECHNICAL"

    # 6. Filter out empty sections
    active_sections = []
    has_summary = bool(getattr(profile, "summary", "")) or bool(getattr(profile, "personal", {}).get("summary"))
    has_skills = bool(getattr(profile, "skills", []))
    has_exp = bool(getattr(profile, "experience", []))
    has_proj = bool(getattr(profile, "projects", []))
    has_edu = bool(getattr(profile, "education", []))
    has_certs = bool(getattr(profile, "certifications", []))
    has_achs = bool(getattr(profile, "achievements", []))
    has_pubs = bool(getattr(profile, "publications", []))
    has_res = bool(getattr(profile, "research", []))
    has_langs = bool(getattr(profile, "languages", []))

    for sec in base_order:
        if sec == "summary" and has_summary:
            active_sections.append(sec)
        elif sec == "skills" and has_skills:
            active_sections.append(sec)
        elif sec in ("experience", "internships") and has_exp and "experience" not in active_sections:
            active_sections.append("experience")
        elif sec == "projects" and has_proj:
            active_sections.append(sec)
        elif sec == "education" and has_edu:
            active_sections.append(sec)
        elif sec == "certifications" and has_certs:
            active_sections.append(sec)
        elif sec == "achievements" and has_achs:
            active_sections.append(sec)
        elif sec == "publications" and has_pubs:
            active_sections.append(sec)
        elif sec == "research" and has_res:
            active_sections.append(sec)
        elif sec == "languages" and has_langs:
            active_sections.append(sec)

    # Add custom additional sections
    for add_sec in getattr(profile, "additional_sections", []):
        sec_title = (getattr(add_sec, "heading", "") or getattr(add_sec, "title", "")).lower()
        if sec_title and sec_title not in active_sections:
            active_sections.append(sec_title)

    # 7. Compute Project & Skill Priorities
    proj_priorities = compute_project_priorities(getattr(profile, "projects", []), jd_requirements, evidence_map)
    skill_priorities = compute_skill_priorities(getattr(profile, "skills", []), jd_requirements, getattr(profile, "evidence_units", []))
    bullet_budgets = compute_bullet_budgets(getattr(profile, "experience", []), page_budget, density)

    # 8. Section priority weights
    section_priorities: dict[str, float] = {}
    for idx, s in enumerate(active_sections):
        section_priorities[s] = round(1.0 - (idx * 0.08), 2)

    # Target metadata
    resolved_target_role = str(target_role or (getattr(jd_requirements, "role_title", "") if jd_requirements else "") or "")
    resolved_seniority = str((getattr(jd_requirements, "seniority", "") if jd_requirements else "") or "")

    project_budget = 3 if proj_emp else (2 if density != ContentDensity.LOW else 1)

    # Set base_order for included_sections
    included_sections = list(base_order)

    return ResumeStrategy(
        career_stage=career_stage,
        target_role=resolved_target_role,
        target_seniority=resolved_seniority,
        template_family=selection.template_family,
        page_budget=page_budget,
        section_order=active_sections,
        section_priority=section_priorities,
        evidence_priority={},
        skill_priority=skill_priorities,
        project_priority=proj_priorities,
        summary_strategy=sum_style,
        experience_strategy="EXPERIENCE_DOMINANT" if exp_emp else "BALANCED_PROJECTS",
        bullet_budget=bullet_budgets,
        project_budget=project_budget,
        content_density=density,
        compression_strategy="SELECTIVE_CONDENSATION" if density == ContentDensity.HIGH else "BALANCED",
        confidence=selection.confidence,
        reason_codes=selection.reason_codes,
        strategy_name=strat_name,
        candidate_type=cand_type,
        template_variant=selection.template_variant,
        template_name=selection.template_family.value.lower(),
        included_sections=included_sections,
        primary_emphasis=primary_emp,
        project_emphasis=proj_emp,
        experience_emphasis=exp_emp,
        max_recommended_bullets_per_role=5 if (page_budget >= 2 or career_stage in (CareerStage.SENIOR, CareerStage.SENIOR_PROFESSIONAL, CareerStage.LEAD, CareerStage.LEADERSHIP, CareerStage.MANAGER, CareerStage.DIRECTOR, CareerStage.EXECUTIVE)) else 4,
        max_recommended_projects=project_budget,
        max_recommended_project_bullets=3,
        highlight_education_top=(career_stage in (CareerStage.STUDENT, CareerStage.FRESHER, CareerStage.ACADEMIC, CareerStage.RESEARCH)),
        include_summary=has_summary,
        summary_style=sum_style,
    )


def resolve_template_strategy(
    classification: CareerClassificationResult | CareerClassification | Any,
    target_role: str = "",
    years_of_experience: float | None = None,
    role_count: int = 1,
    project_count: int = 1,
) -> ResumeStrategy:
    """
    Backward-compatible entrypoint for TemplateStrategy resolution.
    Returns a complete, authoritative ResumeStrategy instance.
    """
    if isinstance(classification, CareerClassificationResult):
        c = classification.classification
        years = classification.years_of_experience or 0.0
    elif isinstance(classification, CareerClassification):
        c = classification
        years = years_of_experience or 0.0
    elif hasattr(classification, "career_stage") and getattr(classification, "career_stage"):
        c = getattr(classification, "career_stage")
        years = getattr(classification, "years_of_experience", 0.0) or 0.0
    else:
        c = CareerClassification.PROFESSIONAL
        years = years_of_experience or 0.0

    if isinstance(c, str):
        try:
            c_stage = CareerStage(c)
        except ValueError:
            c_stage = CareerStage.PROFESSIONAL
    elif hasattr(c, "value"):
        try:
            c_stage = CareerStage(c.value)
        except ValueError:
            c_stage = CareerStage.PROFESSIONAL
    else:
        c_stage = CareerStage.PROFESSIONAL

    # Clean dummy profile without artificial numeric claims
    dummy_profile = CandidateProfile(
        personal={"name": "Candidate", "summary": "Experienced engineer"},
        summary="Experienced engineer",
        skills=["Core Skills"],
        experience=[{"id": f"exp_{i}", "company": "Company", "role": "Engineer"} for i in range(max(1, role_count))],
        projects=[{"id": f"proj_{i}", "title": "Project"} for i in range(max(1, project_count))],
        education=[{"id": "edu_0", "degree": "B.S. in Computer Science", "institution": "University"}],
        publications=["Publication"] if c_stage in (CareerStage.ACADEMIC, CareerStage.RESEARCH) else [],
        research=["Research"] if c_stage in (CareerStage.ACADEMIC, CareerStage.RESEARCH) else [],
    )

    analysis = CareerClassificationResult(
        classification=CareerClassification(c_stage.value) if c_stage.value in CareerClassification._value2member_map_ else CareerClassification.PROFESSIONAL,
        years_of_experience=years,
        professional_role_count=role_count,
    )

    return build_resume_strategy(
        profile=dummy_profile,
        candidate_analysis=analysis,
        target_role=target_role,
    )


def render_profile_with_strategy(
    profile: Any,
    strategy: TemplateStrategy | ResumeStrategy,
) -> dict:
    """
    Renders the canonical CandidateProfile into a structured dictionary following
    the deterministic section ordering and constraints of the ResumeStrategy.
    Guarantees 100% data preservation without altering candidate claims or evidence.
    """
    if hasattr(profile, "to_parsed_dict"):
        base_dict = profile.to_parsed_dict()
    elif isinstance(profile, dict):
        base_dict = dict(profile)
    else:
        base_dict = {}

    ordered_dict: dict[str, Any] = {
        "personal": base_dict.get("personal", {}),
        "_strategy": strategy.model_dump(mode="json"),
        "_ordered_sections": strategy.section_order,
    }

    section_key_map = {
        "summary": "summary",
        "skills": "skills",
        "experience": "experience_raw",
        "internships": "experience_raw",
        "projects": "projects_raw",
        "education": "education_raw",
        "certifications": "certifications",
        "achievements": "achievements",
        "publications": "publications_raw",
        "research": "research_raw",
        "languages": "languages",
    }

    for sec in strategy.section_order:
        data_key = section_key_map.get(sec, sec)
        if data_key in base_dict and base_dict[data_key]:
            ordered_dict[data_key] = base_dict[data_key]

    for k, v in base_dict.items():
        if k not in ordered_dict:
            ordered_dict[k] = v

    return ordered_dict
