"""
Recruiter Impact analysis — deterministic bullet-level scoring.
Same philosophy as the Parseability Engine: detecting weak verbs and
missing numbers is pattern matching, not language understanding, so it
stays out of the AI path (Feature 28) and is fully explainable.
"""
import re
from dataclasses import dataclass, field

WEAK_VERBS = {
    "helped", "assisted", "worked on", "responsible for", "involved in",
    "participated in", "handled", "was part of", "did", "tasked with",
}

STRONG_VERB_HINTS = {
    "built", "designed", "developed", "implemented", "led", "optimized",
    "reduced", "increased", "automated", "launched", "architected",
    "improved", "created", "shipped", "deployed", "migrated", "refactored",
}

QUANTIFICATION_RE = re.compile(r"\d+(\.\d+)?\s*(%|percent|x|ms|s\b|hrs?|hours?|users?|\+)?", re.IGNORECASE)


@dataclass
class BulletAnalysis:
    text: str
    has_weak_verb: bool
    has_strong_verb: bool
    has_quantification: bool
    word_count: int


@dataclass
class RecruiterImpactResult:
    score: int
    bullets_analyzed: int
    quantified_bullets: int
    weak_verb_bullets: int
    quantification_rate: float
    bullet_analyses: list[BulletAnalysis] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def _analyze_bullet(text: str) -> BulletAnalysis:
    lower = text.lower()
    has_weak = any(lower.startswith(v) or f" {v}" in lower for v in WEAK_VERBS)
    has_strong = any(lower.startswith(v) for v in STRONG_VERB_HINTS)
    has_quant = bool(QUANTIFICATION_RE.search(text))
    return BulletAnalysis(
        text=text,
        has_weak_verb=has_weak,
        has_strong_verb=has_strong,
        has_quantification=has_quant,
        word_count=len(text.split()),
    )


def analyze_recruiter_impact(bullets: list[str]) -> RecruiterImpactResult:
    if not bullets:
        return RecruiterImpactResult(
            score=0, bullets_analyzed=0, quantified_bullets=0, weak_verb_bullets=0,
            quantification_rate=0.0,
            issues=["No experience or project bullets were found to analyze."],
        )

    analyses = [_analyze_bullet(b) for b in bullets]
    quantified = sum(1 for a in analyses if a.has_quantification)
    weak = sum(1 for a in analyses if a.has_weak_verb)
    total = len(analyses)
    quant_rate = quantified / total

    score = 100
    score -= int((weak / total) * 40)  # weak verbs hurt a lot
    score -= int((1 - quant_rate) * 40)  # missing numbers hurts a lot
    score = max(0, min(100, score))

    issues = []
    if quant_rate < 0.3:
        issues.append(
            f"Only {quantified}/{total} bullets include a measurable result (a number, %, or metric). "
            f"Recruiters scan for impact, not just duties."
        )
    if weak > 0:
        issues.append(
            f"{weak}/{total} bullets start with a weak verb (e.g. 'helped', 'assisted', 'responsible for'). "
            f"Lead with what you did, not your involvement."
        )

    return RecruiterImpactResult(
        score=score,
        bullets_analyzed=total,
        quantified_bullets=quantified,
        weak_verb_bullets=weak,
        quantification_rate=round(quant_rate, 2),
        bullet_analyses=analyses,
        issues=issues,
    )
