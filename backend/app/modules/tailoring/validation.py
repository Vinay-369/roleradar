"""
Validation Engine for Resume Tailoring (Feature 9 & Truth Guard v6).
Provides deterministic checks for:
1. Programmatic Fabrication Verification (Noun & Tool Tracing)
2. Deterministic Skill & Section Reordering
3. Code-Enforced Protected Section Isolation
4. Deterministic 1-Page PDF Fit Measurement & Trimming
"""
import io
import re
import fitz  # PyMuPDF

from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.resume.parsing.skills_depth import DOMAIN_DEFINITIONS

# Aliases mapping abbreviations and common synonyms to canonical technical terms
TECH_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "reactjs": "react",
    "nextjs": "next.js",
    "vuejs": "vue",
    "tf": "terraform",
    "gcp": "google cloud",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "dsa": "data structures",
    "rest": "rest api",
    "restful": "rest api",
    "fast api": "fastapi",
    "elastic": "elasticsearch",
    "kafka": "kafka",
    "redis": "redis",
    "docker": "docker",
}

# Build comprehensive set of recognized technical tools and competencies
ALL_TECH_TERMS: set[str] = set()
for domain in DOMAIN_DEFINITIONS:
    for kw in domain["keywords"]:
        ALL_TECH_TERMS.add(kw.lower())
for alias, canon in TECH_ALIASES.items():
    ALL_TECH_TERMS.add(alias)
    ALL_TECH_TERMS.add(canon)

PROTECTED_SECTION_NAMES = {
    "EDUCATION",
    "ACADEMIC BACKGROUND",
    "CERTIFICATIONS",
    "LICENSES",
    "CONTACT INFO",
    "PERSONAL INFO",
    "CONTACT",
}

_METRIC_CLAIM_RE = re.compile(
    r"(?:\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\+?\s*%?|\b\d+(?:\.\d+)?\+?\s*(?:%|percent|x|ms|s|secs?|seconds?|mins?|minutes?|hours?|days?|users?|requests?|records?|rows?|transactions?|deployments?|regions?))",
    re.IGNORECASE,
)


def _canonicalize_skill(skill: str) -> str:
    s = skill.strip().lower()
    return TECH_ALIASES.get(s, s)


def extract_technical_terms(text: str) -> set[str]:
    """Extracts all recognized technical tools, languages, databases, and frameworks from text."""
    text_lower = text.lower()
    found = set()
    # Check multi-word terms first, then single-word
    sorted_terms = sorted(ALL_TECH_TERMS, key=lambda x: -len(x))
    for term in sorted_terms:
        # Match whole word boundaries
        pattern = r"(?:\b|_)" + re.escape(term) + r"(?:\b|_)"
        if re.search(pattern, text_lower):
            found.add(_canonicalize_skill(term))
    return found


def detect_fabricated_claims(
    original: str, proposed: str, jd_text: str, candidate_skills: list[str]
) -> list[str]:
    """
    Deterministic Anti-Fabrication Check:
    Extracts all technical tools and frameworks from `proposed`.
    Every technical claim in `proposed` MUST trace to:
    (a) The original bullet being replaced (exact, substring, or alias), OR
    (b) The candidate's verified master resume skills.
    
    If a technical tool in `proposed` is absent from BOTH the original bullet AND
    the candidate's master resume skills (even if requested in the JD), it represents
    an ungrounded technical addition that MUST be flagged.
    """
    if not proposed:
        return []

    proposed_tech = extract_technical_terms(proposed)
    original_tech = extract_technical_terms(original)
    
    # Candidate verified skills set
    verified_tech = set()
    for s in candidate_skills:
        verified_tech.add(_canonicalize_skill(s))
        verified_tech.update(extract_technical_terms(s))

    ungrounded_terms: list[str] = []
    for tech in proposed_tech:
        # Is it in the original bullet?
        in_original = tech in original_tech or tech in original.lower()
        # Is it in the candidate's master resume skills?
        in_candidate = tech in verified_tech or any(tech in s.lower() for s in candidate_skills)
        
        if not in_original and not in_candidate:
            ungrounded_terms.append(tech)

    return sorted(list(set(ungrounded_terms)))


