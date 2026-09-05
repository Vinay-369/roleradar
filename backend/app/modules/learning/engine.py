"""
Skill Gap Analysis + Learning Roadmap (Features 16, 17). Deterministic
on top of the matching engine's existing skill_match detail — no
separate AI call needed, per Feature 28 (don't call the LLM for work
plain code + already-computed data can do).

Priority classification:
  CORE      -> required skill, no evidence at all (matching engine's "missing")
  SECONDARY -> required skill, semantically close evidence exists (matching
               engine's "partial") -- closer to done, still needs work
  BONUS     -> nice-to-have skill not required but would strengthen fit
"""
from dataclasses import dataclass, field
from typing import Any

from app.modules.learning.skill_resources import get_resources_for_skill

PRIORITY_ESTIMATED_DAYS = {"CORE": 10, "SECONDARY": 5, "BONUS": 3}


@dataclass
class SkillGap:
    skill: str
    priority: str  # CORE | SECONDARY | BONUS
    reason: str
    target_job_title: str
    current_evidence: str  # MISSING | PARTIAL | MARKET_REQUIREMENT | DEMONSTRATED
    resources: list[str] = field(default_factory=list)
    project_suggestion: str = ""
    estimated_days: int = 5
    candidate_status: str | None = None  # MATCHED | PARTIAL | RELATED | MISSING | None
    source: str = "ROLE_TAXONOMY"
    confidence: str = "HIGH"
    domain: str | None = None
    subdomain: str | None = None
    # Phase 16D Canonical Career Skill Intelligence fields
    tier: str = "CORE"
    status: str = "NO_RESUME_EVIDENCE"
    importance: str = "CORE"
    evidence: list[dict] = field(default_factory=list)
    explanation: str = ""
    evidence_type: str = "NONE"


DOMAIN_PRACTICE_TEMPLATES: dict[str, str] = {
    "Healthcare": "Work through a clinical simulation, protocol exercise, or patient care scenario applying {skill}.",
    "Pharmaceutical / Life Sciences": "Complete a study protocol analysis, regulatory documentation exercise, or clinical data audit applying {skill}.",
    "Finance / Accounting": "Complete a financial case study, ledger reconciliation, or valuation model demonstrating {skill}.",
    "Education": "Create a lesson plan, curriculum unit, or instructional activity demonstrating {skill}.",
    "Design": "Create a design case study or interactive prototype demonstrating {skill}.",
    "Architecture / Construction": "Draft a site coordination plan, architectural detail sheet, or BIM model incorporating {skill}.",
    "Marketing": "Develop a targeted marketing campaign proposal or analytics audit demonstrating {skill}.",
    "Sales / Business Development": "Prepare a discovery pitch, deal negotiation strategy, or account review utilizing {skill}.",
    "HR / People": "Work through an employee relations case study, talent sourcing plan, or policy workflow utilizing {skill}.",
    "Legal / Compliance": "Analyze a regulatory compliance scenario, contract review exercise, or statutory audit applying {skill}.",
    "Operations / Supply Chain": "Complete an inventory optimization, procurement analysis, or logistics workflow case study applying {skill}.",
    "Consulting": "Develop a client advisory framework, strategic business case, or executive brief utilizing {skill}.",
    "Engineering": "Complete a technical design calculation, CAD/FEA simulation, or engineering schematic applying {skill}.",
    "Manufacturing": "Design a process control sheet, quality inspection plan (FMEA/SPC), or production workflow utilizing {skill}.",
    "Research / Academia": "Formulate a research methodology proposal, experimental protocol, or literature analysis utilizing {skill}.",
    "Media / Creative": "Produce an edited creative piece, narrative storyboard, or media asset demonstrating {skill}.",
    "Hospitality / Travel": "Work through an operational service scenario, guest resolution workflow, or facility audit applying {skill}.",
    "Cybersecurity": "Complete a security assessment, packet analysis lab, or threat mitigation simulation applying {skill}.",
    "Cloud / DevOps / Infrastructure": "Deploy an automated infrastructure script, CI/CD pipeline, or containerized service applying {skill}.",
    "AI / Machine Learning": "Train and evaluate an ML model on a real-world dataset, documenting performance metrics for {skill}.",
    "Data & Analytics": "Perform an exploratory analysis on a realistic dataset and build a decision-support dashboard for {skill}.",
    "Software Engineering": "Build a hands-on application module or service that implements {skill} with tests and documentation.",
    "Product": "Write a product requirements document (PRD), user story map, or discovery brief centered on {skill}.",
    "Project Management": "Draft a project charter, work breakdown structure (WBS), or risk mitigation register applying {skill}.",
}


