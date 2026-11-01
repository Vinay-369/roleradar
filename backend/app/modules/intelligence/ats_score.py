"""
Corporate-Grade ATS Compatibility & Audit Engine (Feature 11).

Deterministic, mathematically precise scoring adhering to corporate enterprise standards:
1. Knockout Gatekeeper filter
2. 4-Category Score Breakdown (100 Points Total):
   - Core Technical Keyword Matching (40 pts)
   - Job Title & Experience Context Alignment (30 pts)
   - Industry & Education Fit (15 pts)
   - Parsing Integrity & Formatting Risk (15 pts)
3. 3-Point Action Plan (Skill Placement, Context Optimization, Formatting Correction)
"""
import re
from dataclasses import dataclass, field

from app.modules.jobs.skill_vocabulary import canonicalize_skill_name, extract_skills_from_text

STOPWORDS = {
    "the", "and", "for", "with", "a", "an", "to", "of", "in", "on", "is", "are",
    "our", "we", "you", "your", "will", "this", "that", "as", "be", "or", "at",
    "by", "from", "it", "all", "any", "both", "each", "few", "more", "most",
}

# These words occur in almost every job description and are not useful ATS
# targets.  A resume should not gain points merely because it repeats them.
GENERIC_JD_TERMS = {
    "candidate", "candidates", "company", "employer", "employee", "role", "position",
    "job", "team", "teams", "work", "working", "experience", "years", "year", "skills",
    "skill", "knowledge", "ability", "abilities", "responsibilities", "requirements",
    "required", "preferred", "including", "looking", "seeking", "strong", "excellent",
    "good", "best", "plus", "etc", "develop", "developed", "development", "build",
    "building", "using", "use", "support", "supports", "provide", "ensure", "help",
}

STRONG_ACTION_VERBS = {
    "architected", "built", "engineered", "developed", "deployed", "optimized",
    "scaled", "automated", "designed", "implemented", "reduced", "increased",
    "accelerated", "created", "spearheaded", "integrated", "transformed",
}

STANDARD_HEADERS = {
    "technical skills", "skills", "projects", "technical projects",
    "education", "work experience", "experience", "certifications",
    "achievements", "professional summary", "summary",
}


@dataclass
class MatchGuidance:
    status: str  # "ideal" | "over_optimized" | "good" | "needs_work"
    label: str
    message: str
    target_range: str = "75% - 85%"


@dataclass
class ScoreCategory:
    category_name: str
    max_points: int
    points_awarded: int
    key_findings: str


@dataclass
class ActionPlanItem:
    type: str  # "Skill Placement" | "Context Optimization" | "Formatting Correction"
    title: str
    description: str


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
    knockout_passed: bool = True
    knockout_reason: str | None = None
    match_status: str = "High Match (>=80%)"
    categories: list[ScoreCategory] = field(default_factory=list)
    action_plan: list[ActionPlanItem] = field(default_factory=list)
    match_guidance: MatchGuidance | None = None


def _extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) >= 2}


def _keyword_coverage(resume_text: str, jd_text: str) -> int:
    jd_keywords = _extract_keywords(jd_text)
    if not jd_keywords:
        return 100
    resume_keywords = _extract_keywords(resume_text)
    target_keywords = {keyword for keyword in jd_keywords if keyword not in GENERIC_JD_TERMS}
    if not target_keywords:
        return 100
    covered = target_keywords & resume_keywords
    return round((len(covered) / len(target_keywords)) * 100)


def _normalise_skill(value: str) -> str:
    """Return one comparison key for aliases and punctuation variants."""
    canonical = canonicalize_skill_name(value)
    return re.sub(r"[^a-z0-9]+", " ", canonical.casefold()).strip()


