"""
Canonical Data Model for RoleRadar Resume Intelligence & Provenance Tracking.
Provides structured CandidateProfile, Entity definitions, and EvidenceUnit provenance.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field

from app.modules.resume.metrics import extract_quantified_metrics, _extract_quantified_metrics


class ClaimType(str, Enum):
    ACTION = "ACTION"
    TECHNOLOGY = "TECHNOLOGY"
    RESPONSIBILITY = "RESPONSIBILITY"
    OUTCOME = "OUTCOME"
    METRIC = "METRIC"
    SCALE = "SCALE"
    DOMAIN = "DOMAIN"
    LEADERSHIP = "LEADERSHIP"
    OWNERSHIP = "OWNERSHIP"
    PERFORMANCE = "PERFORMANCE"
    BUSINESS_IMPACT = "BUSINESS_IMPACT"
    # Legacy / Compatibility Aliases
    DELIVERY = "DELIVERY"
    ACHIEVEMENT = "ACHIEVEMENT"
    QUALIFICATION = "QUALIFICATION"


class SourceCoverageState(str, Enum):
    PRESERVED = "PRESERVED"
    REWRITTEN = "REWRITTEN"
    CONDENSED = "CONDENSED"
    REORDERED = "REORDERED"
    INTENTIONALLY_REMOVED = "INTENTIONALLY_REMOVED"
    NEEDS_USER_INPUT = "NEEDS_USER_INPUT"
    ACCIDENTALLY_LOST = "ACCIDENTALLY_LOST"
    INVALID = "INVALID"


class TailoringAction(str, Enum):
    PRESERVE = "PRESERVE"
    REWRITE = "REWRITE"
    CONDENSE = "CONDENSE"
    REORDER = "REORDER"
    PRIORITIZE = "PRIORITIZE"
    DEPRIORITIZE = "DEPRIORITIZE"
    REMOVE = "REMOVE"
    NEEDS_USER_INPUT = "NEEDS_USER_INPUT"


class TailoringDecision(BaseModel):
    """
    Explicit tailoring decision applied to a specific EvidenceUnit.
    """
    evidence_id: str
    action: TailoringAction = TailoringAction.PRESERVE
    proposed_text: str | None = None
    rewritten_text: str | None = None
    reason: str = ""
    removal_reason: str = ""
    source_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if self.rewritten_text and not self.proposed_text:
            self.proposed_text = self.rewritten_text
        elif self.proposed_text and not self.rewritten_text:
            self.rewritten_text = self.proposed_text
        if self.removal_reason and not self.reason:
            self.reason = self.removal_reason
        elif self.reason and not self.removal_reason:
            self.removal_reason = self.reason


class TailoringPlan(BaseModel):
    """
    Authoritative Tailoring Plan produced by AI intelligence layer.
    Directly consumes and targets EvidenceUnit IDs.
    """
    summary_rewrite: str | None = None
    summary_evidence_id: str = "SUM_001"
    evidence_decisions: list[TailoringDecision] = Field(default_factory=list)
    decisions: list[TailoringDecision] = Field(default_factory=list)
    ordered_skills: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if self.decisions and not self.evidence_decisions:
            self.evidence_decisions = self.decisions
        elif self.evidence_decisions and not self.decisions:
            self.decisions = self.evidence_decisions
    skill_additions: list[str] = Field(default_factory=list)
    section_priority: list[str] = Field(default_factory=list)
    unmatched_gaps: list[str] = Field(default_factory=list)
    removal_reasons: dict[str, str] = Field(default_factory=dict)


def slugify_token(text: str, fallback: str = "ITEM", max_len: int = 16) -> str:
    """
    Extracts a clean, deterministic, semantic uppercase identifier token from text.
    """
    if not text:
        return fallback
    cleaned = re.sub(r"^[•\-\*\s:]+|[•\-\*\s:]+$", "", text).strip()
    cleaned = re.sub(r"\bci\s*/\s*cd\b", "CICD", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmachine\s+learning\b", "ML", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bartificial\s+intelligence\b", "AI", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdeep\s+learning\b", "DL", cleaned, flags=re.IGNORECASE)

    tokens = [re.sub(r"[^A-Za-z0-9]", "", w).upper() for w in cleaned.split() if re.sub(r"[^A-Za-z0-9]", "", w)]
    if not tokens:
        return fallback

    stopwords = {
        "THE", "A", "AN", "AND", "OF", "FOR", "IN", "TO", "WITH", "AT", "ON", "BY",
        "FROM", "DEVELOPMENT", "SOLUTIONS", "TECHNOLOGIES", "TECH", "NETWORKS",
        "SYSTEMS", "CORP", "INC", "LLC", "LTD", "COMPANY", "PROJECT", "SOFTWARE", "ENGINEER"
    }
    meaningful = [t for t in tokens if t not in stopwords]

    if meaningful:
        token = meaningful[0]
        if len(meaningful) >= 2 and len(meaningful[0]) <= 6 and len(meaningful[1]) <= 6:
            token = f"{meaningful[0]}_{meaningful[1]}"
    else:
        token = tokens[0]

    return token[:max_len]


def generate_stable_evidence_id(
    section: str,
    entity_name: str,
    group_or_role: str = "",
    item_num: int = 1,
) -> str:
    """
    Generates permanent, semantic, human-readable EvidenceUnit IDs.
    Examples:
    - EXP_JUNIPER_MARVIS_001
    - EXP_JUNIPER_PACKAGING_001
    - PROJ_VIRTUALBG_001
    - SUM_001
    """
    sec_prefix = section.upper()[:4]
    if sec_prefix.startswith("EXP"):
        sec_prefix = "EXP"
    elif sec_prefix.startswith("PROJ"):
        sec_prefix = "PROJ"
    elif sec_prefix.startswith("SUM"):
        return f"SUM_{item_num:03d}"
    elif sec_prefix.startswith("SKILL"):
        return f"SKILL_{slugify_token(entity_name, 'GENERAL')}"

    ent_tok = slugify_token(entity_name, "CORP")
    if group_or_role:
        grp_tok = slugify_token(group_or_role, "")
        if grp_tok and grp_tok != ent_tok:
            return f"{sec_prefix}_{ent_tok}_{grp_tok}_{item_num:03d}"

    return f"{sec_prefix}_{ent_tok}_{item_num:03d}"


class AdditionalSectionEntity(BaseModel):
    """
    Arbitrary, custom, or unrecognized semantic section preserved with 100% evidence fidelity.
    """
    id: str
    heading: str
    semantic_type: str = "UNKNOWN"
    items: list[str] = Field(default_factory=list)
    text: str = ""
    evidence_units: list[EvidenceUnit] = Field(default_factory=list)

    @property
    def title(self) -> str:
        return self.heading


class EvidenceUnit(BaseModel):
    """
    Atomic verified candidate claim with full provenance tracking and stable semantic identity.
    """
    id: str
    section: str
    entity_id: str | None = None
    original_text: str
    normalized_text: str
    claim_type: ClaimType = ClaimType.DELIVERY
    technologies: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    source_reference: str = ""
    source_location: str = ""
    claims: list[str] = Field(default_factory=list)

    @property
    def text(self) -> str:
        return self.normalized_text or self.original_text

    @property
    def parent_entity_id(self) -> str | None:
        return self.entity_id


class RoleProgression(BaseModel):
    id: str = Field(default_factory=str)
    title: str
    dates: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    bullets: list[str] = Field(default_factory=list)
    evidence_units: list[EvidenceUnit] = Field(default_factory=list)


class ResponsibilityGroup(BaseModel):
    id: str
    heading: str
    technologies: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    evidence_units: list[EvidenceUnit] = Field(default_factory=list)


class WorkExperienceEntity(BaseModel):
    """
    Structured work experience or internship entry with role progression and responsibility groups.
    """
    id: str
    company: str
    role: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    dates: str | None = None
    employment_type: str | None = None
    progression: list[RoleProgression] = Field(default_factory=list)
    responsibility_groups: list[ResponsibilityGroup] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    evidence_units: list[EvidenceUnit] = Field(default_factory=list)

    @property
    def organization(self) -> str:
        return self.company

    @property
    def date_range(self) -> str | None:
        return self.dates

    @property
    def roles(self) -> list[RoleProgression]:
        return self.progression


class ProjectEntity(BaseModel):
    """
    Structured project entry preserving title, tech stack, and bullets.
    """
    id: str
    title: str
    tech_stack: str | None = None
    technologies: list[str] = Field(default_factory=list)
    dates: str | None = None
    url: str | None = None
    bullets: list[str] = Field(default_factory=list)
    evidence_units: list[EvidenceUnit] = Field(default_factory=list)

    @property
    def link(self) -> str | None:
        return self.url

    @property
    def name(self) -> str:
        return self.title


class EducationEntity(BaseModel):
    """
    Structured education institution & qualification entry.
    """
    id: str
    institution: str
    degree: str
    dates: str | None = None
    location: str | None = None
    gpa: str | None = None


class CandidateProfile(BaseModel):
    """
    Canonical, format-agnostic candidate profile with verified evidence graph.
    Authoritative semantic representation of any candidate resume.
    """
    personal: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    experience: list[WorkExperienceEntity] = Field(default_factory=list)
    internships: list[WorkExperienceEntity] = Field(default_factory=list)
    projects: list[ProjectEntity] = Field(default_factory=list)
    education: list[EducationEntity] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    skills_explicit: list[str] = Field(default_factory=list)
    skills_inferred: list[str] = Field(default_factory=list)
    skills_categorized: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    research: list[str] = Field(default_factory=list)
    leadership: list[str] = Field(default_factory=list)
    volunteer: list[str] = Field(default_factory=list)
    side_quests: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    additional_sections: list[AdditionalSectionEntity] = Field(default_factory=list)
    evidence_units: list[EvidenceUnit] = Field(default_factory=list)

    @property
    def identity(self) -> Any:
        class IdentityProxy:
            def __init__(self, data: dict):
                self._data = data or {}
            def __getattr__(self, name):
                return self._data.get(name)
            def __getitem__(self, name):
                return self._data.get(name)
            def __contains__(self, name):
                return name in self._data
            def get(self, name, default=None):
                return self._data.get(name, default)
        return IdentityProxy(self.personal)

    @property
    def name(self) -> str:
        return self.personal.get("name", "")

    @property
    def professional_experience(self) -> list[WorkExperienceEntity]:
        return self.experience

    @professional_experience.setter
    def professional_experience(self, val: list[WorkExperienceEntity]) -> None:
        self.experience = val

    @property
    def contact(self) -> Any:
        return self.identity

    def get_evidence_by_id(self, evidence_id: str) -> EvidenceUnit | None:
        for ev in self.evidence_units:
            if ev.id == evidence_id:
                return ev
        return None

    def find_evidence_units(
        self,
        section: str | None = None,
        entity_id: str | None = None,
    ) -> list[EvidenceUnit]:
        results = []
        for ev in self.evidence_units:
            if section and ev.section.upper() != section.upper():
                continue
            if entity_id and ev.entity_id != entity_id:
                continue
            results.append(ev)
        return results

    def to_parsed_dict(self) -> dict[str, Any]:
        """
        Converts canonical profile into the exact backward-compatible dictionary format
        expected by master_parsed, export, matching, and tailoring.
        """
        exp_raw: list[str] = []
        for exp in self.experience:
            if exp.progression and len(exp.progression) > 1:
                # Multi-role progression under the same company
                exp_raw.append(exp.company)
                for p in exp.progression:
                    p_str = f"{p.title} ({p.dates})" if p.dates else p.title
                    exp_raw.append(p_str)
                    for b in p.bullets:
                        exp_raw.append(b)
                if exp.location:
                    exp_raw.append(exp.location)
            else:
                header_parts = []
                is_dummy_company = not exp.company or exp.company.lower() in ("work experience", "company")
                if not is_dummy_company and exp.role:
                    header_parts.append(f"{exp.role} at {exp.company}")
                elif not is_dummy_company:
                    header_parts.append(exp.company)
                elif exp.role and (exp.dates or exp.location):
                    header_parts.append(exp.role)

                if exp.dates:
                    header_parts.append(f"({exp.dates})")
                if exp.location:
                    header_parts.append(f"- {exp.location}")
                if header_parts:
                    exp_raw.append(" ".join(header_parts))

            if exp.responsibility_groups:
                for grp in exp.responsibility_groups:
                    if grp.heading:
                        exp_raw.append(grp.heading)
                    for b in grp.bullets:
                        exp_raw.append(b)
            else:
                for b in exp.bullets:
                    exp_raw.append(b)

        proj_raw: list[dict[str, Any]] = []
        for p in self.projects:
            proj_dict: dict[str, Any] = {
                "title": p.title,
                "tech_stack": p.tech_stack,
                "technologies": p.technologies,
                "bullets": p.bullets,
            }
            if p.dates:
                proj_dict["dates"] = p.dates
            proj_raw.append(proj_dict)

        edu_raw: list[dict[str, Any]] = []
        for e in self.education:
            edu_raw.append({
                "institution": e.institution,
                "degree": e.degree,
                "dates": e.dates or "",
                "location": e.location or "",
                "cgpa": e.gpa or "",
            })

        return {
            "personal": dict(self.personal),
            "summary": self.summary,
            "skills": list(self.skills),
            "skills_explicit": list(self.skills_explicit),
            "skills_inferred": list(self.skills_inferred),
            "skills_categorized": list(self.skills_categorized),
            "experience": [e.model_dump() if hasattr(e, "model_dump") else dict(e) for e in self.experience],
            "experience_raw": exp_raw if exp_raw else [b for exp in self.experience for b in exp.bullets],
            "internships": [e.model_dump() if hasattr(e, "model_dump") else dict(e) for e in self.internships],
            "internships_raw": [b for intern in self.internships for b in intern.bullets],
            "projects": [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in self.projects],
            "projects_raw": proj_raw,
            "education": [e.model_dump() if hasattr(e, "model_dump") else dict(e) for e in self.education],
            "education_raw": edu_raw,
            "evidence_units": [ev.model_dump() if hasattr(ev, "model_dump") else dict(ev) for ev in self.evidence_units],
            "certifications": list(self.certifications),
            "achievements": list(self.achievements),
            "publications": list(self.publications),
            "research": list(self.research),
            "leadership": list(self.leadership),
            "volunteer": list(self.volunteer),
            "side_quests": list(self.side_quests),
            "languages": list(self.languages),
            "links": list(self.links),
            "additional_sections": [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in self.additional_sections],
        }

    def to_dict(self) -> dict[str, Any]:
        """Alias for to_parsed_dict."""
        return self.to_parsed_dict()

    @classmethod
    def from_parsed_dict(cls, data: dict[str, Any], raw_text: str = "") -> "CandidateProfile":
        """
        Constructs a canonical CandidateProfile from an existing parsed dictionary,
        generating structured entities and EvidenceUnits with stable semantic IDs.
        """
        from app.modules.jobs.skill_vocabulary import extract_skills_from_text
        from app.modules.resume.metrics import extract_quantified_metrics

        evidence_units: list[EvidenceUnit] = []
        seen_evidence_ids: set[str] = set()

        def make_unique_id(base_id: str) -> str:
            if base_id not in seen_evidence_ids:
                seen_evidence_ids.add(base_id)
                return base_id
            counter = 2
            while f"{base_id}_{counter}" in seen_evidence_ids:
                counter += 1
            unique_id = f"{base_id}_{counter}"
            seen_evidence_ids.add(unique_id)
            return unique_id

        # 0. Summary Evidence Unit
        if data.get("summary"):
            s_text = str(data["summary"]).strip()
            if s_text:
                sum_ev = EvidenceUnit(
                    id=make_unique_id("SUM_001"),
                    section="SUMMARY",
                    entity_id="summary",
                    original_text=s_text,
                    normalized_text=s_text,
                    claim_type=ClaimType.RESPONSIBILITY,
                    technologies=list(extract_skills_from_text(s_text)),
                    metrics=extract_quantified_metrics(s_text),
                    source_reference=s_text,
                )
                evidence_units.append(sum_ev)

        # 1. Ingest Experience Entities
        raw_exp = data.get("experience_entities") or data.get("experience") or []
        exp_entities: list[WorkExperienceEntity] = []
        if raw_exp:
            for item in raw_exp:
                if isinstance(item, WorkExperienceEntity):
                    exp_entities.append(item)
                elif isinstance(item, dict):
                    exp_entities.append(WorkExperienceEntity.model_validate(item))
        elif data.get("experience_raw"):
            from app.modules.resume.parsing.structurer import parse_experience_section
            exp_entities = parse_experience_section(data["experience_raw"])

        for exp in exp_entities:
            all_exp_bullets = []
            exp.evidence_units = []
            seen_exp_bullets: set[str] = set()

            # A. Responsibility Groups
            if exp.responsibility_groups:
                for grp in exp.responsibility_groups:
                    grp.evidence_units = []
                    grp_bullets = []
                    for b_idx, bullet in enumerate(grp.bullets):
                        b_stripped = bullet.strip()
                        if not b_stripped or b_stripped in seen_exp_bullets:
                            continue
                        ev_id = make_unique_id(generate_stable_evidence_id("EXPERIENCE", exp.company, grp.heading, b_idx + 1))
                        metrics = extract_quantified_metrics(bullet)
                        techs = list(extract_skills_from_text(bullet))
                        claim_type = ClaimType.METRIC if metrics else (ClaimType.LEADERSHIP if any(w in bullet.lower().split() for w in ["led", "managed", "spearheaded", "directed"]) else ClaimType.DELIVERY)
                        ev = EvidenceUnit(
                            id=ev_id,
                            section="EXPERIENCE",
                            entity_id=exp.id,
                            original_text=bullet,
                            normalized_text=bullet,
                            claim_type=claim_type,
                            technologies=techs,
                            metrics=metrics,
                            source_reference=bullet,
                        )
                        evidence_units.append(ev)
                        grp.evidence_units.append(ev)
                        exp.evidence_units.append(ev)
                        grp_bullets.append(bullet)
                        all_exp_bullets.append(bullet)
                        seen_exp_bullets.add(b_stripped)
                    grp.bullets = grp_bullets

            # B. Role Progression (Multiple roles under single employer)
            if exp.progression:
                for prog_idx, prog in enumerate(exp.progression):
                    prog.evidence_units = []
                    prog_bullets = []
                    for b_idx, bullet in enumerate(prog.bullets):
                        b_stripped = bullet.strip()
                        if not b_stripped or b_stripped in seen_exp_bullets:
                            continue
                        ev_id = make_unique_id(generate_stable_evidence_id("EXPERIENCE", exp.company, prog.title or exp.role, b_idx + 1))
                        metrics = extract_quantified_metrics(bullet)
                        techs = list(extract_skills_from_text(bullet))
                        claim_type = ClaimType.METRIC if metrics else (ClaimType.LEADERSHIP if any(w in bullet.lower().split() for w in ["led", "managed", "spearheaded", "directed"]) else ClaimType.DELIVERY)
                        ev = EvidenceUnit(
                            id=ev_id,
                            section="EXPERIENCE",
                            entity_id=exp.id,
                            original_text=bullet,
                            normalized_text=bullet,
                            claim_type=claim_type,
                            technologies=techs,
                            metrics=metrics,
                            source_reference=bullet,
                        )
                        evidence_units.append(ev)
                        prog.evidence_units.append(ev)
                        exp.evidence_units.append(ev)
                        prog_bullets.append(bullet)
                        all_exp_bullets.append(bullet)
                        seen_exp_bullets.add(b_stripped)
                    prog.bullets = prog_bullets

            # C. Direct Experience Bullets
            for b_idx, bullet in enumerate(exp.bullets):
                b_stripped = bullet.strip()
                if not b_stripped or b_stripped in seen_exp_bullets:
                    continue
                ev_id = make_unique_id(generate_stable_evidence_id("EXPERIENCE", exp.company, exp.role, b_idx + 1))
                metrics = extract_quantified_metrics(bullet)
                techs = list(extract_skills_from_text(bullet))
                claim_type = ClaimType.METRIC if metrics else (ClaimType.LEADERSHIP if any(w in bullet.lower().split() for w in ["led", "managed", "spearheaded", "directed"]) else ClaimType.DELIVERY)
                ev = EvidenceUnit(
                    id=ev_id,
                    section="EXPERIENCE",
                    entity_id=exp.id,
                    original_text=bullet,
                    normalized_text=bullet,
                    claim_type=claim_type,
                    technologies=techs,
                    metrics=metrics,
                    source_reference=bullet,
                )
                evidence_units.append(ev)
                exp.evidence_units.append(ev)
                all_exp_bullets.append(bullet)
                seen_exp_bullets.add(b_stripped)

            exp.bullets = list(all_exp_bullets) if all_exp_bullets else exp.bullets
            exp.technologies = list(extract_skills_from_text(" ".join(exp.bullets)))

        # 1b. Ingest Internship Entities
        raw_intern = data.get("internships_entities") or data.get("internships") or []
        intern_entities: list[WorkExperienceEntity] = []
        if raw_intern:
            for item in raw_intern:
                if isinstance(item, WorkExperienceEntity):
                    intern_entities.append(item)
                elif isinstance(item, dict):
                    intern_entities.append(WorkExperienceEntity.model_validate(item))
        elif data.get("internships_raw"):
            from app.modules.resume.parsing.structurer import parse_experience_section
            intern_entities = parse_experience_section(data["internships_raw"])

        for intern in intern_entities:
            intern.evidence_units = []
            for b_idx, bullet in enumerate(intern.bullets):
                b_clean = bullet.strip()
                if not b_clean:
                    continue
                ev_id = make_unique_id(generate_stable_evidence_id("INTERNSHIP", intern.company, intern.role, b_idx + 1))
                metrics = extract_quantified_metrics(b_clean)
                techs = list(extract_skills_from_text(b_clean))
                ev = EvidenceUnit(
                    id=ev_id,
                    section="INTERNSHIPS",
                    entity_id=intern.id,
                    original_text=b_clean,
                    normalized_text=b_clean,
                    claim_type=ClaimType.METRIC if metrics else ClaimType.DELIVERY,
                    technologies=techs,
                    metrics=metrics,
                    source_reference=b_clean,
                )
                evidence_units.append(ev)
                intern.evidence_units.append(ev)
            intern.technologies = list(extract_skills_from_text(" ".join(intern.bullets)))

        # 2. Ingest Project Entities
        raw_proj = data.get("projects_entities") or data.get("projects") or []
        proj_entities: list[ProjectEntity] = []
        if raw_proj and isinstance(raw_proj[0], (ProjectEntity, dict)) and not (isinstance(raw_proj[0], dict) and "bullets" in raw_proj[0] and "title" not in raw_proj[0]):
            for item in raw_proj:
                if isinstance(item, ProjectEntity):
                    proj_entities.append(item)
                elif isinstance(item, dict):
                    proj_entities.append(ProjectEntity.model_validate(item))
            for pe in proj_entities:
                pe.evidence_units = []
                for b_idx, bullet in enumerate(pe.bullets):
                    ev_id = make_unique_id(generate_stable_evidence_id("PROJECTS", pe.title, "", b_idx + 1))
                    metrics = extract_quantified_metrics(bullet)
                    b_techs = list(extract_skills_from_text(bullet))
                    ev = EvidenceUnit(
                        id=ev_id,
                        section="PROJECTS",
                        entity_id=pe.id,
                        original_text=bullet,
                        normalized_text=bullet,
                        claim_type=ClaimType.METRIC if metrics else ClaimType.DELIVERY,
                        technologies=b_techs,
                        metrics=metrics,
                        source_reference=bullet,
                    )
                    evidence_units.append(ev)
                    pe.evidence_units.append(ev)
                pe.technologies = list(extract_skills_from_text((pe.tech_stack or "") + " " + " ".join(pe.bullets)))
        else:
            from app.modules.resume.parsing.structurer import parse_projects_section
            proj_raw_list = data.get("projects_raw") or []
            if proj_raw_list and isinstance(proj_raw_list[0], dict):
                for p_idx, p in enumerate(proj_raw_list):
                    p_title = p.get("title") or f"Project {len(proj_entities)+1}"
                    p_tech = p.get("tech_stack") or p.get("technologies")
                    p_tech_str = ", ".join(p_tech) if isinstance(p_tech, list) else (str(p_tech) if p_tech else "")
                    p_bullets = [str(b).strip() for b in p.get("bullets", []) if str(b).strip()]
                    p_dates = p.get("dates")
                    proj_id = f"proj_{len(proj_entities)}"
                    p_techs = list(set(list(extract_skills_from_text(p_tech_str + " " + " ".join(p_bullets)))))
                    ev_list = []
                    for b_idx, bullet in enumerate(p_bullets):
                        ev_id = make_unique_id(generate_stable_evidence_id("PROJECTS", p_title, "", b_idx + 1))
                        metrics = extract_quantified_metrics(bullet)
                        b_techs = list(extract_skills_from_text(bullet))
                        ev = EvidenceUnit(
                            id=ev_id,
                            section="PROJECTS",
                            entity_id=proj_id,
                            original_text=bullet,
                            normalized_text=bullet,
                            claim_type=ClaimType.METRIC if metrics else ClaimType.DELIVERY,
                            technologies=b_techs,
                            metrics=metrics,
                            source_reference=bullet,
                        )
                        evidence_units.append(ev)
                        ev_list.append(ev)
                    proj_entities.append(ProjectEntity(
                        id=proj_id,
                        title=p_title,
                        tech_stack=p_tech_str or None,
                        technologies=p_techs,
                        dates=p_dates,
                        bullets=p_bullets,
                        evidence_units=ev_list,
                    ))
            else:
                proj_entities = parse_projects_section(proj_raw_list)
                for pe in proj_entities:
                    pe.evidence_units = []
                    for b_idx, bullet in enumerate(pe.bullets):
                        ev_id = make_unique_id(generate_stable_evidence_id("PROJECTS", pe.title, "", b_idx + 1))
                        metrics = extract_quantified_metrics(bullet)
                        b_techs = list(extract_skills_from_text(bullet))
                        ev = EvidenceUnit(
                            id=ev_id,
                            section="PROJECTS",
                            entity_id=pe.id,
                            original_text=bullet,
                            normalized_text=bullet,
                            claim_type=ClaimType.METRIC if metrics else ClaimType.DELIVERY,
                            technologies=b_techs,
                            metrics=metrics,
                            source_reference=bullet,
                        )
                        evidence_units.append(ev)
                        pe.evidence_units.append(ev)

        # 3. Ingest Education Entities
        raw_edu = data.get("education_entities") or data.get("education") or []
        edu_entities: list[EducationEntity] = []
        if raw_edu:
            for item in raw_edu:
                if isinstance(item, EducationEntity):
                    edu_entities.append(item)
                elif isinstance(item, dict):
                    edu_entities.append(EducationEntity.model_validate(item))
        elif data.get("education_raw"):
            from app.modules.resume.parsing.structurer import parse_education_section
            raw_edu_list = data.get("education_raw", [])
            if raw_edu_list and isinstance(raw_edu_list[0], dict):
                for e_idx, e in enumerate(raw_edu_list):
                    edu_entities.append(EducationEntity(
                        id=f"edu_{e_idx}",
                        institution=e.get("institution") or "Institution",
                        degree=e.get("degree") or "Degree",
                        dates=e.get("dates") or e.get("year"),
                        location=e.get("location"),
                        gpa=e.get("cgpa") or e.get("gpa") or e.get("percentage"),
                    ))
            else:
                edu_entities = parse_education_section(raw_edu_list)

        # 4. Ingest Additional Sections
        add_sections: list[AdditionalSectionEntity] = []
        for a_idx, a in enumerate(data.get("additional_sections", [])):
            if isinstance(a, AdditionalSectionEntity):
                add_sections.append(a)
            elif isinstance(a, dict):
                heading = a.get("heading") or f"Section {a_idx+1}"
                items = a.get("items") or []
                text_content = a.get("text") or ""
                sec_id = a.get("id") or f"add_sec_{a_idx}"
                ev_list = []
                for it_idx, item in enumerate(items):
                    ev_id = make_unique_id(generate_stable_evidence_id("ADDITIONAL", heading, "", it_idx + 1))
                    ev = EvidenceUnit(
                        id=ev_id,
                        section="ADDITIONAL",
                        entity_id=sec_id,
                        original_text=item,
                        normalized_text=item,
                        claim_type=ClaimType.DELIVERY,
                        technologies=list(extract_skills_from_text(item)),
                        metrics=extract_quantified_metrics(item),
                        source_reference=item,
                        source_location=f"ADDITIONAL: {heading}",
                    )
                    evidence_units.append(ev)
                    ev_list.append(ev)
                add_sections.append(AdditionalSectionEntity(
                    id=sec_id,
                    heading=heading,
                    semantic_type=a.get("semantic_type", "UNKNOWN"),
                    items=items,
                    text=text_content,
                    evidence_units=ev_list,
                ))

        skills_explicit = list(data.get("skills_explicit") or data.get("skills") or [])
        skills_inferred = list(data.get("skills_inferred") or [])
        skills_all = list(data.get("skills") or skills_explicit)

        return cls(
            personal=data.get("personal", {}),
            summary=data.get("summary"),
            experience=exp_entities,
            internships=intern_entities,
            projects=proj_entities,
            education=edu_entities,
            skills=skills_all,
            skills_explicit=skills_explicit,
            skills_inferred=skills_inferred,
            skills_categorized=data.get("skills_categorized", []),
            certifications=data.get("certifications", []),
            achievements=data.get("achievements", []),
            publications=data.get("publications", []),
            research=data.get("research", []),
            leadership=data.get("leadership", []),
            volunteer=data.get("volunteer", []),
            side_quests=data.get("side_quests", []),
            languages=data.get("languages", []),
            links=data.get("links", []),
            additional_sections=add_sections,
            evidence_units=evidence_units,
        )