def _project_suggestion(skill: str, domain: str | None = None) -> str:
    if domain and domain in DOMAIN_PRACTICE_TEMPLATES:
        return DOMAIN_PRACTICE_TEMPLATES[domain].format(skill=skill)
    if domain:
        dom_lower = domain.lower()
        for d_key, template in DOMAIN_PRACTICE_TEMPLATES.items():
            if d_key.lower() in dom_lower or dom_lower in d_key.lower():
                return template.format(skill=skill)
    return f"Complete a practical applied exercise or case study demonstrating {skill} with measurable results."


# ---------------------------------------------------------------------------
# Declarative Prerequisite Registry
# (Prerequisite Skill / Foundation, Dependent Advanced Competency)
# ---------------------------------------------------------------------------
PREREQUISITE_DEPENDENCIES: list[tuple[str, str]] = [
    # Programming & Scripting -> Applications / Advanced
    ("python", "predictive machine learning"),
    ("python", "statistical modeling & hypothesis testing"),
    ("python", "statistical modeling"),
    ("python", "feature engineering"),
    ("python", "machine learning"),
    ("python", "deep learning"),
    ("python", "data wrangling"),
    ("python", "ml pipeline engineering"),
    ("python", "supervised & unsupervised modeling"),
    ("python", "computer vision"),
    ("python", "natural language processing"),
    ("python", "fastapi"),
    ("python", "django"),
    
    # Data & Querying -> Advanced Analytics & Modeling
    ("sql", "data wrangling"),
    ("sql", "database modeling & querying"),
    ("sql", "database modeling"),
    ("sql", "etl/elt pipeline development"),
    ("sql", "data warehouse modeling"),
    ("sql", "predictive machine learning"),
    
    # Web Foundations -> Frameworks & State
    ("html5", "react"),
    ("css3", "responsive design"),
    ("javascript", "react"),
    ("javascript", "vue"),
    ("javascript", "angular"),
    ("javascript", "typescript"),
    ("react", "state management"),
    ("react", "next.js"),
    
    # Systems & Infrastructure
    ("linux", "cloud infrastructure configuration"),
    ("linux", "kubernetes"),
    ("linux", "docker"),
    ("docker", "containerization & orchestration"),
    ("docker", "kubernetes"),
    ("containerization basics", "microservices architecture"),
    ("git", "ci/cd pipelines"),
    ("git & version control", "ci/cd pipelines"),
    ("git", "github actions"),
    
    # Core CS & Architecture
    ("data structures & algorithms", "system design"),
    ("object-oriented programming", "system design"),
    ("rest apis", "microservices architecture"),
    ("restful api design", "microservices architecture"),
    
    # Data Science / ML Foundations
    ("statistics", "predictive machine learning"),
    ("statistical modeling & hypothesis testing", "predictive machine learning"),
    ("data wrangling", "feature engineering"),
    ("predictive machine learning", "model evaluation metrics"),
    ("predictive machine learning", "model evaluation & drift monitoring"),
    ("predictive machine learning", "model serving & inference apis"),
    
    # Finance / Accounting Foundations
    ("double-entry bookkeeping", "general ledger maintenance"),
    ("general ledger maintenance", "financial statement preparation"),
    ("general ledger maintenance", "month-end & year-end closing"),
    ("financial modeling", "capital expenditure evaluation"),
    ("budgeting & forecasting", "variance & trend analysis"),
    
    # Healthcare / Clinical
    ("patient assessment & triage", "care plan formulation & execution"),
    ("vital signs monitoring", "decompensation detection"),
    
    # Physical Engineering
    ("3d cad modeling", "finite element analysis (fea)"),
    ("circuit design & schematic capture", "pcb layout & routing"),
    ("kinematics & dynamics modeling", "motion planning & trajectory generation"),
]


