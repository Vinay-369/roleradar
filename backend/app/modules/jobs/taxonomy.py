"""
Structured Job Description Taxonomy, Section Reconstruction, and Requirement Extraction.
Classifies JD requirements into MUST_HAVE, PREFERRED, RESPONSIBILITY, QUALIFICATION, DOMAIN, SOFT_SKILL.
Provides deterministic StructuredJobRequirements representation without mutating candidate evidence.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field

from app.modules.jobs.skill_vocabulary import extract_skills_from_text


class RequirementCategory(str, Enum):
    MUST_HAVE = "MUST_HAVE"
    PREFERRED = "PREFERRED"
    RESPONSIBILITY = "RESPONSIBILITY"
    QUALIFICATION = "QUALIFICATION"
    DOMAIN = "DOMAIN"
    SOFT_SKILL = "SOFT_SKILL"
    COMPANY_OVERVIEW = "COMPANY_OVERVIEW"
    ROLE_OVERVIEW = "ROLE_OVERVIEW"
    BENEFITS = "BENEFITS"
    EEO_LEGAL = "EEO_LEGAL"
    UNKNOWN = "UNKNOWN"


class JobRequirement(BaseModel):
    id: str
    category: RequirementCategory
    text: str
    skills_detected: list[str] = Field(default_factory=list)
    importance_weight: float = 1.0
    source_section: str = "UNKNOWN"
    source_heading: str | None = None
    raw_text: str | None = None
    normalized_text: str | None = None


class StructuredJobRequirements(BaseModel):
    target_role: str | None = None
    job_title: str | None = None
    company: str | None = None
    company_overview: str | None = None
    role_overview: str | None = None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    domain: str | None = None
    requirements: list[JobRequirement] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    experience_requirements: str | None = None
    min_years_experience: float | None = None
    max_years_experience: float | None = None
    behavioral_expectations: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    domain_terminology: list[str] = Field(default_factory=list)
    domain_keywords: list[str] = Field(default_factory=list)
    important_terminology: list[str] = Field(default_factory=list)


JDRequirements = StructuredJobRequirements

# Backward compatibility header regex lists
MUST_HAVE_HEADERS = [
    r"^\s*(?:requirements?|must\s+haves?|basic\s+qualifications?|minimum\s+qualifications?|what\s+you\s+need|core\s+requirements?|essential\s+skills?|what\s+we['’]?re\s+looking\s+for|what\s+you\s+bring|mandatory\s+requirements?|skills\s+required)\b",
]
PREFERRED_HEADERS = [
    r"^\s*(?:preferred\s+qualifications?|nice\s+to\s+haves?|bonus\s+points?|good\s+to\s+have|preferred\s+skills?|plus|desirable|bonus|desired\s+qualifications?|additional\s+qualifications?)\b",
]
RESPONSIBILITY_HEADERS = [
    r"^\s*(?:responsibilities|what\s+you['’]ll\s+do|what\s+you\s+will\s+do|duties|the\s+role|key\s+responsibilities|day\s+to\s+day|scope\s+of\s+work|your\s+mission|core\s+duties)\b",
]
QUALIFICATION_HEADERS = [
    r"^\s*(?:education\s+&\s+experience|qualifications?|eligibility|background|education|degree\s+requirements?|academic\s+background)\b",
]
DOMAIN_HEADERS = [
    r"^\s*(?:domain\s+knowledge|industry\s+background|about\s+the\s+domain|business\s+context|about\s+the\s+team)\b",
]

SOFT_SKILL_KEYWORDS = {
    "communication", "teamwork", "leadership", "problem solving", "collaboration",
    "analytical thinking", "adaptability", "critical thinking", "work ethic", "mentoring",
    "interpersonal", "presentation", "time management", "ownership", "curiosity",
    "attention to detail", "stakeholder management", "cross-functional",
}

KNOWN_TOOLS = {
    "docker", "kubernetes", "git", "github", "gitlab", "jenkins", "terraform",
    "ansible", "aws", "azure", "gcp", "jira", "postman", "linux", "figma",
    "grafana", "prometheus", "helm", "ci/cd", "circleci", "datadog", "splunk",
    "airflow", "kafka", "redis", "elasticsearch",
}

DOMAIN_TERMS = {
    "distributed systems", "microservices", "machine learning", "deep learning",
    "computer vision", "natural language processing", "nlp", "data engineering",
    "cloud infrastructure", "etl pipelines", "rest apis", "graphql",
    "event-driven architecture", "devops", "fintech", "cybersecurity", "saas",
    "frontend development", "backend development", "full stack", "generative ai",
    "large language models", "llms", "high-throughput", "low latency",
}

TITLE_ROLE_KEYWORDS = {
    "engineer", "developer", "architect", "scientist", "manager", "director",
    "lead", "analyst", "consultant", "specialist", "administrator", "designer",
    "programmer", "officer", "vp", "president", "head", "intern", "associate", "fellow"
}

WORK_MODES = {"remote", "hybrid", "on-site", "onsite", "in-office"}
JOB_TYPES = {"full-time", "part-time", "contract", "internship", "temporary", "freelance"}

_BULLET_PREFIX_RE = re.compile(
    r"^\s*(?:[•▪▫►▶◆◇●○✓✔➔→➢·∙\-\*–—]|\uf0b7|\uf0a7|\u2022|\u25aa|\u25b6|\u25c6|\u2713|\u27a4|\d+[\.\)]|[a-zA-Z][\.\)])\s*"
)
_EXP_PATTERN = re.compile(
    r"\b(?:minimum\s+(?:of\s+)?)?(\d+\+?(?:\s*(?:to|-)\s*\d+)?)\s*(?:years?|yrs?)(?:\s+of)?(?:\s+[\w\s,\/\-]{1,65})?\s+experience\b",
    re.IGNORECASE
)


def _normalize_heading_text(heading: str) -> str:
    """Normalizes raw heading string by stripping punctuation, extra spaces, and casing."""
    h = heading.strip().lower()
    h = re.sub(r"['’`]", "", h)
    h = re.sub(r"[:\-\*•\(\)\/&|]+", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def _detect_section_category(raw_line: str) -> tuple[RequirementCategory, str] | None:
    """
    Generalized semantic section heading recognition.
    Bullet lines and full requirement sentences are never treated as section headings.
    Tolerates hyphens, slashes, ampersands, colons, punctuation, and wording variations.
    """
    line_s = raw_line.strip()
    if not line_s:
        return None

    # Bulleted items are requirement content, never headings
    if _BULLET_PREFIX_RE.match(line_s):
        return None

    norm = _normalize_heading_text(line_s)
    if not norm or len(norm.split()) > 7:
        return None

    # Requirement phrasing predicates are not section headings
    if any(p in norm for p in ["years of", "years experience", "experience with", "production experience", "working knowledge of", "responsible for"]):
        return None

    # 1. EEO / Legal
    if any(k in norm for k in ["equal opportunity", "eeo statement", "diversity and inclusion", "diversity inclusion", "disclaimer", "affirmative action", "legal notices"]):
        return RequirementCategory.EEO_LEGAL, norm

    # 2. Benefits / Compensation
    if any(k in norm for k in ["benefits", "compensation", "what we offer", "perks", "total rewards", "salary range", "what you get"]):
        return RequirementCategory.BENEFITS, norm

    # 3. Role Overview (must check before generic company overview)
    if any(k in norm for k in ["role overview", "about the role", "job overview", "position overview", "job summary", "the opportunity", "position summary", "role summary", "about this role"]):
        return RequirementCategory.ROLE_OVERVIEW, norm

    # 4. Company Overview
    if any(k in norm for k in ["about us", "about the company", "company overview", "who we are", "our company", "our mission", "about "]) and not any(k in norm for k in ["role", "position", "job"]):
        return RequirementCategory.COMPANY_OVERVIEW, norm

    # 5. Preferred / Nice-to-Have (must check before required)
    if any(k in norm for k in [
        "preferred", "nice to have", "bonus", "good to have", "plus", "desirable", 
        "desired", "additional qualifications", "preferred qualifications", "preferred skills",
        "nice to haves", "bonus points", "what would make you stand out", "standout qualifications",
        "nice to have preferred"
    ]):
        return RequirementCategory.PREFERRED, norm

    # 6. Must-Have / Required
    if any(norm == k or norm.startswith(k + " ") or norm.endswith(" " + k) or f" {k} " in norm for k in [
        "requirements", "must have", "must haves", "basic qualifications", "minimum qualifications",
        "what you need", "core requirements", "essential skills", "what were looking for",
        "what we are looking for", "mandatory requirements", "required qualifications",
        "key requirements", "what you bring", "minimum requirements", "required skills",
        "skills required", "qualifications"
    ]):
        return RequirementCategory.MUST_HAVE, norm

    # 7. Responsibilities
    if any(norm == k or norm.startswith(k + " ") or norm.endswith(" " + k) or f" {k} " in norm for k in [
        "responsibilities", "what youll do", "what you will do", "duties", "the role",
        "key responsibilities", "day to day", "scope of work", "your mission", "core duties",
        "what you will be doing", "what youll be doing", "how youll make an impact"
    ]):
        return RequirementCategory.RESPONSIBILITY, norm

    # 8. Education / Qualifications
    if any(k in norm for k in ["education & experience", "education experience", "eligibility", "education requirements", "academic background"]):
        return RequirementCategory.QUALIFICATION, norm

    # 9. Domain Knowledge / Context
    if any(k in norm for k in ["domain knowledge", "industry background", "about the domain", "business context", "about the team"]):
        return RequirementCategory.DOMAIN, norm

    return None


def _extract_header_metadata(lines: list[str]) -> dict[str, str | None]:
    """Extracts job title, company, location, work mode, and employment type from header lines."""
    data: dict[str, str | None] = {
        "title": None,
        "company": None,
        "location": None,
        "work_mode": None,
        "employment_type": None,
    }

    for line in lines[:8]:
        line_s = line.strip()
        if not line_s:
            continue

        # Check inline work mode
        wm_m = re.search(r"\b(remote|hybrid|on-site|onsite|in-office)\b", line_s, re.IGNORECASE)
        if wm_m and not data["work_mode"]:
            val = wm_m.group(1).lower()
            if val == "onsite":
                val = "on-site"
            data["work_mode"] = val.capitalize()

        # Check inline employment type
        jt_m = re.search(r"\b(full-time|part-time|contract|internship|temporary|freelance)\b", line_s, re.IGNORECASE)
        if jt_m and not data["employment_type"]:
            val = jt_m.group(1).lower()
            if val == "full-time":
                data["employment_type"] = "Full-Time"
            elif val == "part-time":
                data["employment_type"] = "Part-Time"
            else:
                data["employment_type"] = val.capitalize()

        # 1. Pipe-separated header bar (e.g. "Acme Financial | New York, NY | Hybrid | Full-Time")
        if "|" in line_s:
            segments = [s.strip() for s in line_s.split("|") if s.strip()]
            for seg in segments:
                seg_low = seg.lower()
                if seg_low in WORK_MODES and not data["work_mode"]:
                    data["work_mode"] = seg.capitalize()
                elif seg_low in JOB_TYPES and not data["employment_type"]:
                    data["employment_type"] = "Full-Time" if seg_low == "full-time" else ("Part-Time" if seg_low == "part-time" else seg.capitalize())
                elif any(k in seg_low for k in TITLE_ROLE_KEYWORDS) and not data["title"]:
                    data["title"] = seg
                elif any(c in seg for c in [",", "NY", "CA", "TX", "MA", "FL", "WA", "Remote", "India", "UK", "US", "Bangalore", "London"]) and not data["location"] and seg_low not in WORK_MODES:
                    data["location"] = seg
                elif not data["company"] and len(seg.split()) <= 4:
                    data["company"] = seg
            continue

        # 2. Key-value labeled metadata (e.g. "Location: Bangalore, India / Hybrid")
        m_loc = re.match(r"^(?:location|workplace)\s*:\s*(.+)$", line_s, re.IGNORECASE)
        if m_loc:
            loc_raw = m_loc.group(1).strip()
            if "/" in loc_raw:
                parts = [p.strip() for p in loc_raw.split("/")]
                data["location"] = parts[0]
                for p in parts[1:]:
                    if p.lower() in WORK_MODES and not data["work_mode"]:
                        data["work_mode"] = p.capitalize()
                    elif p.lower() in JOB_TYPES and not data["employment_type"]:
                        p_low = p.lower()
                        data["employment_type"] = "Full-Time" if p_low == "full-time" else ("Part-Time" if p_low == "part-time" else p.capitalize())
            else:
                data["location"] = loc_raw
            continue

        m_type = re.match(r"^(?:job\s+type|employment\s+type|type)\s*:\s*(.+)$", line_s, re.IGNORECASE)
        if m_type and not data["employment_type"]:
            data["employment_type"] = m_type.group(1).strip()
            continue

        m_title = re.match(r"^(?:job\s+title|title|role|position)\s*:\s*(.+)$", line_s, re.IGNORECASE)
        if m_title and not data["title"]:
            data["title"] = m_title.group(1).strip()
            continue

        # 3. "Title at Company" pattern
        if " at " in line_s.lower() and not data["title"]:
            t_cand, _, c_cand = line_s.partition(" at ")
            data["title"] = t_cand.strip()
            data["company"] = c_cand.strip()
            continue

        # 4. Delimiter-separated lines (e.g. "Capco - Java Full Stack Developer" or "OpenBio Labs - Boston, MA (On-site)")
        if " - " in line_s:
            parts = [p.strip() for p in line_s.split(" - ", 1)]
            p0_low, p1_low = parts[0].lower(), parts[1].lower()
            p0_has_role = any(k in p0_low for k in TITLE_ROLE_KEYWORDS)
            p1_has_role = any(k in p1_low for k in TITLE_ROLE_KEYWORDS)

            if p0_has_role and not p1_has_role:
                if not data["title"]:
                    data["title"] = parts[0]
            elif p1_has_role and not p0_has_role:
                if not data["company"]:
                    data["company"] = parts[0]
                if not data["title"]:
                    data["title"] = parts[1]
            elif not p0_has_role and not p1_has_role:
                if not data["company"] and len(parts[0].split()) <= 4:
                    data["company"] = parts[0]
                if not data["location"] and ("," in parts[1] or any(c in parts[1] for c in ["MA", "CA", "NY", "TX", "FL", "WA", "India"])):
                    loc_clean = re.sub(r"\(.*?\)", "", parts[1]).strip()
                    data["location"] = loc_clean
            continue

        # 5. Standalone Title Line
        if not data["title"] and len(line_s.split()) <= 8 and not line_s.endswith(":"):
            if any(k in line_s.lower() for k in TITLE_ROLE_KEYWORDS):
                data["title"] = line_s

    return data


def analyze_job_description(jd_text: str, title: str = "") -> StructuredJobRequirements:
    """
    Parses and categorizes Job Description text into structured requirements.
    Pure analytical transformation — never alters candidate profile data.
    """
    lines = [l.strip() for l in jd_text.split("\n")]
    meta = _extract_header_metadata(lines)
    inferred_title = title.strip() or meta["title"] or ""
    company_name = meta["company"]
    location_val = meta["location"]
    work_mode_val = meta["work_mode"]
    employment_type_val = meta["employment_type"]

    # Step 1 & 2: Section Partitioning & Block Grouping
    current_cat = RequirementCategory.UNKNOWN
    current_heading = "Header / Preamble"

    sections_map: list[dict[str, Any]] = []
    current_block_lines: list[str] = []

    def flush_section():
        if current_block_lines:
            sections_map.append({
                "category": current_cat,
                "heading": current_heading,
                "lines": list(current_block_lines),
            })
            current_block_lines.clear()

    for line in lines:
        if not line:
            continue

        cat_match = _detect_section_category(line)
        if cat_match:
            flush_section()
            current_cat, _ = cat_match
            current_heading = line.strip(" :")
            continue

        current_block_lines.append(line)

    flush_section()

    # Step 3 to 10: Extract Requirements, Skills, Context, and Provenance
    requirements: list[JobRequirement] = []
    must_have_skills: set[str] = set()
    preferred_skills: set[str] = set()
    responsibilities: list[str] = []
    qualifications: list[str] = []
    company_overview_blocks: list[str] = []
    role_overview_blocks: list[str] = []
    soft_skills: set[str] = set()
    detected_tools: set[str] = set()
    detected_techs: set[str] = set()
    detected_domains: set[str] = set()
    education_reqs: list[str] = []
    cert_reqs: list[str] = []

    experience_req = None
    min_years: float | None = None
    max_years: float | None = None

    for sec in sections_map:
        sec_cat = sec["category"]
        sec_heading = sec["heading"]
        sec_lines = sec["lines"]

        # 1. Company Overview
        if sec_cat == RequirementCategory.COMPANY_OVERVIEW:
            company_overview_blocks.append(" ".join(sec_lines))
            continue

        # 2. Role Overview
        if sec_cat == RequirementCategory.ROLE_OVERVIEW:
            role_overview_blocks.append(" ".join(sec_lines))
            continue

        # 3. Benefits / EEO / Legal (isolated from candidate requirements)
        if sec_cat in (RequirementCategory.BENEFITS, RequirementCategory.EEO_LEGAL):
            continue

        # 4. Unknown / Preamble
        if sec_cat == RequirementCategory.UNKNOWN:
            for line in sec_lines:
                if re.match(r"^(?:location|job\s+type|salary|employment\s+type|department)\s*:\s*", line, re.IGNORECASE):
                    continue
                if any(w in line.lower() for w in ["looking for", "we are seeking", "join our team"]):
                    role_overview_blocks.append(line)
                elif any(w in line.lower() for w in ["consultancy", "global company", "founded in", "mission is"]):
                    company_overview_blocks.append(line)
            continue

        # 5. Core Requirements / Responsibilities / Qualifications / Domain
        for raw_line in sec_lines:
            clean_text = _BULLET_PREFIX_RE.sub("", raw_line).strip()
            if not clean_text or len(clean_text) < 3:
                continue

            # Skip standalone header sub-tags
            if clean_text.endswith(":") and len(clean_text.split()) <= 4:
                sub_cat = _detect_section_category(clean_text)
                if sub_cat:
                    sec_cat = sub_cat[0]
                    sec_heading = clean_text.strip(" :")
                    continue

            # Experience extraction
            if not experience_req:
                if not any(w in clean_text.lower() for w in ["our company", "we have", "firm with", "history of", "in business"]):
                    exp_m = _EXP_PATTERN.search(clean_text)
                    if exp_m:
                        experience_req = exp_m.group(0).strip()
                        years_val_str = exp_m.group(1).replace("+", "").strip()
                        if "-" in years_val_str or "to" in years_val_str:
                            p_nums = re.findall(r"\d+", years_val_str)
                            if len(p_nums) >= 2:
                                min_years = float(p_nums[0])
                                max_years = float(p_nums[1])
                        else:
                            try:
                                min_years = float(years_val_str)
                            except ValueError:
                                pass

            # Education extraction
            is_edu = any(re.search(r"\b" + kw + r"\b", clean_text, re.IGNORECASE) for kw in [
                "bachelor", "master", "phd", "degree", "diploma", "b.tech", "b.e", "m.tech", "bs in", "ms in", "b.s.", "m.s."
            ])
            if is_edu:
                education_reqs.append(clean_text)
                qualifications.append(clean_text)

            # Certification extraction
            if any(re.search(r"\b" + kw + r"\b", clean_text, re.IGNORECASE) for kw in [
                "certified", "certification", "aws certified", "ckad", "pmp", "cissp", "certifications"
            ]):
                cert_reqs.append(clean_text)

            # Skill detection
            detected_skills = extract_skills_from_text(clean_text)
            detected_soft = [w for w in SOFT_SKILL_KEYWORDS if w in clean_text.lower()]
            soft_skills.update(detected_soft)

            for skill in detected_skills:
                if skill.lower() in KNOWN_TOOLS:
                    detected_tools.add(skill)
                else:
                    detected_techs.add(skill)

            for term in DOMAIN_TERMS:
                if re.search(r"\b" + re.escape(term) + r"\b", clean_text, re.IGNORECASE):
                    detected_domains.add(term.title())

            # Category assignment & skill partitioning
            item_cat = sec_cat
            if detected_soft and not detected_skills and len(clean_text.split()) <= 10:
                item_cat = RequirementCategory.SOFT_SKILL
                weight = 0.5
            elif item_cat == RequirementCategory.MUST_HAVE:
                must_have_skills.update(detected_skills)
                weight = 1.0
            elif item_cat == RequirementCategory.PREFERRED:
                preferred_skills.update(detected_skills)
                weight = 0.6
            elif item_cat == RequirementCategory.RESPONSIBILITY:
                responsibilities.append(clean_text)
                weight = 0.8
            elif item_cat == RequirementCategory.QUALIFICATION:
                qualifications.append(clean_text)
                weight = 0.7
            elif item_cat == RequirementCategory.DOMAIN:
                detected_domains.add(clean_text)
                weight = 0.65
            else:
                weight = 0.5

            req_id = f"req_{len(requirements)}"
            requirements.append(JobRequirement(
                id=req_id,
                category=item_cat,
                text=clean_text,
                skills_detected=detected_skills,
                importance_weight=weight,
                source_section=str(sec_cat.value),
                source_heading=sec_heading,
                raw_text=raw_line,
                normalized_text=clean_text,
            ))

    # Step 11: Seniority Classification (Anchored Evidence)
    seniority = "MID"
    title_lower = (inferred_title or "").lower()

    # 1. High-priority Title Check
    if any(re.search(r"\b" + kw + r"\b", title_lower) for kw in ["senior", "sr", "lead", "principal", "staff", "director", "manager", "head", "architect"]):
        seniority = "SENIOR"
    elif any(re.search(r"\b" + kw + r"\b", title_lower) for kw in ["junior", "jr", "intern", "internship", "graduate", "entry level", "associate", "trainee"]):
        seniority = "ENTRY"
    else:
        # 2. Experience-based Check
        if min_years is not None:
            if min_years >= 6.0:
                seniority = "SENIOR"
            elif min_years <= 2.0:
                seniority = "ENTRY"
            else:
                seniority = "MID"
        else:
            seniority = "MID"

    # Step 12: Domain Classification (Weighted Evidence)
    domain_scores: dict[str, float] = {
        "Full Stack Engineering": 0.0,
        "Backend & Distributed Systems": 0.0,
        "Frontend & Web": 0.0,
        "Cloud & Infrastructure": 0.0,
        "AI & Machine Learning": 0.0,
        "Data Engineering": 0.0,
        "Mobile Development": 0.0,
        "Cybersecurity": 0.0,
        "Embedded & Systems": 0.0,
    }

    def score_zone(text_str: str, weight: float):
        t_low = text_str.lower()
        if re.search(r"\b(full\s*stack|fullstack)\b", t_low):
            domain_scores["Full Stack Engineering"] += 3.0 * weight
        if re.search(r"\b(backend|api|apis|microservices|distributed systems|spring boot|django|fastapi|golang)\b", t_low):
            domain_scores["Backend & Distributed Systems"] += 1.5 * weight
        if re.search(r"\b(frontend|react|angular|vue|ui|ux|html5|css3|typescript|javascript)\b", t_low):
            domain_scores["Frontend & Web"] += 1.5 * weight
        if re.search(r"\b(cloud|devops|site reliability|kubernetes|docker|aws|azure|gcp|terraform|infrastructure)\b", t_low):
            domain_scores["Cloud & Infrastructure"] += 1.0 * weight
        if re.search(r"\b(machine learning|deep learning|ai engineer|nlp|computer vision|llms|pytorch|tensorflow)\b", t_low):
            domain_scores["AI & Machine Learning"] += 2.0 * weight
        if re.search(r"\b(data engineer|etl|spark|hadoop|big data|data pipeline|snowflake|databricks)\b", t_low):
            domain_scores["Data Engineering"] += 2.0 * weight
        if re.search(r"\b(ios|android|swift|kotlin|react native|flutter|mobile)\b", t_low):
            domain_scores["Mobile Development"] += 2.0 * weight
        if re.search(r"\b(security|infosec|cyber|penetration|soc|siem|vulnerability)\b", t_low):
            domain_scores["Cybersecurity"] += 2.0 * weight
        if re.search(r"\b(embedded|firmware|c\+\+|rtos|kernel|hardware)\b", t_low):
            domain_scores["Embedded & Systems"] += 2.0 * weight

    score_zone(inferred_title or "", 3.0)
    score_zone(" ".join(responsibilities), 2.0)
    score_zone(" ".join(list(must_have_skills)), 1.5)
    score_zone(" ".join(list(preferred_skills)), 0.5)

    best_domain = max(domain_scores.items(), key=lambda x: x[1])
    assigned_domain = best_domain[0] if best_domain[1] > 0 else "Full Stack Engineering"

    domain_list = sorted(list(detected_domains))
    req_skills = sorted(list(must_have_skills))
    pref_skills = sorted(list(preferred_skills))
    all_soft = sorted(list(soft_skills))

    return StructuredJobRequirements(
        target_role=inferred_title or None,
        job_title=inferred_title or None,
        company=company_name,
        company_overview="\n\n".join(company_overview_blocks) if company_overview_blocks else None,
        role_overview="\n\n".join(role_overview_blocks) if role_overview_blocks else None,
        location=location_val,
        work_mode=work_mode_val,
        employment_type=employment_type_val,
        seniority=seniority,
        domain=assigned_domain,
        requirements=requirements,
        required_skills=req_skills,
        must_have_skills=req_skills,
        preferred_skills=pref_skills,
        responsibilities=responsibilities,
        tools=sorted(list(detected_tools)),
        technologies=sorted(list(detected_techs)),
        qualifications=qualifications,
        education_requirements=education_reqs,
        certifications=cert_reqs,
        experience_requirements=experience_req,
        min_years_experience=min_years,
        max_years_experience=max_years,
        behavioral_expectations=all_soft,
        soft_skills=all_soft,
        keywords=req_skills + sorted(list(detected_tools)),
        domain_terminology=domain_list,
        domain_keywords=domain_list,
        important_terminology=domain_list + req_skills,
    )


# Canonical alias
analyze_jd_requirements = analyze_job_description
