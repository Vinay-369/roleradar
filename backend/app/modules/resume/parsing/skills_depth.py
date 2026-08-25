"""
Technical Stack & Skills Depth Engine — deterministic skill taxonomy scoring.
Categorizes candidate skills into 5 core engineering domains and computes
stack breadth, domain completeness, and verified skill density.
"""
import re
from dataclasses import dataclass, field

JUNK_WORDS = {
    "communication", "teamwork", "leadership", "time management",
    "problem solving", "critical thinking", "adaptability", "work ethic",
    "skills", "knowledge", "proficient", "familiar", "working", "building",
    "responsible", "assisted", "learning", "enthusiastic", "hardworking",
    "hard worker", "team player", "good communication", "quick learner",
    "passionate", "detail oriented", "self motivated", "good listener",
    "ms office", "microsoft office", "word", "powerpoint", "excel",
    # Spoken languages & personal details
    "english", "kannada", "hindi", "telugu", "tamil", "malayalam", "marathi",
    "address", "location", "native", "gender", "dob", "nationality", "indian",
    "hobbies", "interests", "strengths", "languages known",
    # Geographic locations & cities
    "karnataka", "maharashtra", "tamil nadu", "telangana", "andhra pradesh",
    "kerala", "delhi", "uttar pradesh", "gujarat", "rajasthan", "west bengal",
    "punjab", "haryana", "bihar", "odisha", "madhya pradesh", "goa",
    "davanagere", "davangere", "bangalore", "bengaluru", "mysore", "mysuru",
    "hubli", "dharwad", "mangalore", "mangaluru", "belgaum", "belagavi",
    "mumbai", "pune", "hyderabad", "chennai", "coimbatore", "kochi",
    "kolkata", "noida", "gurgaon", "gurugram", "ahmedabad", "jaipur",
    "remote", "india", "usa", "uk",
}

DOMAIN_DEFINITIONS = [
    {
        "id": "databases",
        "name": "Databases & Storage Systems",
        "keywords": [
            "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
            "cassandra", "dynamodb", "kafka", "rabbitmq", "spark", "dbt", "snowflake",
            "bigquery", "nosql", "sql server", "mssql", "firebase", "supabase", "prisma",
            "sqlalchemy", "hibernate", "neo4j", "mariadb", "couchdb", "relational databases",
        ],
    },
    {
        "id": "frameworks",
        "name": "Frameworks & Web Technologies",
        "keywords": [
            "react", "angular", "vue", "next.js", "nextjs", "nuxt", "svelte", "tailwind",
            "bootstrap", "redux", "zustand", "express", "fastapi", "django", "flask",
            "spring boot", "spring", "asp.net", "dotnet", ".net", "nestjs", "graphql",
            "rest api", "restful", "rest", "trpc", "grpc", "gin", "fiber", "laravel",
        ],
    },
    {
        "id": "devops_cloud",
        "name": "Cloud, Containers & DevOps",
        "keywords": [
            "aws", "azure", "google cloud", "gcp", "docker", "kubernetes", "k8s", "terraform",
            "ci/cd", "ci-cd", "github actions", "gitlab", "jenkins", "linux", "ubuntu",
            "nginx", "prometheus", "grafana", "devops", "ansible", "cloud", "helm",
            "cloudformation", "datadog", "argocd", "sonarqube",
        ],
    },
    {
        "id": "languages",
        "name": "Programming Languages",
        "keywords": [
            "python", "java", "javascript", "typescript", "c++", "c#", "golang", "go", "rust",
            "kotlin", "swift", "ruby", "php", "scala", "r", "dart", "html5", "html",
            "css3", "css", "sass", "scss", "sql", "bash", "shell", "powershell", "lua",
        ],
    },
    {
        "id": "core_cs_tools",
        "name": "Core CS, Architecture & Tools",
        "keywords": [
            "data structures", "dsa", "algorithms", "system design", "microservices",
            "oop", "object oriented", "unit testing", "pytest", "jest", "postman",
            "git", "github", "clean architecture", "design patterns", "multithreading",
            "concurrency", "asynchronous", "rest architecture", "tdd", "bdd",
            "agile", "scrum", "jira", "vite", "webpack", "docker compose",
        ],
    },
]


@dataclass
class CategorizedSkillDomain:
    id: str
    name: str
    items: list[str] = field(default_factory=list)