def _order_skills_with_prerequisites(gaps: list[SkillGap]) -> list[str]:
    """
    Sorts learning gap skills by honoring prerequisite dependencies while preserving
    priority significance (CORE > SECONDARY > BONUS).

    If Skill A is a prerequisite of Skill B, Skill A is guaranteed to be scheduled
    before Skill B, even if Skill A was classified as SECONDARY and Skill B as CORE.
    """
    if not gaps:
        return []

    # Map unique skill name to its best (highest) priority gap
    priority_ranks = {"CORE": 0, "SECONDARY": 1, "BONUS": 2}
    unique_skills: dict[str, SkillGap] = {}
    for g in gaps:
        if g.skill not in unique_skills:
            unique_skills[g.skill] = g
        else:
            # Keep higher priority
            if priority_ranks.get(g.priority, 3) < priority_ranks.get(unique_skills[g.skill].priority, 3):
                unique_skills[g.skill] = g

    skill_list = list(unique_skills.keys())
    skill_lower_map = {s.lower().strip(): s for s in skill_list}

    # Build directed graph edges: prereq -> dep
    dependents: dict[str, list[str]] = {s: [] for s in skill_list}
    in_degree: dict[str, int] = {s: 0 for s in skill_list}

    for p_pat, d_pat in PREREQUISITE_DEPENDENCIES:
        p_matches = [orig for low, orig in skill_lower_map.items() if p_pat in low]
        d_matches = [orig for low, orig in skill_lower_map.items() if d_pat in low]

        for p_match in p_matches:
            for d_match in d_matches:
                if p_match != d_match and d_match not in dependents[p_match]:
                    dependents[p_match].append(d_match)
                    in_degree[d_match] += 1

    # Topological sort prioritizing CORE > SECONDARY > BONUS, stable by original order
    available = [s for s in skill_list if in_degree[s] == 0]
    ordered: list[str] = []

    def sort_key(s: str) -> tuple[int, int, int]:
        # If this skill is an unmet prerequisite for a CORE skill, its scheduling urgency
        # is elevated to 0 so foundations precede downstream core methodologies.
        unlocks_core = any(unique_skills[dep].priority == "CORE" for dep in dependents[s])
        effective_p_rank = 0 if unlocks_core else priority_ranks.get(unique_skills[s].priority, 2)
        has_deps = len(dependents[s]) > 0
        return (effective_p_rank, 0 if has_deps else 1, skill_list.index(s))

    while available:
        available.sort(key=sort_key)
        chosen = available.pop(0)
        ordered.append(chosen)

        for dep in dependents[chosen]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                available.append(dep)

    # If any cycle prevented full sorting, append any remaining skills in priority order
    if len(ordered) < len(skill_list):
        remaining = [s for s in skill_list if s not in ordered]
        remaining.sort(key=sort_key)
        ordered.extend(remaining)

    return ordered