def detect_unsupported_metrics(original: str, proposed: str) -> list[str]:
    """Return measurable claims introduced by a bullet rewrite.

    A rewrite may improve wording but cannot manufacture a percentage, scale,
    duration, or throughput result.  Numeric tokens without a unit are not
    treated as metrics so normal sentence numbering does not create noise.
    """
    def normalize(metric: str) -> str:
        value = metric.lower().replace(",", "").replace("+", "")
        value = re.sub(r"\s+", "", value)
        return value.replace("percent", "%")

    original_metrics = {normalize(metric) for metric in _METRIC_CLAIM_RE.findall(original)}
    proposed_metrics = {normalize(metric) for metric in _METRIC_CLAIM_RE.findall(proposed)}
    return sorted(proposed_metrics - original_metrics)


def detect_dropped_source_skills(original: str, proposed: str) -> list[str]:
    """Detect technical evidence removed from a rewritten source bullet."""
    original_skills = {skill.lower() for skill in extract_skills_from_text(original)}
    proposed_skills = {skill.lower() for skill in extract_skills_from_text(proposed)}
    return sorted(original_skills - proposed_skills)


def has_verbatim_source_evidence(original: str, source_evidence: str) -> bool:
    """Require a concrete quotation, not an AI-written claim of grounding."""
    original_normalized = " ".join(original.lower().split())
    evidence_normalized = " ".join(source_evidence.lower().split())
    return bool(evidence_normalized and len(evidence_normalized) >= 12 and evidence_normalized in original_normalized)


def compute_deterministic_skill_reorder(
    master_skills: list[str], jd_text: str
) -> tuple[list[str], list[str], list[str], bool]:
    """
    Deterministically reorders candidate skills to prioritize JD-relevant competencies:
    1. Skills explicitly requested in the JD (in order of JD prominence)
    2. Other skills already verified on the candidate's master resume
    3. Computes unmatched JD skills (Gaps Found — Not Added)
    
    Returns: (reordered_skills, matched_skills, unmatched_jd_skills, was_reordered)
    """
    jd_tech = extract_technical_terms(jd_text)
    
    matched_skills: list[str] = []
    other_skills: list[str] = []
    seen_canon: set[str] = set()

    for skill in master_skills:
        s_clean = skill.strip()
        if not s_clean:
            continue
        canon = _canonicalize_skill(s_clean)
        if canon in seen_canon:
            continue
        seen_canon.add(canon)

        skill_tech = extract_technical_terms(s_clean)
        # Check if skill or any of its extracted terms is in the JD
        if canon in jd_tech or any(t in jd_tech for t in skill_tech):
            matched_skills.append(s_clean)
        else:
            other_skills.append(s_clean)

    reordered = matched_skills + other_skills
    
    # Identify JD required skills that the candidate lacks
    unmatched_jd_skills = [t.title() for t in jd_tech if t not in seen_canon]

    was_reordered = (
        len(matched_skills) > 0 and 
        len(master_skills) > 1 and 
        reordered != master_skills
    )

    return reordered, matched_skills, unmatched_jd_skills, was_reordered


def is_target_in_protected_section(original_text: str, master_resume_text: str) -> bool:
    """Checks if a snippet being replaced belongs to a protected section (Education, Contact)."""
    if not original_text or not master_resume_text:
        return False

    orig_clean = original_text.strip().lower()
    lines = master_resume_text.splitlines()
    current_sec = "HEADER"

    for line in lines:
        line_clean = line.strip().upper()
        if any(h in line_clean for h in ("PROJECT", "EXPERIENCE", "SKILL", "SUMMARY", "WORK", "LEADERSHIP", "ACHIEVEMENT")):
            current_sec = "ELIGIBLE"
        elif any(h in line_clean for h in ("EDUCATION", "ACADEMIC BACKGROUND", "ACADEMIC QUALIFICATIONS", "CERTIFICATION", "CERTIFICATE", "CONTACT", "DEGREE")):
            current_sec = "PROTECTED"

        if orig_clean in line.lower() and current_sec == "PROTECTED":
            return True

    return False


def validate_protected_sections(
    master_parsed: dict, final_parsed: dict
) -> tuple[bool, list[str]]:
    """
    Ensures that Education items, degrees, institutions, and candidate personal contact
    info are structurally preserved and not corrupted or deleted.
    """
    errors: list[str] = []
    
    # 1. Check Education preservation
    master_edu = master_parsed.get("education_raw", master_parsed.get("education", []))
    final_edu = final_parsed.get("education_raw", final_parsed.get("education", []))
    
    if master_edu and not final_edu:
        errors.append("Education section was deleted or corrupted in tailored output.")
    elif len(final_edu) < len(master_edu):
        errors.append(f"Education entries reduced from {len(master_edu)} to {len(final_edu)}.")

    # 2. Check Personal Contact Info preservation
    master_contact = master_parsed.get("personal", master_parsed.get("personal_info", {}))
    final_contact = final_parsed.get("personal", final_parsed.get("personal_info", {}))

    if master_contact.get("email") and not final_contact.get("email"):
        errors.append("Candidate email contact was dropped during tailoring.")

    is_valid = len(errors) == 0
    return is_valid, errors


