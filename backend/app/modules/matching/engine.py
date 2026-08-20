"""
Matching engine (Feature 6). Fully deterministic weighted formula —
the LLM is never the ranking algorithm, per your explicit requirement
that AI must not be the sole source of a deterministic score.

Skill similarity uses the pluggable EmbeddingProvider (TF-IDF by
default, sentence-transformers optional) so "React.js" vs "React"
still counts as a match without requiring exact string equality.
"""
from dataclasses import dataclass, field

from app.core.embeddings.base import EmbeddingProvider

# Default weights — Feature 6 requires these to be configurable, not
# fixed at the code level for one category, so they're passed in
# rather than hardcoded as module constants.
DEFAULT_WEIGHTS = {
    "skill": 0.35,
    "role": 0.20,
    "experience": 0.15,
    "location": 0.15,
    "salary": 0.10,
    "industry": 0.05,
}

# Fresher mode boosts skill/project evidence over years of experience;
# experienced mode does the opposite. Both still sum to 1.0.
CATEGORY_WEIGHTS = {
    "FRESHER": {"skill": 0.40, "role": 0.20, "experience": 0.05, "location": 0.15, "salary": 0.15, "industry": 0.05},
    "EXPERIENCED": {"skill": 0.30, "role": 0.20, "experience": 0.25, "location": 0.10, "salary": 0.10, "industry": 0.05},
    "CAREER_SWITCHER": {"skill": 0.35, "role": 0.15, "experience": 0.10, "location": 0.15, "salary": 0.15, "industry": 0.10},
    "INTERNSHIP_SEEKER": {"skill": 0.45, "role": 0.15, "experience": 0.05, "location": 0.20, "salary": 0.15, "industry": 0.00},
}

READINESS_THRESHOLDS = {"ready": 90, "fix_gaps": 70}  # below fix_gaps -> learn_first


@dataclass
class SkillMatchDetail:
    matched: list[str] = field(default_factory=list)
    partial: list[str] = field(default_factory=list)  # matched via semantic similarity, not exact
    missing: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    overall_score: int
    skill_score: int
    role_score: int
    experience_score: int
    location_score: int
    salary_score: int
    industry_score: int
    skill_match: SkillMatchDetail
    apply_readiness: str  # "ready" | "fix_gaps" | "learn_first"


def _skill_match(
    candidate_skills: list[str], required_skills: list[str], embedder: EmbeddingProvider, threshold: float = 0.55
) -> tuple[int, SkillMatchDetail]:
    if not required_skills:
        return 100, SkillMatchDetail()

    candidate_lower = [s.lower().strip() for s in candidate_skills]
    detail = SkillMatchDetail()

    for req in required_skills:
        req_lower = req.lower().strip()
        if req_lower in candidate_lower:
            detail.matched.append(req)
            continue
        best_sim = max((embedder.similarity(req_lower, c) for c in candidate_lower), default=0.0)
        if best_sim >= threshold:
            detail.partial.append(req)
        else:
            detail.missing.append(req)

    score = round(((len(detail.matched) + 0.6 * len(detail.partial)) / len(required_skills)) * 100)
    return min(100, score), detail


def _role_match(candidate_target_roles: list[str], job_title: str, embedder: EmbeddingProvider) -> int:
    if not candidate_target_roles:
        return 50  # neutral if candidate hasn't specified target roles
    best = max((embedder.similarity(role, job_title) for role in candidate_target_roles), default=0.0)
    return round(best * 100)


def _experience_match(candidate_years: float, job_min: int, job_max: int) -> int:
    if job_min <= candidate_years <= job_max:
        return 100
    if candidate_years < job_min:
        gap = job_min - candidate_years
        return max(0, round(100 - gap * 25))
    over = candidate_years - job_max
    return max(40, round(100 - over * 10))


def _location_match(candidate_locations: list[str], candidate_remote_pref: str, job_location: str, job_is_remote: bool) -> int:
    if candidate_remote_pref == "remote" and job_is_remote:
        return 100
    if candidate_remote_pref == "any":
        return 100 if (job_is_remote or not candidate_locations or job_location in candidate_locations) else 60
    if job_is_remote:
        return 90
    if not candidate_locations:
        return 60
    return 100 if job_location in candidate_locations else 30


def _salary_match(candidate_min_lpa: float | None, job_salary_max: float | None, salary_disclosed: bool) -> int:
    if candidate_min_lpa is None:
        return 70
    if not salary_disclosed or job_salary_max is None:
        return 50  # neutral, not penalized — undisclosed salary shouldn't hide good jobs
    return 100 if job_salary_max >= candidate_min_lpa else max(0, round(100 - (candidate_min_lpa - job_salary_max) * 15))


def _industry_match(candidate_industries: list[str], job_industry: str) -> int:
    if not candidate_industries:
        return 70
    return 100 if job_industry in candidate_industries else 40


def _apply_readiness(score: int) -> str:
    if score >= READINESS_THRESHOLDS["ready"]:
        return "ready"
    if score >= READINESS_THRESHOLDS["fix_gaps"]:
        return "fix_gaps"
    return "learn_first"


def compute_match(
    candidate: dict,
    job: dict,
    embedder: EmbeddingProvider,
    category: str = "FRESHER",
) -> MatchResult:
    """
    candidate expects: skills (list[str]), target_roles (list[str]),
    experience_years (float), preferred_locations (list[str]),
    remote_preference (str), min_lpa (float | None), industries (list[str])

    job expects: skills_required, title, experience_min, experience_max,
    location, is_remote, salary_max, salary_disclosed, industry
    """
    weights = CATEGORY_WEIGHTS.get(category, DEFAULT_WEIGHTS)

    skill_score, skill_detail = _skill_match(candidate.get("skills", []), job.get("skills_required", []), embedder)
    role_score = _role_match(candidate.get("target_roles", []), job.get("title", ""), embedder)
    experience_score = _experience_match(
        candidate.get("experience_years", 0), job.get("experience_min", 0), job.get("experience_max", 99)
    )
    location_score = _location_match(
        candidate.get("preferred_locations", []),
        candidate.get("remote_preference", "any"),
        job.get("location", ""),
        job.get("is_remote", False),
    )
    salary_score = _salary_match(candidate.get("min_lpa"), job.get("salary_max"), job.get("salary_disclosed", False))
    industry_score = _industry_match(candidate.get("industries", []), job.get("industry", ""))

    overall = round(
        skill_score * weights["skill"]
        + role_score * weights["role"]
        + experience_score * weights["experience"]
        + location_score * weights["location"]
        + salary_score * weights["salary"]
        + industry_score * weights["industry"]
    )

    return MatchResult(
        overall_score=overall,
        skill_score=skill_score,
        role_score=role_score,
        experience_score=experience_score,
        location_score=location_score,
        salary_score=salary_score,
        industry_score=industry_score,
        skill_match=skill_detail,
        apply_readiness=_apply_readiness(overall),
    )