def compute_skill_gaps(
    missing_required: list[str],
    partial_required: list[str],
    missing_nice_to_have: list[str],
    job_title: str,
    is_market_benchmark: bool = False,
    source: str = "ROLE_TAXONOMY",
    confidence: str = "HIGH",
    domain: str | None = None,
    subdomain: str | None = None,
    candidate_status_map: dict[str, str] | None = None,
) -> list[SkillGap]:
    gaps: list[SkillGap] = []
    status_map = candidate_status_map or {}

    for skill in missing_required:
        if is_market_benchmark:
            reason = f"'{skill}' is commonly expected as a core competency for {job_title}."
            evidence = "MARKET_REQUIREMENT"
            cand_status = None
        else:
            reason = f"'{skill}' is a required skill for {job_title} and no evidence of it was found in your resume."
            evidence = "MISSING"
            cand_status = status_map.get(skill, "MISSING")

        gaps.append(SkillGap(
            skill=skill,
            priority="CORE",
            reason=reason,
            target_job_title=job_title,
            current_evidence=evidence,
            resources=get_resources_for_skill(skill),
            project_suggestion=_project_suggestion(skill, domain),
            estimated_days=PRIORITY_ESTIMATED_DAYS["CORE"],
            candidate_status=cand_status,
            source=source,
            confidence=confidence,
            domain=domain,
            subdomain=subdomain,
            tier="CORE",
            status="NO_RESUME_EVIDENCE",
            importance="CORE",
            evidence=[],
            explanation=reason,
            evidence_type="NONE",
        ))

    for skill in partial_required:
        if is_market_benchmark:
            reason = f"'{skill}' is a common competency expected for {job_title}."
            evidence = "MARKET_REQUIREMENT"
            cand_status = None
        else:
            reason = f"'{skill}' is required, and your resume shows related experience, but not this exact skill by name."
            evidence = "PARTIAL"
            cand_status = status_map.get(skill, "PARTIAL")

        gaps.append(SkillGap(
            skill=skill,
            priority="SECONDARY",
            reason=reason,
            target_job_title=job_title,
            current_evidence=evidence,
            resources=get_resources_for_skill(skill),
            project_suggestion=_project_suggestion(skill, domain),
            estimated_days=PRIORITY_ESTIMATED_DAYS["SECONDARY"],
            candidate_status=cand_status,
            source=source,
            confidence=confidence,
            domain=domain,
            subdomain=subdomain,
            tier="CORE",
            status="PARTIALLY_DEMONSTRATED",
            importance="CORE",
            evidence=[],
            explanation=reason,
            evidence_type="RELATED_TECHNOLOGY",
        ))

    for skill in missing_nice_to_have:
        if is_market_benchmark:
            reason = f"'{skill}' is an optional or specialized skill that strengthens your profile for {job_title}."
            evidence = "MARKET_REQUIREMENT"
            cand_status = None
        else:
            reason = f"'{skill}' isn't required for {job_title} but would strengthen your application."
            evidence = "MISSING"
            cand_status = status_map.get(skill, "MISSING")

        gaps.append(SkillGap(
            skill=skill,
            priority="BONUS",
            reason=reason,
            target_job_title=job_title,
            current_evidence=evidence,
            resources=get_resources_for_skill(skill),
            project_suggestion=_project_suggestion(skill, domain),
            estimated_days=PRIORITY_ESTIMATED_DAYS["BONUS"],
            candidate_status=cand_status,
            source=source,
            confidence=confidence,
            domain=domain,
            subdomain=subdomain,
            tier="ADVANCED",
            status="NO_RESUME_EVIDENCE",
            importance="OPTIONAL",
            evidence=[],
            explanation=reason,
            evidence_type="NONE",
        ))

    return gaps


