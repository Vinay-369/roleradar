"""
Action Verb Strength Analysis — deterministic bullet-lead evaluation.
Evaluates whether resume bullets start with high-impact active engineering verbs
versus passive, weak, or vague participation verbs.
"""
import re
from dataclasses import dataclass, field

STRONG_ACTION_VERBS = {
    # Engineering & Building
    "architected", "built", "designed", "developed", "engineered", "constructed",
    "authored", "prototyped", "implemented", "programmed", "coded", "crafted",
    # Optimization & Scaling
    "optimized", "scaled", "accelerated", "reduced", "decreased", "minimized",
    "increased", "boosted", "maximized", "streamlined", "enhanced", "upgraded",
    "refactored", "modernized", "overhauled", "fine-tuned", "consolidated",
    # DevOps & Infrastructure
    "deployed", "automated", "orchestrated", "containerized", "migrated",
    "provisioned", "configured", "monitored", "instrumented", "shipped",
    # Leadership & Delivery
    "spearheaded", "led", "directed", "championed", "delivered", "launched",
    "established", "standardized", "instituted", "formulated", "executed",
    # Integration & Collaboration
    "integrated", "connected", "collaborated", "negotiated", "resolved",
    "diagnosed", "audited", "benchmarked", "profiled", "secured",
}

WEAK_PASSIVE_VERBS = {
    "helped", "assisted", "worked on", "responsible for", "involved in",
    "participated in", "handled", "was part of", "did", "tasked with",
    "contributed to", "supported", "tried to", "attempted", "learned",
    "gained knowledge", "got exposure", "familiar with",
}

_WORD_SPLIT_RE = re.compile(r"[^\w\s-]")


@dataclass
class BulletVerbAnalysis:
    text: str
    lead_verb: str | None
    is_strong: bool
    is_weak: bool


@dataclass
class ActionVerbResult:
    score: int  # 0 - 100
    total_bullets: int
    strong_verb_bullets: int
    weak_verb_bullets: int
    strong_verbs_found: list[str] = field(default_factory=list)
    weak_verbs_found: list[str] = field(default_factory=list)
    power_verb_rate: float = 0.0
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def _extract_lead_phrase(text: str) -> tuple[str | None, bool, bool]:
    """
    Extracts the lead verb/phrase of a bullet point and classifies it as strong or weak.
    """
    cleaned = _WORD_SPLIT_RE.sub(" ", text).strip().lower()
    words = cleaned.split()
    if not words:
        return None, False, False

    # Check multi-word weak phrases first (e.g. "worked on", "responsible for", "participated in")
    two_words = " ".join(words[:2])
    three_words = " ".join(words[:3]) if len(words) >= 3 else ""

    for weak_p in WEAK_PASSIVE_VERBS:
        if weak_p in (three_words, two_words, words[0]):
            return weak_p, False, True
        if cleaned.startswith(weak_p):
            return weak_p, False, True

    # Check single-word strong verbs
    first_word = words[0]
    if first_word in STRONG_ACTION_VERBS:
        return first_word, True, False

    # Also check past-tense verb suffixes that match strong patterns
    if first_word.endswith("ed") and len(first_word) > 4:
        return first_word, True, False

    return first_word, False, False


def analyze_action_verbs(bullets: list[str]) -> ActionVerbResult:
    """
    Evaluates the action verb quality and diversity of resume bullets.
    """
    if not bullets:
        return ActionVerbResult(
            score=0,
            total_bullets=0,
            strong_verb_bullets=0,
            weak_verb_bullets=0,
            power_verb_rate=0.0,
            issues=["No experience or project bullets found to analyze for action verbs."],
            recommendations=["Add detailed bullet points describing your technical contributions."],
        )

    strong_count = 0
    weak_count = 0
    strong_verbs: list[str] = []
    weak_verbs: list[str] = []
    verb_frequency: dict[str, int] = {}

    for b in bullets:
        lead, is_strong, is_weak = _extract_lead_phrase(b)
        if lead:
            verb_frequency[lead] = verb_frequency.get(lead, 0) + 1
        if is_weak:
            weak_count += 1
            if lead and lead not in weak_verbs:
                weak_verbs.append(lead)
        elif is_strong:
            strong_count += 1
            if lead and lead not in strong_verbs:
                strong_verbs.append(lead)

    total = len(bullets)
    power_rate = round(strong_count / total, 2)

    # Base scoring formula
    # 100 base score
    # - 35 points max penalty for weak verbs
    # - 35 points max penalty for missing strong lead verbs
    # - 15 points max penalty for excessive repetition of the exact same verb
    score = 100
    score -= int((weak_count / total) * 45)
    score -= int(((total - strong_count) / total) * 35)

    # Repetition check (if any single verb starts > 40% of all bullets)
    repeated_verbs = [v for v, count in verb_frequency.items() if count / total > 0.4 and total > 2]
    if repeated_verbs:
        score -= 10

    score = max(10, min(100, score))

    issues: list[str] = []
    recommendations: list[str] = []

    if weak_count > 0:
        issues.append(
            f"{weak_count}/{total} bullet points use passive or weak phrasing ({', '.join(weak_verbs[:3])})."
        )
        recommendations.append(
            "Replace passive involvement phrases ('helped', 'worked on') with direct engineering action verbs ('architected', 'optimized', 'scaled')."
        )

    if power_rate < 0.6:
        issues.append(
            f"Only {int(power_rate * 100)}% of bullets lead with assertive technical action verbs."
        )
        recommendations.append(
            "Begin every bullet with a high-impact past-tense technical verb specifying your exact contribution."
        )

    if repeated_verbs:
        issues.append(
            f"Overused starting verb: '{repeated_verbs[0]}' leads more than 40% of your bullets."
        )
        recommendations.append(
            "Diversify your action verbs (e.g. use 'orchestrated', 'streamlined', 'implemented', 'refactored' instead of repeating the same term)."
        )

    return ActionVerbResult(
        score=score,
        total_bullets=total,
        strong_verb_bullets=strong_count,
        weak_verb_bullets=weak_count,
        strong_verbs_found=strong_verbs,
        weak_verbs_found=weak_verbs,
        power_verb_rate=power_rate,
        issues=issues,
        recommendations=recommendations,
    )