@dataclass
class SkillsDepthResult:
    score: int  # 0 - 100
    total_skills: int
    verified_skills_count: int
    domain_coverage_count: int  # 0 - 5
    categorized_domains: list[CategorizedSkillDomain] = field(default_factory=list)
    missing_domains: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def _is_junk(skill_str: str) -> bool:
    lower = skill_str.strip().lower()
    if len(lower) < 2:
        return True
    if lower in JUNK_WORDS:
        return True
    return any(j in lower for j in [
        "team player", "communication", "hardworking", "passionate",
        "detail oriented", "quick learner", "self motivated", "time management",
        "problem solving", "critical thinking",
    ])


def _matches_keyword(lower_skill: str, keyword: str) -> bool:
    if lower_skill == keyword:
        return True
    # Special short tokens
    if keyword in {"c", "r", "go", "sql", "git"}:
        pattern = r"(?:^|[\s,/+])" + re.escape(keyword) + r"(?:$|[\s,/+])"
        return bool(re.search(pattern, lower_skill))
    # Standard keyword match
    return keyword in lower_skill


def analyze_skills_depth(raw_skills: list[str]) -> SkillsDepthResult:
    """
    Categorizes extracted skills into 5 engineering domains and calculates depth score.
    """
    seen: set[str] = set()
    cleaned_skills: list[str] = []

    for s in raw_skills:
        trimmed = s.strip()
        lower = trimmed.lower()
        if _is_junk(lower) or lower in seen:
            continue
        seen.add(lower)
        cleaned_skills.append(trimmed)

    # Initialize domain containers
    domain_map: dict[str, list[str]] = {d["id"]: [] for d in DOMAIN_DEFINITIONS}

    for skill in cleaned_skills:
        lower = skill.lower()
        categorized = False

        for dom in DOMAIN_DEFINITIONS:
            dom_id = dom["id"]
            keywords = dom["keywords"]
            if any(_matches_keyword(lower, kw) for kw in keywords):
                domain_map[dom_id].append(skill)
                categorized = True
                break

        if not categorized:
            # Only categorize into core_cs_tools if it's reasonably technical and not junk/location
            if (
                len(skill) <= 30
                and not any(c in skill for c in [".", "!", "?", ",", "|", "/"])
                and not _is_junk(lower)
            ):
                domain_map["core_cs_tools"].append(skill)

    categorized_list: list[CategorizedSkillDomain] = []
    covered_domain_names: list[str] = []
    missing_domain_names: list[str] = []

    for dom in DOMAIN_DEFINITIONS:
        dom_id = dom["id"]
        items = domain_map[dom_id]
        cat = CategorizedSkillDomain(id=dom_id, name=dom["name"], items=items)
        categorized_list.append(cat)
        if items:
            covered_domain_names.append(dom["name"])
        else:
            missing_domain_names.append(dom["name"])

    coverage_count = len(covered_domain_names)
    total_verified = sum(len(c.items) for c in categorized_list)

    # Deterministic Scoring (0-100):
    # - Domain breadth (5 domains * 12 points = 60 max)
    # - Skill volume & depth (up to 40 max based on verified count)
    volume_points = (
        40 if total_verified >= 10
        else 30 if total_verified >= 6
        else 20 if total_verified >= 3
        else 10 if total_verified >= 1
        else 0
    )
    breadth_points = coverage_count * 12

    score = min(100, max(15, breadth_points + volume_points)) if total_verified > 0 else 0

    issues: list[str] = []
    recommendations: list[str] = []

    if total_verified < 5:
        issues.append(
            f"Low technical skill volume: only {total_verified} verified skills detected (recommended: 8–15)."
        )
        recommendations.append(
            "Add core technical tools, databases, and frameworks explicitly into a dedicated Skills section."
        )

    if coverage_count < 3:
        issues.append(
            f"Limited stack breadth: skills cover only {coverage_count}/5 engineering domains."
        )
        if missing_domain_names:
            recommendations.append(
                f"Consider adding competencies in missing domains: {', '.join(missing_domain_names[:2])}."
            )

    return SkillsDepthResult(
        score=score,
        total_skills=len(raw_skills),
        verified_skills_count=total_verified,
        domain_coverage_count=coverage_count,
        categorized_domains=categorized_list,
        missing_domains=missing_domain_names,
        issues=issues,
        recommendations=recommendations,
    )
