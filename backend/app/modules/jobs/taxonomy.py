"""
Structured Job Description Taxonomy and Requirement Extraction.
Classifies JD requirements into MUST_HAVE, PREFERRED, RESPONSIBILITY, QUALIFICATION, DOMAIN, SOFT_SKILL.
Provides deterministic JDRequirements representation without mutating candidate evidence.
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


class JobRequirement(BaseModel):
    id: str
    category: RequirementCategory
    text: str
    skills_detected: list[str] = Field(default_factory=list)
    importance_weight: float = 1.0


class StructuredJobRequirements(BaseModel):
    target_role: str | None = None
    job_title: str | None = None
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
    experience_requirements: str | None = None
    behavioral_expectations: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    domain_terminology: list[str] = Field(default_factory=list)
    domain_keywords: list[str] = Field(default_factory=list)
    important_terminology: list[str] = Field(default_factory=list)


JDRequirements = StructuredJobRequirements


MUST_HAVE_HEADERS = [
    r"^\s*(?:requirements?|must\s+haves?|basic\s+qualifications?|minimum\s+qualifications?|what\s+you\s+need|core\s+requirements?|essential\s+skills?|what\s+we['’]?re\s+looking\s+for)\b",
]
PREFERRED_HEADERS = [
    r"^\s*(?:preferred\s+qualifications?|nice\s+to\s+haves?|bonus\s+points?|good\s+to\s+have|preferred\s+skills?|plus|desirable|bonus)\b",
]
RESPONSIBILITY_HEADERS = [
    r"^\s*(?:responsibilities|what\s+you['’]ll\s+do|duties|the\s+role|key\s+responsibilities|day\s+to\s+day|scope\s+of\s+work|your\s+mission)\b",
]
QUALIFICATION_HEADERS = [
    r"^\s*(?:education\s+&\s+experience|qualifications?|eligibility|background|education|degree\s+requirements?)\b",
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


def analyze_job_description(jd_text: str, title: str = "") -> StructuredJobRequirements:
    """
    Parses and categorizes Job Description text into structured requirements.
    Pure analytical transformation — never alters candidate profile data.
    """
    lines = jd_text.split("\n")
    current_category = RequirementCategory.MUST_HAVE
    requirements: list[JobRequirement] = []

    must_have_skills: set[str] = set()
    preferred_skills: set[str] = set()
    responsibilities: list[str] = []
    qualifications: list[str] = []
    soft_skills: set[str] = set()
    detected_tools: set[str] = set()
    detected_techs: set[str] = set()
    detected_domains: set[str] = set()
    experience_req = None

    non_empty_lines = [l.strip() for l in lines if l.strip()]
    inferred_title = title.strip()
    if not inferred_title and non_empty_lines:
        first_line = non_empty_lines[0]
        if len(first_line.split()) <= 10 and not any(re.search(p, first_line.lower()) for p in MUST_HAVE_HEADERS + PREFERRED_HEADERS + RESPONSIBILITY_HEADERS + QUALIFICATION_HEADERS + DOMAIN_HEADERS):
            inferred_title = re.sub(r"^(?:job\s+title|title|role)\s*:\s*", "", first_line, flags=re.IGNORECASE).strip()

    # Experience requirement extractor pattern
    exp_pattern = re.compile(r"\b(\d+\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?\s+experience)\b", re.IGNORECASE)

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        # Header detection
        line_lower = line.lower()
        if any(re.search(p, line_lower) for p in MUST_HAVE_HEADERS):
            current_category = RequirementCategory.MUST_HAVE
            continue
        elif any(re.search(p, line_lower) for p in PREFERRED_HEADERS):
            current_category = RequirementCategory.PREFERRED
            continue
        elif any(re.search(p, line_lower) for p in RESPONSIBILITY_HEADERS):
            current_category = RequirementCategory.RESPONSIBILITY
            continue
        elif any(re.search(p, line_lower) for p in QUALIFICATION_HEADERS):
            current_category = RequirementCategory.QUALIFICATION
            continue
        elif any(re.search(p, line_lower) for p in DOMAIN_HEADERS):
            current_category = RequirementCategory.DOMAIN
            continue

        # Clean bullet glyphs
        clean_text = re.sub(r"^[•\-\*\u2013\u2014\u2022\u25CF\u25AA\d\.\)]+\s*", "", line).strip()
        if not clean_text or len(clean_text) < 3:
            continue

        # Skip top-level metadata lines (Location, Salary, Employment Type, etc.)
        if re.match(r"^(?:location|salary|compensation|employment\s+type|experience\s+level|work\s+type|department)\s*:\s*", clean_text, re.IGNORECASE):
            continue

        detected_skills = extract_skills_from_text(clean_text)
        detected_soft = [w for w in SOFT_SKILL_KEYWORDS if w in clean_text.lower()]

        # Check for experience requirement
        if not experience_req:
            exp_m = exp_pattern.search(clean_text)
            if exp_m:
                experience_req = exp_m.group(1).strip()

        # Detect tools vs technologies
        for skill in detected_skills:
            if skill.lower() in KNOWN_TOOLS:
                detected_tools.add(skill)
            else:
                detected_techs.add(skill)

        # Detect domain terminology
        for term in DOMAIN_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", clean_text, re.IGNORECASE):
                detected_domains.add(term.title())

        is_qualification = (
            current_category == RequirementCategory.QUALIFICATION
            or any(re.search(r"\b" + kw + r"\b", clean_text, re.IGNORECASE) for kw in ["bs", "ms", "phd", "bachelor", "master", "degree", "diploma", "b.tech", "b.e", "m.tech", "years experience", "years of experience"])
        )
        if is_qualification:
            qualifications.append(clean_text)

        item_cat = current_category
        if detected_soft and not detected_skills and len(clean_text.split()) <= 10:
            item_cat = RequirementCategory.SOFT_SKILL
            soft_skills.update(detected_soft)
        elif is_qualification and current_category != RequirementCategory.MUST_HAVE and current_category != RequirementCategory.PREFERRED:
            item_cat = RequirementCategory.QUALIFICATION
        elif current_category == RequirementCategory.MUST_HAVE:
            must_have_skills.update(detected_skills)
        elif current_category == RequirementCategory.PREFERRED:
            preferred_skills.update(detected_skills)
        elif current_category == RequirementCategory.RESPONSIBILITY:
            responsibilities.append(clean_text)
        elif current_category == RequirementCategory.QUALIFICATION:
            pass
        elif current_category == RequirementCategory.DOMAIN:
            detected_domains.add(clean_text)

        weight = 1.0
        if item_cat == RequirementCategory.MUST_HAVE:
            weight = 1.0
        elif item_cat == RequirementCategory.PREFERRED:
            weight = 0.6
        elif item_cat == RequirementCategory.RESPONSIBILITY:
            weight = 0.8
        elif item_cat == RequirementCategory.QUALIFICATION:
            weight = 0.7
        elif item_cat == RequirementCategory.DOMAIN:
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
        ))

    # Infer domain & seniority
    seniority = None
    full_lower = (inferred_title + " " + jd_text).lower()
    if any(w in full_lower for w in ["lead", "principal", "staff", "director", "manager", "architect", "head"]):
        seniority = "SENIOR"
    elif any(w in full_lower for w in ["junior", "intern", "graduate", "entry level", "associate", "trainee"]):
        seniority = "ENTRY"
    else:
        seniority = "MID"

    domain = None
    if any(w in full_lower for w in ["machine learning", "deep learning", "ai engineer", "computer vision", "nlp"]):
        domain = "AI & Machine Learning"
    elif any(w in full_lower for w in ["cloud", "devops", "site reliability", "infrastructure", "kubernetes"]):
        domain = "Cloud & Infrastructure"
    elif any(w in full_lower for w in ["data engineer", "etl", "spark", "big data"]):
        domain = "Data Engineering"
    elif any(w in full_lower for w in ["backend", "api", "distributed systems"]):
        domain = "Backend & Distributed Systems"
    elif any(w in full_lower for w in ["frontend", "react", "ui", "ux"]):
        domain = "Frontend & Web"
    elif any(w in full_lower for w in ["full stack", "fullstack"]):
        domain = "Full Stack Engineering"

    domain_list = sorted(list(detected_domains))
    req_skills = sorted(list(must_have_skills))
    all_soft = sorted(list(soft_skills))

    return StructuredJobRequirements(
        target_role=inferred_title or None,
        job_title=inferred_title or None,
        seniority=seniority,
        domain=domain,
        requirements=requirements,
        required_skills=req_skills,
        must_have_skills=req_skills,
        preferred_skills=sorted(list(preferred_skills)),
        responsibilities=responsibilities,
        tools=sorted(list(detected_tools)),
        technologies=sorted(list(detected_techs)),
        qualifications=qualifications,
        experience_requirements=experience_req,
        behavioral_expectations=all_soft,
        soft_skills=all_soft,
        keywords=req_skills + sorted(list(detected_tools)),
        domain_terminology=domain_list,
        domain_keywords=domain_list,
        important_terminology=domain_list + req_skills,
    )


# Canonical alias
analyze_jd_requirements = analyze_job_description