def determine_competency_tier(skill: str, profile: Any = None) -> str:
    s_low = skill.lower().strip()
    
    # 1. Cloud & Specialization check
    cloud_keywords = [
        "aws", "gcp", "azure", "cloud", "kubernetes", "k8s", "terraform",
        "serverless", "distributed systems", "distributed data systems",
        "cloud infrastructure", "cloud deployment", "infrastructure as code",
        "container orchestration", "real-time streaming"
    ]
    if any(k in s_low for k in cloud_keywords):
        return "CLOUD_SPECIALIZATION"
        
    # 2. Concrete Tools & Technologies (e.g. Docker, PostgreSQL, React, FastAPI, Redis, etc.)
    if profile and getattr(profile, "tools_technologies", None) and any(s_low == t.lower() for t in profile.tools_technologies):
        if s_low not in {"python", "sql", "git", "linux", "html5", "css3", "javascript"}:
            return "TOOLS"

    # 3. Foundation check
    foundation_skills = {
        "python", "sql", "git", "git & version control", "version control",
        "linux", "bash", "html5", "css3", "javascript", "data structures",
        "algorithms", "data structures & algorithms", "object-oriented programming",
        "oop", "statistics", "mathematics", "linear algebra", "discrete math",
        "double-entry bookkeeping", "general ledger maintenance", "cad fundamentals"
    }
    if s_low in foundation_skills or any(k == s_low for k in foundation_skills):
        return "FOUNDATION"
    for prereq, _ in PREREQUISITE_DEPENDENCIES:
        if prereq == s_low and s_low in foundation_skills:
            return "FOUNDATION"
            
    # 4. Domain & Processing check
    domain_processing_skills = {
        "etl", "elt", "etl / elt", "etl/elt pipeline development", "data modeling",
        "dimensional modeling", "data warehouse", "data warehousing",
        "data warehouse modeling", "stream processing", "batch processing",
        "caching", "caching strategies", "message queues", "microservices architecture",
        "predictive machine learning", "feature engineering", "deep learning",
        "model evaluation", "model serving", "data wrangling", "system design"
    }
    if any(k in s_low for k in domain_processing_skills):
        return "DOMAIN_PROCESSING"
    if profile and getattr(profile, "knowledge_areas", None) and any(s_low == k.lower() for k in profile.knowledge_areas):
        return "DOMAIN_PROCESSING"
        
    # 5. Tools & Technologies fallback
    if profile and getattr(profile, "tools_technologies", None) and any(s_low == t.lower() for t in profile.tools_technologies):
        return "TOOLS"

    # 6. Core competencies check
    if profile and getattr(profile, "core_competencies", None) and any(s_low == c.lower() for c in profile.core_competencies):
        return "CORE"
        
    # 7. Optional competencies check
    if profile and getattr(profile, "optional_competencies", None) and any(s_low == o.lower() for o in profile.optional_competencies):
        return "ADVANCED"
        
    return "CORE"


def determine_competency_importance(skill: str, profile: Any = None) -> str:
    if not profile:
        return "CORE"
    s_low = skill.lower().strip()
    if getattr(profile, "core_competencies", None) and any(s_low == c.lower() for c in profile.core_competencies):
        return "CORE"
    if getattr(profile, "common_competencies", None) and any(s_low == c.lower() for c in profile.common_competencies):
        return "COMMON"
    if getattr(profile, "optional_competencies", None) and any(s_low == o.lower() for o in profile.optional_competencies):
        return "OPTIONAL"
    if getattr(profile, "tools_technologies", None) and any(s_low == t.lower() for t in profile.tools_technologies):
        return "COMMON"
    if getattr(profile, "knowledge_areas", None) and any(s_low == k.lower() for k in profile.knowledge_areas):
        return "COMMON"
    return "CORE"


