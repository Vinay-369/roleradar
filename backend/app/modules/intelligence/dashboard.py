"""
Dashboard aggregation (Feature 21). Not a new scoring engine — a
composite of scores already computed elsewhere (Parseability,
Recruiter Impact, the Matching Engine's per-job scores) plus simple
deterministic "what should I do next" logic. Consistent with the rest
of the app: the LLM is never involved in producing this number.
"""
from dataclasses import dataclass, field


@dataclass
class DashboardSummary:
    role_readiness_index: int
    ats_compatibility: int
    skill_coverage: int
    top_matches: list[dict] = field(default_factory=list)
    application_counts: dict = field(default_factory=dict)
    recommended_next_action: str = ""
    resume_uploaded: bool = False
    onboarding_completed: bool = False


def compute_rri(parseability_score: int, recruiter_impact_score: int, best_match_skill_score: int) -> int:
    """
    Role Readiness Index: a simplified, honestly-scoped version of the
    original 5-component formula (ATS/Recruiter/Skill/Evidence/Integrity).
    Evidence and Integrity scores aren't built as separate engines in
    this build, so RRI here is explicitly the 3 components that do
    exist, weighted toward skill coverage since that's the strongest
    predictor of apply-readiness.
    """
    return round(parseability_score * 0.3 + recruiter_impact_score * 0.3 + best_match_skill_score * 0.4)


def recommend_next_action(
    resume_uploaded: bool,
    onboarding_completed: bool,
    parseability_score: int | None,
    recruiter_impact_score: int | None,
    top_matches: list[dict],
) -> str:
    if not onboarding_completed:
        return "Complete your profile so RoleRadar can start matching you to real roles."
    if not resume_uploaded:
        return "Upload your resume to unlock scoring, matching, and tailoring."
    if parseability_score is not None and parseability_score < 70:
        return "Your resume has structural issues that could block ATS parsing — check Resume Intelligence before applying anywhere."
    if recruiter_impact_score is not None and recruiter_impact_score < 60:
        return "Add measurable results to your experience bullets — most currently lack a number or metric."
    if not top_matches:
        return "No strong job matches yet — try broadening your target roles or locations in Settings."

    best = top_matches[0]
    if best["apply_readiness"] == "ready":
        return f"You're ready to apply to {best['job_title']} at {best['company']} ({best['overall_score']}% match)."
    if best["missing_skills"]:
        skill = best["missing_skills"][0]
        return f"Your strongest next action is to close the '{skill}' gap before applying to {best['job_title']} at {best['company']}."
    return f"Review {best['job_title']} at {best['company']} — your top current match at {best['overall_score']}%."
