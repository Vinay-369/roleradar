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
    current_evidence: str  # MISSING | PARTIAL
    resources: list[str] = field(default_factory=list)
    project_suggestion: str = ""
    estimated_days: int = 5


def _project_suggestion(skill: str) -> str:
    return f"Build a hands-on project that uses {skill} directly, then add it to your portfolio and resume with measurable results."


def compute_skill_gaps(
    missing_required: list[str],
    partial_required: list[str],
    missing_nice_to_have: list[str],
    job_title: str,
) -> list[SkillGap]:
    gaps: list[SkillGap] = []

    for skill in missing_required:
        gaps.append(SkillGap(
            skill=skill,
            priority="CORE",
            reason=f"'{skill}' is a required skill for {job_title} and no evidence of it was found in your resume.",
            target_job_title=job_title,
            current_evidence="MISSING",
            resources=get_resources_for_skill(skill),
            project_suggestion=_project_suggestion(skill),
            estimated_days=PRIORITY_ESTIMATED_DAYS["CORE"],
        ))

    for skill in partial_required:
        gaps.append(SkillGap(
            skill=skill,
            priority="SECONDARY",
            reason=f"'{skill}' is required, and your resume shows related experience, but not this exact skill by name.",
            target_job_title=job_title,
            current_evidence="PARTIAL",
            resources=get_resources_for_skill(skill),
            project_suggestion=_project_suggestion(skill),
            estimated_days=PRIORITY_ESTIMATED_DAYS["SECONDARY"],
        ))

    for skill in missing_nice_to_have:
        gaps.append(SkillGap(
            skill=skill,
            priority="BONUS",
            reason=f"'{skill}' isn't required for {job_title} but would strengthen your application.",
            target_job_title=job_title,
            current_evidence="MISSING",
            resources=get_resources_for_skill(skill),
            project_suggestion=_project_suggestion(skill),
            estimated_days=PRIORITY_ESTIMATED_DAYS["BONUS"],
        ))

    return gaps


def build_roadmap(gaps: list[SkillGap]) -> dict[str, list[str]]:
    """
    Feature 17: Immediate / 1 Week / 2 Weeks / 1 Month buckets.

    Distributes ALL gaps across the 4 windows as evenly as possible,
    in priority order (CORE first, then SECONDARY, then BONUS), rather
    than a fixed CORE-vs-SECONDARY split. The fixed-split version could
    leave later windows completely empty whenever there weren't many
    CORE/SECONDARY gaps specifically -- this guarantees a genuinely
    scheduled plan whenever there's anything to schedule at all, with
    earlier windows getting any remainder so the highest-priority gaps
    are still front-loaded.
    """
    ordered_skills = (
        [g.skill for g in gaps if g.priority == "CORE"]
        + [g.skill for g in gaps if g.priority == "SECONDARY"]
        + [g.skill for g in gaps if g.priority == "BONUS"]
    )

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
