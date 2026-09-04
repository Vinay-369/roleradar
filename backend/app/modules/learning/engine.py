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

from app.modules.learning.skill_resources import get_resources_for_skill

PRIORITY_ESTIMATED_DAYS = {"CORE": 10, "SECONDARY": 5, "BONUS": 3}


@dataclass
class SkillGap:
    skill: str
    priority: str  # CORE | SECONDARY | BONUS
    reason: str
    target_job_title: str
    current_evidence: str  # MISSING | PARTIAL | MARKET_REQUIREMENT
    resources: list[str] = field(default_factory=list)
    project_suggestion: str = ""
    estimated_days: int = 5
    candidate_status: str | None = None  # MATCHED | PARTIAL | RELATED | MISSING | None
    source: str = "ROLE_TAXONOMY"
    confidence: str = "HIGH"
    domain: str | None = None
    subdomain: str | None = None


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
        ))

    return gaps


def build_roadmap(gaps: list[SkillGap]) -> dict[str, list[str]]:
    """
    Feature 17: Immediate / 1 Week / 2 Weeks / 1 Month buckets.

    Uses prerequisite-aware topological ordering while front-loading highest-priority
    gaps. Foundational competencies (e.g. Python, SQL, Linux, Git) precede dependent
    advanced competencies (e.g. Machine Learning, System Design, Kubernetes).

    Distributes ordered skills evenly across the 4 stages.
    """
    ordered_skills = _order_skills_with_prerequisites(gaps)

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