def _target_terms(
    jd_text: str,
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Extract technical ATS targets without scoring generic JD prose.

    Provider-parsed skills are authoritative when available.  The vocabulary
    fallback keeps custom/pasted JDs useful while avoiding the old behaviour of
    treating every common English word as a keyword.
    """
    required = [str(item).strip() for item in (required_skills or []) if str(item).strip()]
    preferred = [str(item).strip() for item in (preferred_skills or []) if str(item).strip()]
    if not required and not preferred:
        extracted = extract_skills_from_text(jd_text)
        required = extracted

        # If the JD contains no recognized technical vocabulary, leave the
        # technical factor unscored instead of inventing requirements from
        # ordinary job-description prose.

    def unique(items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            key = _normalise_skill(item)
            if key and key not in seen:
                seen.add(key)
                result.append(item)
        return result

    required = unique(required)
    preferred = [item for item in unique(preferred) if _normalise_skill(item) not in {_normalise_skill(x) for x in required}]
    return required, preferred


def _target_coverage(
    resume_text: str,
    required_skills: list[str],
    preferred_skills: list[str],
) -> tuple[int, int]:
    """Return required coverage and weighted all-target coverage."""
    resume_terms = {_normalise_skill(item) for item in extract_skills_from_text(resume_text)}
    # A skill can be present in prose even when the extractor does not return
    # it because it is a custom technology; compare normalized phrases too.
    resume_normalized = re.sub(r"[^a-z0-9+#.]+", " ", resume_text.casefold())

    def covered(skill: str) -> bool:
        key = _normalise_skill(skill)
        return key in resume_terms or bool(key and re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", resume_normalized))

    required_hits = sum(covered(skill) for skill in required_skills)
    preferred_hits = sum(covered(skill) for skill in preferred_skills)
    required_score = round(required_hits / len(required_skills) * 100) if required_skills else 100
    total_count = len(required_skills) + len(preferred_skills)
    total_score = round((required_hits + 0.5 * preferred_hits) / (len(required_skills) + 0.5 * len(preferred_skills)) * 100) if total_count else 100
    return required_score, total_score


def _check_knockout(resume_text: str, jd_text: str) -> tuple[bool, str | None]:

    """Evaluates absolute non-negotiable requirements mentioned in the JD."""
    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()

    # Only apply a knockout when the JD uses an explicit mandatory phrase.
    # A casual mention of citizenship or clearance must not disqualify someone.
    if re.search(r"\b(?:us|u\.s\.?|united states)\s+citizenship\s+(?:is\s+)?required\b", jd_lower):
        if not re.search(r"\b(?:us|u\.s\.?|united states)\s+citizen(?:ship)?\b", resume_lower):
            return False, "Failed Knockout: Job requires US Citizenship."
    if re.search(r"\b(?:active\s+)?security\s+clearance\s+(?:is\s+)?required\b", jd_lower):
        if not re.search(r"\b(?:active\s+)?(?:security\s+)?clearance\b", resume_lower):
            return False, "Failed Knockout: Job requires an active security clearance."

    return True, None


def _calculate_keyword_density(resume_text: str, jd_text: str) -> tuple[int, float, bool]:
    jd_keywords = _extract_keywords(jd_text)
    resume_words = [w.lower() for w in re.findall(r"[a-zA-Z0-9+.#-]+", resume_text)]
    total_resume_words = max(1, len(resume_words))

    if not jd_keywords:
        return 100, 1.0, False

    resume_keyword_set = set(resume_words)
    covered = {
        keyword for keyword in jd_keywords
        if keyword not in GENERIC_JD_TERMS and keyword in resume_keyword_set
    }
    coverage = round((len(covered) / len(jd_keywords)) * 100)

    # ATS Keyword Density measures individual term repetition frequency (keyword stuffing guard).
    # Repeating a single target keyword excessively (>3.5% of total document words) triggers over-optimization flags.
    word_counts = {}
    for w in resume_words:
        if w in covered:
            word_counts[w] = word_counts.get(w, 0) + 1

    max_keyword_count = max(word_counts.values()) if word_counts else 0
    max_single_density = round((max_keyword_count / total_resume_words) * 100, 2)

    # One occurrence in a short resume is normal. Require repeated use before
    # flagging stuffing; this avoids penalizing concise fresher resumes.
    over_optimized = max_single_density > 3.5 and max_keyword_count >= 3
    return coverage, max_single_density, over_optimized


def _get_match_guidance(overall: int, over_optimized: bool) -> MatchGuidance:
    if 75 <= overall <= 85 and not over_optimized:
        return MatchGuidance(
            status="ideal",
            label="Ideal Match Zone",
            message="Optimal fit for both corporate ATS filtering and human recruiter review (75%–85% target range).",
        )
    elif overall > 85 or over_optimized:
        return MatchGuidance(
            status="over_optimized",
            label="High Optimization Match",
            message="High match score (>=85%). Meets automated corporate shortlisting benchmarks.",
        )
    elif 50 <= overall < 75:
        return MatchGuidance(
            status="good",
            label="Mid Match Zone",
            message="Solid foundation. Adding target skills and stronger metric verbs will elevate into the 85%+ bracket.",
        )
    else:
        return MatchGuidance(
            status="needs_work",
            label="Low Match Zone",
            message="Significant gap between resume and JD requirements. Review critical technical keywords.",
        )


def compute_ats_score(
    resume_text: str,
    jd_text: str,
    parseability_score: int,
    recruiter_impact_score: int,
    skill_match_score: int | None,
    role_match_score: int | None,
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
) -> ATSScoreResult:
    # Missing evidence is neutral when the caller cannot calculate a factor;
    # it is not the same as evidence that the candidate failed the factor.
    role_match_score = role_match_score if role_match_score is not None else 50

    target_required, target_preferred = _target_terms(jd_text, required_skills, preferred_skills)
    extracted_required_score, target_keyword_coverage = _target_coverage(
        resume_text, target_required, target_preferred
    )
    if skill_match_score is None:
        skill_match_score = extracted_required_score if target_required else 0
    else:
        skill_match_score = max(0, min(100, skill_match_score))
    # 1. Knockout Check
    knockout_passed, knockout_reason = _check_knockout(resume_text, jd_text)
    if not knockout_passed:
        return ATSScoreResult(
            overall=0,
            keyword_coverage=0,
            required_skills=0,
            role_alignment=0,
            structure=parseability_score,
            formatting=parseability_score,
            readability=recruiter_impact_score,
            keyword_density=0.0,
            over_optimization_warning=False,
            knockout_passed=False,
            knockout_reason=knockout_reason,
            match_status="Failed Knockout Criteria",
            categories=[
                ScoreCategory("Technical Keywords", 40, 0, "Disqualified at Initial Knockout Gatekeeper."),
                ScoreCategory("Experience Context", 30, 0, "Disqualified at Initial Knockout Gatekeeper."),
                ScoreCategory("Education & Domain", 15, 0, "Disqualified at Initial Knockout Gatekeeper."),
                ScoreCategory("Parsing & Formatting", 15, 0, "Disqualified at Initial Knockout Gatekeeper."),
            ],
            action_plan=[
                ActionPlanItem("Skill Placement", "Verify Eligibility Requirements", knockout_reason or "Knockout failed."),
            ],
            match_guidance=MatchGuidance("needs_work", "Failed Knockout", knockout_reason or "Knockout criteria not met."),
        )

    # Density remains a stuffing guard, while coverage is based on actual
    # technical targets rather than all words in the job description.
    _, keyword_density, over_optimization_warning = _calculate_keyword_density(resume_text, jd_text)
    keyword_coverage = target_keyword_coverage if target_required or target_preferred else 0

    # Category 1: Technical Keywords (Weight: 40 Points)
    # Exact Match (25 pts) + Semantic Match (15 pts) - Penalty (5 pts if over_optimized)
    has_skill_targets = bool(target_required or target_preferred)
    exact_pts = round(
        25 if not has_skill_targets else min(25, ((skill_match_score or 0) / 100.0) * 25)
    )
    semantic_pts = round(15 if not has_skill_targets else min(15, (keyword_coverage / 100.0) * 15))
    penalty = 5 if over_optimization_warning else 0
    cat1_score = max(0, min(40, exact_pts + semantic_pts - penalty))
    if not has_skill_targets:
        cat1_findings = "No explicit employer skill targets were available; technical alignment is not scored."
    elif penalty == 0:
        cat1_findings = f"Exact technical skill alignment: {exact_pts}/25 pts, semantic coverage: {semantic_pts}/15 pts."
    else:
        cat1_findings = f"Exact match: {exact_pts}/25, semantic match: {semantic_pts}/15. Deducted 5 pts for high keyword density ({keyword_density}%)."

    # Category 2: Experience Context Alignment (Weight: 30 Points)
    # Title/Role Match (15 pts) + Action & Impact Verbs (15 pts)
    role_pts = round(min(15, (role_match_score / 100.0) * 15))
    action_pts = round(min(15, (recruiter_impact_score / 100.0) * 15))
    cat2_score = max(0, min(30, role_pts + action_pts))
    cat2_findings = f"Target role match: {role_pts}/15 pts. Action verbs and metric quantifications: {action_pts}/15 pts."

    # Category 3: Industry & Education Fit (Weight: 15 Points)
    # Do not award CS-specific points to every candidate.  Education is scored
    # only when the JD asks for it; an absent requirement is a neutral fit.
    education_requested = bool(re.search(
        r"\b(?:bachelor|master|degree|b\.?tech|b\.?e\.?|bca|mca|computer science|engineering|mba|phd|diploma)\b",
        jd_text,
        re.IGNORECASE,
    )) and not bool(re.search(
        r"\b(?:no|not|without|doesn['’]?t\s+require)\s+(?:an?\s+)?(?:formal\s+)?(?:education|degree|qualification)s?\b|\b(?:education|degree|qualification)(?:\s+requirement)?\s+is\s+not\b",
        jd_text,
        re.IGNORECASE,
    ))
    if not education_requested:
        edu_pts = 10
    else:
        has_degree_evidence = bool(re.search(
            r"\b(?:bachelor|master|degree|b\.?tech|b\.?e\.?|bca|mca|computer science|engineering|mba|phd|diploma)\b",
            resume_text,
            re.IGNORECASE,
        ))
        edu_pts = 10 if has_degree_evidence else 0
    has_domain = bool(target_required and skill_match_score and skill_match_score >= 50)
    domain_pts = 5 if has_domain else (2 if not target_required else 0)
    cat3_score = edu_pts + domain_pts
    edu_note = "JD has no explicit education requirement; neutral score applied" if not education_requested else "Education requirement evidence"
    cat3_findings = f"{edu_note}: {edu_pts}/10 pts. Domain competency evidence: {domain_pts}/5 pts."

    # Category 4: Parsing Integrity & Formatting Risk (Weight: 15 Points)
    # Structural Headers (10 pts) + Date Formatting (5 pts)
    headers_pts = round(min(10, (parseability_score / 100.0) * 10))
    has_valid_dates = bool(re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|20\d\d)\b", resume_text))
    dates_pts = 5 if has_valid_dates else 2
    cat4_score = headers_pts + dates_pts
    cat4_findings = f"Standard ATS headers & single-column layout: {headers_pts}/10 pts. Chronological date structure: {dates_pts}/5 pts."

    total_score = min(100, max(0, cat1_score + cat2_score + cat3_score + cat4_score))

    # Match Status Label
    if total_score >= 80:
        match_status = "High Match (>=80%)"
    elif total_score >= 50:
        match_status = "Mid Match (50-79%)"
    else:
        match_status = "Low Match (<50%)"

    categories = [
        ScoreCategory("Technical Keywords", 40, cat1_score, cat1_findings),
        ScoreCategory("Experience Context", 30, cat2_score, cat2_findings),
        ScoreCategory("Education & Domain", 15, cat3_score, cat3_findings),
        ScoreCategory("Parsing & Formatting", 15, cat4_score, cat4_findings),
    ]

    action_plan = [
        ActionPlanItem(
            type="Skill Placement",
            title="Prioritize High-Yield Technical Keywords",
            description="Move primary required skills from the JD to the beginning of your Technical Skills row.",
        ),
        ActionPlanItem(
            type="Context Optimization",
            title="Amplify Project Action Verbs with Metrics",
            description="Ensure every project bullet opens with a decisive action verb (Architected, Optimized, Built) and metric outcome.",
        ),
        ActionPlanItem(
            type="Formatting Correction",
            title="Verify Clean Single-Column Chronology",
            description="Keep all dates in standard Month YYYY format and verify GitHub/LinkedIn links are active.",
        ),
    ]

    guidance = _get_match_guidance(total_score, over_optimization_warning)

    return ATSScoreResult(
        overall=total_score,
        keyword_coverage=keyword_coverage,
        required_skills=skill_match_score,
        role_alignment=role_match_score,
        structure=parseability_score,
        formatting=parseability_score,
        readability=recruiter_impact_score,
        keyword_density=keyword_density,
        over_optimization_warning=over_optimization_warning,
        knockout_passed=True,
        knockout_reason=None,
        match_status=match_status,
        categories=categories,
        action_plan=action_plan,
        match_guidance=guidance,
    )