def evaluate_career_competencies(
    profile: Any,
    candidate: Any = None,
    source: str = "ROLE_TAXONOMY",
    confidence: str = "HIGH",
) -> list[SkillGap]:
    """
    Phase 16D Canonical Career Competency Alignment Engine.
    
    Evaluates the complete authoritative role competency map for a canonical career:
    - FOUNDATION
    - CORE
    - DOMAIN_PROCESSING
    - TOOLS
    - CLOUD_SPECIALIZATION
    - ADVANCED
    
    Distinguishes:
    1. DEMONSTRATED (delivery evidence in experience/projects or verified explicit skill)
    2. PARTIALLY_DEMONSTRATED (coursework/education evidence or related adjacent technology)
    3. NO_RESUME_EVIDENCE (no evidence in resume, never implying the candidate does not know it)
    """
    import re
    from app.modules.matching.evidence_mapping import TECH_SYNONYMS, RELATED_SKILL_CLUSTERS

    # Ordered union of all competencies defined in the canonical role profile
    raw_competencies: list[str] = []
    seen: set[str] = set()

    for comp_list in [
        getattr(profile, "core_competencies", []),
        getattr(profile, "common_competencies", []),
        getattr(profile, "tools_technologies", []),
        getattr(profile, "knowledge_areas", []),
        getattr(profile, "optional_competencies", []),
    ]:
        for comp in (comp_list or []):
            c_clean = comp.strip()
            if c_clean and c_clean.lower() not in seen:
                seen.add(c_clean.lower())
                raw_competencies.append(c_clean)

    # Pre-extract candidate lookup structures if resume present
    exp_units = []
    proj_units = []
    edu_units = []
    skill_units = []
    candidate_skills_set = set()
    entity_name_lookup: dict[str, str] = {}

    if candidate is not None:
        for idx, p in enumerate(getattr(candidate, "projects", []) or []):
            title = getattr(p, "title", None) or getattr(p, "name", None)
            if title:
                entity_name_lookup[f"proj_{idx}"] = title
                p_id = getattr(p, "id", None)
                if p_id:
                    entity_name_lookup[p_id] = title

        for idx, e in enumerate(getattr(candidate, "experience", []) or []):
            company = getattr(e, "company", None) or getattr(e, "role", None)
            if company:
                entity_name_lookup[f"exp_{idx}"] = company
                e_id = getattr(e, "id", None)
                if e_id:
                    entity_name_lookup[e_id] = company

        for idx, ed in enumerate(getattr(candidate, "education", []) or []):
            inst = getattr(ed, "institution", None) or getattr(ed, "degree", None)
            if inst:
                entity_name_lookup[f"edu_{idx}"] = inst
                ed_id = getattr(ed, "id", None)
                if ed_id:
                    entity_name_lookup[ed_id] = inst

        candidate_skills_set = {
            s.lower().strip()
            for s in (getattr(candidate, "skills_explicit", None) or getattr(candidate, "skills", None) or [])
            if s and s.strip()
        }
        for ev in (getattr(candidate, "evidence_units", None) or []):
            sec = (getattr(ev, "section", "") or "").upper()
            claim_val = getattr(getattr(ev, "claim_type", None), "value", "")
            if sec == "EXPERIENCE" or claim_val in ("CORE_EXPERIENCE", "WORK_EXPERIENCE"):
                exp_units.append(ev)
            elif sec == "PROJECTS" or claim_val == "PROJECT_CONTRIBUTION":
                proj_units.append(ev)
            elif sec == "EDUCATION" or claim_val == "ACADEMIC_CREDENTIAL":
                edu_units.append(ev)
            elif sec == "SKILLS":
                skill_units.append(ev)
                for t in (getattr(ev, "technologies", None) or []):
                    candidate_skills_set.add(t.lower().strip())

    competencies: list[SkillGap] = []

    for comp in raw_competencies:
        tier = determine_competency_tier(comp, profile)
        importance = determine_competency_importance(comp, profile)
        priority = "CORE" if importance == "CORE" else ("SECONDARY" if importance == "COMMON" else "BONUS")
        estimated_days = PRIORITY_ESTIMATED_DAYS.get(priority, 5)

        # ----------------------------------------------------------------------
        # MODE A: NO RESUME AVAILABLE
        # ----------------------------------------------------------------------
        if candidate is None:
            competencies.append(SkillGap(
                skill=comp,
                priority=priority,
                reason=f"'{comp}' is commonly expected as a {tier.lower().replace('_', ' ')} competency for {profile.canonical_role}.",
                target_job_title=profile.canonical_role,
                current_evidence="MARKET_REQUIREMENT",
                resources=get_resources_for_skill(comp),
                project_suggestion=_project_suggestion(comp, profile.domain),
                estimated_days=estimated_days,
                candidate_status=None,
                source=source,
                confidence=confidence,
                domain=profile.domain,
                subdomain=profile.subdomain,
                tier=tier,
                status="NO_RESUME_EVIDENCE",
                importance=importance,
                evidence=[],
                explanation="Market benchmark requirement for this role.",
                evidence_type="NONE",
            ))
            continue

        # ----------------------------------------------------------------------
        # MODE B: RESUME PRESENT (EVIDENCE ALIGNMENT)
        # ----------------------------------------------------------------------
        c_low = comp.lower().strip()
        synonyms = set(TECH_SYNONYMS.get(c_low, set())) | {c_low}
        for part in re.split(r"&|/|\band\b", c_low):
            p_clean = part.strip()
            if len(p_clean) >= 3:
                synonyms.add(p_clean)
                synonyms.update(TECH_SYNONYMS.get(p_clean, set()))

        status = "NO_RESUME_EVIDENCE"
        evidence_type = "NONE"
        evidence_list: list[dict] = []
        explanation = "No resume evidence found"
        cand_status = "MISSING"
        current_evidence = "MISSING"

        # 1. Check Work Experience Delivery Evidence
        matched_exp = None
        for ev in exp_units:
            ev_techs = {t.lower().strip() for t in (getattr(ev, "technologies", None) or [])}
            ev_text = (getattr(ev, "normalized_text", None) or getattr(ev, "original_text", "") or "").lower()
            if any(syn in ev_techs or f" {syn} " in f" {ev_text} " or ev_text.startswith(f"{syn} ") or ev_text.endswith(f" {syn}") or syn == ev_text for syn in synonyms):
                matched_exp = ev
                break

        if matched_exp:
            status = "DEMONSTRATED"
            evidence_type = "WORK_EXPERIENCE"
            human_company = entity_name_lookup.get(matched_exp.entity_id, matched_exp.entity_id or "Work Experience")
            explanation = f"Demonstrated through work experience at {human_company}"
            evidence_list.append({
                "section": "EXPERIENCE",
                "entity_name": human_company,
                "text": matched_exp.normalized_text or matched_exp.original_text or comp,
                "evidence_type": "WORK_EXPERIENCE",
                "source_reference": getattr(matched_exp, "source_reference", None),
            })
            cand_status = "MATCHED"
            current_evidence = "DEMONSTRATED"

        # 2. Check Project Delivery Evidence
        if status == "NO_RESUME_EVIDENCE":
            matched_proj = None
            for ev in proj_units:
                ev_techs = {t.lower().strip() for t in (getattr(ev, "technologies", None) or [])}
                ev_text = (getattr(ev, "normalized_text", None) or getattr(ev, "original_text", "") or "").lower()
                if any(syn in ev_techs or f" {syn} " in f" {ev_text} " or ev_text.startswith(f"{syn} ") or ev_text.endswith(f" {syn}") or syn == ev_text for syn in synonyms):
                    matched_proj = ev
                    break

            if matched_proj:
                status = "DEMONSTRATED"
                evidence_type = "PROJECT"
                human_proj = entity_name_lookup.get(matched_proj.entity_id, matched_proj.entity_id or "Applied Project")
                explanation = f"Demonstrated through project '{human_proj}'"
                evidence_list.append({
                    "section": "PROJECTS",
                    "entity_name": human_proj,
                    "text": matched_proj.normalized_text or matched_proj.original_text or comp,
                    "evidence_type": "PROJECT",
                    "source_reference": getattr(matched_proj, "source_reference", None),
                })
                cand_status = "MATCHED"
                current_evidence = "DEMONSTRATED"

        # 3. Check Explicit Skills Qualification
        if status == "NO_RESUME_EVIDENCE":
            if any(syn in candidate_skills_set for syn in synonyms):
                status = "DEMONSTRATED"
                evidence_type = "EXPLICIT_SKILL"
                explanation = "Listed in verified resume skills qualification"
                evidence_list.append({
                    "section": "SKILLS",
                    "entity_name": "Skills",
                    "text": comp,
                    "evidence_type": "EXPLICIT_SKILL",
                    "source_reference": None,
                })
                cand_status = "MATCHED"
                current_evidence = "DEMONSTRATED"

        # 4. Check Academic / Coursework Evidence
        if status == "NO_RESUME_EVIDENCE":
            matched_edu = None
            for ev in edu_units:
                ev_techs = {t.lower().strip() for t in (getattr(ev, "technologies", None) or [])}
                ev_text = (getattr(ev, "normalized_text", None) or getattr(ev, "original_text", "") or "").lower()
                if any(syn in ev_techs or f" {syn} " in f" {ev_text} " or syn == ev_text for syn in synonyms):
                    matched_edu = ev
                    break

            if matched_edu:
                status = "PARTIALLY_DEMONSTRATED"
                evidence_type = "COURSEWORK"
                human_edu = entity_name_lookup.get(matched_edu.entity_id, matched_edu.entity_id or "Education")
                explanation = f"Supported by academic coursework / degree credentials ({human_edu})"
                evidence_list.append({
                    "section": "EDUCATION",
                    "entity_name": human_edu,
                    "text": matched_edu.normalized_text or matched_edu.original_text or comp,
                    "evidence_type": "COURSEWORK",
                    "source_reference": getattr(matched_edu, "source_reference", None),
                })
                cand_status = "PARTIAL"
                current_evidence = "PARTIAL"

        # 5. Check Related / Adjacent Technology Clusters
        if status == "NO_RESUME_EVIDENCE":
            related_candidates: set[str] = set()
            for cluster in RELATED_SKILL_CLUSTERS:
                if any(syn in cluster for syn in synonyms):
                    related_candidates.update(cluster - synonyms)

            matched_related = next((r for r in related_candidates if r.lower().strip() in candidate_skills_set), None)
            if matched_related:
                status = "PARTIALLY_DEMONSTRATED"
                evidence_type = "RELATED_TECHNOLOGY"
                explanation = f"Related technology '{matched_related.title()}' provides transferable foundation"
                evidence_list.append({
                    "section": "SKILLS",
                    "entity_name": "Related Skill",
                    "text": matched_related,
                    "evidence_type": "RELATED_TECHNOLOGY",
                    "source_reference": None,
                })
                cand_status = "PARTIAL"
                current_evidence = "PARTIAL"

        # Build honest human reason
        if status == "DEMONSTRATED":
            reason = f"'{comp}' is demonstrated on your resume ({explanation.lower()})."
        elif status == "PARTIALLY_DEMONSTRATED":
            reason = f"'{comp}' is partially demonstrated: {explanation}."
        else:
            reason = f"'{comp}' is expected for {profile.canonical_role}, but no verified evidence was found in your resume."

        effective_priority = "SECONDARY" if status == "PARTIALLY_DEMONSTRATED" else priority
        effective_days = PRIORITY_ESTIMATED_DAYS.get(effective_priority, 5)

        competencies.append(SkillGap(
            skill=comp,
            priority=effective_priority,
            reason=reason,
            target_job_title=profile.canonical_role,
            current_evidence=current_evidence,
            resources=get_resources_for_skill(comp),
            project_suggestion=_project_suggestion(comp, profile.domain),
            estimated_days=effective_days,
            candidate_status=cand_status,
            source=source,
            confidence=confidence,
            domain=profile.domain,
            subdomain=profile.subdomain,
            tier=tier,
            status=status,
            importance=importance,
            evidence=evidence_list,
            explanation=explanation,
            evidence_type=evidence_type,
        ))

    return competencies


def build_roadmap(gaps: list[SkillGap]) -> dict[str, list[str]]:
    """
    Feature 17: Immediate / 1 Week / 2 Weeks / 1 Month buckets.

    Uses prerequisite-aware topological ordering while front-loading highest-priority
    gaps. Foundational competencies (e.g. Python, SQL, Linux, Git) precede dependent
    advanced competencies (e.g. Machine Learning, System Design, Kubernetes).

    Phase 16D: Excludes DEMONSTRATED skills so students only study real gaps.
    Distributes ordered skills evenly across the 4 stages.
    """
    learning_eligible_gaps = [g for g in gaps if getattr(g, "status", None) != "DEMONSTRATED"]
    ordered_skills = _order_skills_with_prerequisites(learning_eligible_gaps)

    buckets: list[list[str]] = [[], [], [], []]
    if ordered_skills:
        total = len(ordered_skills)
        base = total // 4
        remainder = total % 4
        idx = 0
        for bucket_i in range(4):
            count = base + (1 if bucket_i < remainder else 0)
            buckets[bucket_i] = ordered_skills[idx: idx + count]
            idx += count

    return {
        "immediate": buckets[0],
        "week_1": buckets[1],
        "week_2": buckets[2],
        "month_1": buckets[3],
    }