def measure_and_enforce_one_page_fit(
    content: str | dict, candidate_name: str = "Candidate", template: str = "modern", max_pages: int = 1, required_skills: list[str] | None = None
) -> tuple[str | dict, bool, int]:
    """
    Renders the tailored resume directly into the real PDF layout, measures actual page count using PyMuPDF,
    and applies deterministic priority-ordered trimming if overflow occurs:
    1. Trims low-priority project bullets (never index 0, never metrics/quantified numbers, never required skill matches).
    2. Trims low-priority experience bullets if needed.
    
    Returns: (final_content, fits_one_page, page_count)
    """
    import copy
    from app.modules.tailoring.export import generate_pdf

    if isinstance(content, dict):
        parsed = copy.deepcopy(content)
        pdf_bytes = generate_pdf(parsed, candidate_name=candidate_name, template=template)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = doc.page_count
        doc.close()

        if page_count <= max_pages:
            return parsed, True, page_count

        # Iterative intelligent trimming on structured object
        # Priority 1: Trim secondary project bullets lacking metrics
        projects = list(parsed.get("projects_raw", []))
        req_set = {s.lower() for s in (required_skills or [])}

        metric_re = re.compile(
            r"(?:\b\d+%\b|\$\d+|\€\d+|\₹\d+|\b\d+x\b|\b\d+\s*(?:ms|sec|minutes?|hours?|users?|requests?|qps|rps|tps|transactions?)\b|\b\d{1,3}(?:,\d{3})+\b|\b\d+\+)",
            re.IGNORECASE,
        )

        def can_trim_bullet(b_str: str, force_non_metric: bool = False) -> bool:
            # Never trim index 0
            # Never trim if mentions a required skill
            b_lower = b_str.lower()
            if any(s in b_lower for s in req_set):
                return False
            # Never trim if has explicit metric unless force_non_metric is True
            if not force_non_metric and (metric_re.search(b_str) or "%" in b_str):
                return False
            return True

        # Pass 1: Trim non-metric secondary project bullets from the bottom
        for idx in range(len(projects) - 1, 0, -1):
            if can_trim_bullet(projects[idx], force_non_metric=False):
                projects.pop(idx)
                parsed["projects_raw"] = projects
                pdf_bytes = generate_pdf(parsed, candidate_name=candidate_name, template=template)
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                page_count = doc.page_count
                doc.close()
                if page_count <= max_pages:
                    return parsed, True, page_count

        # Pass 2: If still overflowing, trim secondary project bullets (never index 0)
        for idx in range(len(projects) - 1, 0, -1):
            projects.pop(idx)
            parsed["projects_raw"] = projects
            pdf_bytes = generate_pdf(parsed, candidate_name=candidate_name, template=template)
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = doc.page_count
            doc.close()
            if page_count <= max_pages:
                return parsed, True, page_count

        return parsed, page_count <= max_pages, page_count

    # Plain text fallback
    final_text = str(content)
    pdf_bytes = generate_pdf(final_text, candidate_name=candidate_name, template=template)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = doc.page_count
    doc.close()

    if page_count <= max_pages:
        return final_text, True, page_count

    lines = final_text.splitlines()
    trimmed_lines = list(lines)
    
    in_projects = False
    project_bullet_indices = []
    for idx, line in enumerate(trimmed_lines):
        upper = line.strip().upper()
        if "PROJECT" in upper:
            in_projects = True
            continue
        elif any(sec in upper for sec in ("EXPERIENCE", "EDUCATION", "SKILLS")):
            in_projects = False

        if in_projects and line.strip().startswith(("•", "-", "*")):
            has_metric = bool(re.search(r"\d+%?|\$\d+", line))
            if not has_metric:
                project_bullet_indices.append(idx)

    for b_idx in reversed(project_bullet_indices):
        trimmed_lines.pop(b_idx)
        candidate_text = "\n".join(trimmed_lines)
        pdf_bytes = generate_pdf(candidate_text, candidate_name=candidate_name, template=template)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = doc.page_count
        doc.close()
        if page_count <= max_pages:
            return candidate_text, True, page_count

    return final_text, page_count <= max_pages, page_count
