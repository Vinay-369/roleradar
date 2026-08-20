"""
RoleRadar ATS Compatibility Score (Feature 11).

Deliberately NOT a new scoring engine — it's a combination of scores
already computed by other deterministic modules (Parseability,
Recruiter Impact, the Matching Engine's skill/role sub-scores), plus
one new component (keyword coverage against the specific JD text).
This keeps the "same score, explained differently in different places"
promise honest: the Resume Intelligence page and the ATS page for a
given job are reading from the same underlying facts, not two
different opinions.

Named "RoleRadar ATS Compatibility Score" throughout the API and UI —
never presented as a real company's proprietary ATS score, per your
explicit requirement.
"""
import re
from dataclasses import dataclass

STOPWORDS = {
    "the", "and", "for", "with", "a", "an", "to", "of", "in", "on", "is", "are",
    "our", "we", "you", "your", "will", "this", "that", "as", "be", "or", "at",
}


@dataclass
class MatchGuidance:
    status: str  # "ideal" | "over_optimized" | "good" | "needs_work"
    label: str
    message: str
    target_range: str = "75% - 85%"


@dataclass
class ATSScoreResult:
    overall: int
    keyword_coverage: int
    required_skills: int
    role_alignment: int
    structure: int
    formatting: int
    readability: int
    keyword_density: float = 1.5
    over_optimization_warning: bool = False
    match_guidance: MatchGuidance = None


def _extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{2,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def _keyword_coverage(resume_text: str, jd_text: str) -> int:
    jd_keywords = _extract_keywords(jd_text)
    if not jd_keywords:
        return 100
    resume_keywords = _extract_keywords(resume_text)
    covered = jd_keywords & resume_keywords
    return round((len(covered) / len(jd_keywords)) * 100)


def _calculate_keyword_density(resume_text: str, jd_text: str) -> tuple[int, float, bool]:
    jd_keywords = _extract_keywords(jd_text)
    resume_words = [w.lower() for w in re.findall(r"[a-zA-Z0-9+.#-]+", resume_text)]
    total_resume_words = max(1, len(resume_words))

    if not jd_keywords:
        return 100, 1.0, False

    resume_keyword_set = set(resume_words)
    covered = jd_keywords & resume_keyword_set
    coverage = round((len(covered) / len(jd_keywords)) * 100)

    # Count total occurrences of covered JD keywords across resume
    total_occurrences = sum(1 for w in resume_words if w in covered)
    density = round((total_occurrences / total_resume_words) * 100, 2)

    over_optimized = density > 3.0 or coverage > 90
    return coverage, density, over_optimized


def _get_match_guidance(overall: int, over_optimized: bool) -> MatchGuidance:
    if 75 <= overall <= 85 and not over_optimized:
        return MatchGuidance(
            status="ideal",
            label="Ideal Match Zone",
            message="Optimal fit for both ATS filtering and human recruiter review (75%–85% target range).",
        )
    elif overall > 85 or over_optimized:
        return MatchGuidance(
            status="over_optimized",
            label="High Optimization Alert",
            message="High match score. Ensure content reads naturally and avoids repetitive keyword stuffing.",
        )
    elif 60 <= overall < 75:
        return MatchGuidance(
            status="good",
            label="Solid Foundation",
            message="Good compatibility. Add 1–2 target skills from the JD to reach the ideal 75%–80% zone.",
        )
    else:
        return MatchGuidance(
            status="needs_work",
            label="Needs Targeted Tailoring",
            message="Significant gap between resume and JD requirements. Focus on core technical competencies.",
        )


def compute_ats_score(
    resume_text: str,
    jd_text: str,
    parseability_score: int,
    recruiter_impact_score: int,
    skill_match_score: int,
    role_match_score: int,
) -> ATSScoreResult:
    keyword_coverage, keyword_density, over_optimization_warning = _calculate_keyword_density(resume_text, jd_text)

    # Structure/Formatting/Readability are all facets of the same
    # deterministic Parseability Engine result, surfaced separately
    # here because Feature 11 asks for them as distinct dashboard rows.
    structure = parseability_score
    formatting = parseability_score
    readability = recruiter_impact_score

    overall = round(
        keyword_coverage * 0.25
        + skill_match_score * 0.30
        + role_match_score * 0.15
        + structure * 0.15
        + readability * 0.15
    )

    guidance = _get_match_guidance(overall, over_optimization_warning)

    return ATSScoreResult(
        overall=overall,
        keyword_coverage=keyword_coverage,
        required_skills=skill_match_score,
        role_alignment=role_match_score,
        structure=structure,
        formatting=formatting,
        readability=readability,
        keyword_density=keyword_density,
        over_optimization_warning=over_optimization_warning,
        match_guidance=guidance,
    )
