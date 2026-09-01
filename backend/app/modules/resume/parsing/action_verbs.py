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
    "created", "devised", "invented", "modeled", "compiled", "generated", "produced",
    # Optimization & Scaling
    "optimized", "scaled", "accelerated", "reduced", "decreased", "minimized",
    "increased", "boosted", "maximized", "streamlined", "enhanced", "upgraded",
    "refactored", "modernized", "overhauled", "fine-tuned", "consolidated", "achieved",
    # DevOps, Operations & Infrastructure
    "deployed", "automated", "orchestrated", "containerized", "migrated",
    "provisioned", "configured", "monitored", "instrumented", "shipped",
    "maintained", "tested", "verified", "validated", "parsed",
    # Leadership & Delivery
    "spearheaded", "led", "directed", "championed", "delivered", "launched",
    "established", "standardized", "instituted", "formulated", "executed",
    "managed", "pioneered", "published", "conducted",
    # Integration & Analysis
    "integrated", "connected", "collaborated", "negotiated", "resolved",
    "diagnosed", "audited", "benchmarked", "profiled", "secured",
    "trained", "evaluated", "extracted", "collected", "analyzed",
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


def strengthen_bullet_verb(bullet_text: str, default_verb: str = "Engineered") -> tuple[str, bool]:
    """
    Strengthens the opening verb of a bullet point while guaranteeing:
    1. NEVER double-stack verbs (e.g. 'Developed Implemented', 'Architected Built').
    2. If the bullet already starts with a strong action verb from STRONG_ACTION_VERBS,
       it is preserved without prepending or duplicating.
    3. If the bullet starts with a weak/passive verb or phrasing (e.g. 'Worked on', 'Responsible for'),
       it replaces the weak phrasing with default_verb.
    4. Bullet glyphs/prefixes ('• ', '- ', '1. ') are cleanly preserved.
    Returns: (refined_bullet, was_changed)
    """
    raw = bullet_text.strip()
    if not raw:
        return raw, False

    # Extract leading bullet prefix if present
    bullet_prefix_match = re.match(
        r"^(?:[•\-\*\u2013\u2014\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u27A4\u2714\u2713\u279C\u2192\u25BA\u25B6\u25C6\u25C7\u25CF\u25CB\u2718\u2717\u2705\u27A2\u2794\u2714\ufffd]|\d{1,2}[\.\)]|\([a-zA-Z0-9]+\)|[a-zA-Z]\))\s+",
        raw,
    )
    prefix = bullet_prefix_match.group(0) if bullet_prefix_match else ""
    content = raw[len(prefix):].strip() if prefix else raw

    if not content:
        return raw, False

    clean_words = content.split()
    if not clean_words:
        return raw, False

    # Guard 1: Structural category headings (ending with ':')
    if content.endswith(":"):
        return raw, False

    # Guard 2: Role progression / dates header line (e.g. 'Software Engineer - 3 (April 2024 - Present)')
    if re.search(r"\b(?:\d{4}|present)\b", content, re.IGNORECASE) and len(clean_words) <= 12 and not content.endswith((".", ";", "!")):
        return raw, False

    # Guard 3: Company / short non-bullet title headers
    if len(clean_words) <= 5 and not content.endswith((".", ";", "!")) and not any(w.lower().endswith("ed") for w in clean_words) and not prefix:
        return raw, False

    # Guard 4: If line has category prefix like 'Category Name: Action...'
    if ":" in content:
        cat_part, sep, body_part = content.partition(":")
        if len(cat_part.split()) <= 8 and len(body_part.split()) >= 3:
            body_res, changed = strengthen_bullet_verb(body_part.strip(), default_verb=default_verb)
            return f"{prefix}{cat_part.strip()}: {body_res}", changed

    # 1. Clean accidental duplicate creation verbs (e.g. "Developed Implemented..." -> "Implemented...")
    if len(clean_words) >= 3:
        w0 = re.sub(r"[^a-zA-Z]", "", clean_words[0]).lower()
        w1 = re.sub(r"[^a-zA-Z]", "", clean_words[1]).lower()
        GENERIC_CREATION_VERBS = {"developed", "built", "engineered", "implemented", "created", "designed", "architected"}
        if w0 in GENERIC_CREATION_VERBS and w1 in GENERIC_CREATION_VERBS:
            fixed_content = " ".join([clean_words[1].capitalize()] + clean_words[2:])
            return f"{prefix}{fixed_content}", True

    first_word_clean = re.sub(r"[^a-zA-Z]", "", clean_words[0]).lower()

    # 2. Check for weak multi-word phrases first (e.g. "Worked on", "Responsible for")
    lower_content = content.lower()
    weak_prefixes = [
        "responsible for", "worked on", "helped in", "helped with", "assisted with",
        "assisted in", "involved in", "part of team that", "tasked with", "duties included",
        "contributed to", "participated in", "focused on",
    ]
    for wp in weak_prefixes:
        if lower_content.startswith(wp):
            remainder = content[len(wp):].strip().lstrip(":, -")
            r_words = remainder.split()
            if r_words and r_words[0].lower().endswith("ing") and len(r_words[0]) > 4:
                new_content = f"{default_verb} " + " ".join(r_words[1:]) if len(r_words) > 1 else f"{default_verb} {remainder}"
            else:
                new_content = f"{default_verb} {remainder}"
            return f"{prefix}{new_content}", True

    # 3. If first word is in WEAK_PASSIVE_VERBS (e.g. 'worked', 'helped', 'assisted', 'handled')
    if first_word_clean in WEAK_PASSIVE_VERBS or first_word_clean in {"worked", "helped", "assisted", "did", "made", "handled", "used"}:
        new_content = f"{default_verb} " + " ".join(clean_words[1:]) if len(clean_words) > 1 else default_verb
        return f"{prefix}{new_content}", True

    # 4. If first 5 words contain a recognized strong action verb (e.g. "For iOS, implemented...", "Successfully deployed...", "Built..."):
    for w in clean_words[:5]:
        w_clean = re.sub(r"[^a-zA-Z]", "", w).lower()
        if w_clean in STRONG_ACTION_VERBS or (w_clean.endswith("ed") and len(w_clean) > 4):
            return raw, False

    # 5. If first word ends in 'ing' (gerund like 'Building', 'Designing', 'Implementing')
    if first_word_clean.endswith("ing") and len(first_word_clean) > 4:
        new_content = f"{default_verb} " + " ".join(clean_words[1:]) if len(clean_words) > 1 else default_verb
        return f"{prefix}{new_content}", True

    # 6. Complete descriptive system / project statement
    # If phrase already has a complete predicate or structure, adapt cleanly without broken articles
    adapted_content = content
    if clean_words[0].lower() not in {"a", "an", "the"} and not clean_words[0].isupper():
        adapted_content = content[0].lower() + content[1:]

    # Never produce 'Built a <word>ing,' or broken comma sequences
    if re.search(r"^[a-zA-Z]+ing\b\s*,", adapted_content):
        return raw, False

    new_content = f"{default_verb} {adapted_content}"
    return f"{prefix}{new_content}", True
