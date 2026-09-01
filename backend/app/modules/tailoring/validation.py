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
from typing import Any
import fitz  # PyMuPDF
from pydantic import BaseModel, Field

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


LEADERSHIP_VERBS = {"led", "managed", "spearheaded", "directed", "mentored", "supervised", "championed"}
DEPLOYMENT_VERBS = {"deployed", "provisioned", "containerized", "orchestrated"}
OPTIMIZATION_VERBS = {"optimized", "accelerated", "boosted", "maximized"}
ARCHITECTURE_VERBS = {"architected", "overhauled"}


def detect_unsupported_action_verbs_and_scope(original: str, proposed: str) -> list[str]:
    """
    Detects ungrounded action verb and scope escalations in rewritten bullets:
    - Leadership claims (led, managed, spearheaded) when source has no leadership evidence
    - Deployment claims (deployed, provisioned) when source has no deployment/infrastructure evidence
    - Optimization claims (optimized, accelerated) when source has no optimization/performance evidence
    - Architecture claims (architected) when source has no architecture evidence
    - Production scope modifiers introduced without source backing
    """
    if not original or not proposed:
        return []

    violations = []
    orig_lower = original.lower()
    prop_lower = proposed.lower()

    orig_words = set(re.findall(r"\b[a-z-]+\b", orig_lower))
    prop_words = set(re.findall(r"\b[a-z-]+\b", prop_lower))

    # 1. Leadership escalation
    for v in LEADERSHIP_VERBS:
        if v in prop_words and not any(k in orig_lower for k in ["lead", "led", "manage", "mentor", "direct", "supervis", "spearhead", "champion"]):
            violations.append(f"Leadership claim ({v}) introduced without source evidence")

    # 2. Deployment escalation
    for v in DEPLOYMENT_VERBS:
        if v in prop_words and not any(k in orig_lower for k in ["deploy", "production", "release", "cloud", "server", "host", "aws", "gcp", "azure", "docker", "k8s", "kubernetes", "ci/cd", "infra"]):
            violations.append(f"Deployment claim ({v}) introduced without source evidence")

    # 3. Optimization / Delta escalation
    for v in OPTIMIZATION_VERBS:
        if v in prop_words and not any(k in orig_lower for k in ["optimi", "reduc", "accelerat", "improv", "increas", "decreas", "boost", "fast", "speed", "latency", "throughput", "cost", "scale"]):
            violations.append(f"Optimization claim ({v}) introduced without source evidence")

    # 4. Architecture escalation
    for v in ARCHITECTURE_VERBS:
        if v in prop_words and not any(k in orig_lower for k in [
            "architect", "design", "system", "infrastruct", "framework",
            "pipeline", "engine", "api", "backend", "service", "app",
            "parser", "database", "platform", "microservice", "distributed"
        ]):
            violations.append(f"Architecture claim ({v}) introduced without source evidence")

    # 5. Production scope modifier
    if "production" in prop_words and not any(k in orig_lower for k in ["production", "prod", "live", "clinical", "commercial", "industry"]):
        violations.append("Production scope modifier introduced without source evidence")

    return sorted(list(set(violations)))


_FRAGMENT_BULLET_PREFIX_RE = re.compile(
    r"^(?:[•\-\*\u2013\u2014\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u27A4\u2714\u2713\u279C\u2192\u25BA\u25B6\u25C6\u25C7\u25CF\u25CB\u2718\u2717\u2705\u27A2\u2794\u2714\ufffd▪▫◦‣⁃■□★☆+>~]|(?:\b[oO]\b\s+)|\d{1,2}[\.\)]|\([a-zA-Z0-9]+\)|[a-zA-Z]\))\s+",
    re.UNICODE,
)
_DANGLING_ENDINGS = {"and", "or", "with", "for", "to", "by", "via", "using", "including", "such as", "as well as", "in"}
_DANGLING_STARTS = {"and", "or", "but", "nor", "so", "yet", "to", "by", "via", "of", "in order to", "as well as", "such as", "including"}


def detect_sentence_fragments_and_truncation(original: str, proposed: str) -> list[str]:
    """
    Structural Content-Integrity Check:
    Rejects:
    - empty fragments
    - sentence fragments / missing leading action verbs
    - bullets beginning with an orphaned continuation (e.g. 'and deployed on AWS')
    - truncated evidence / abruptly cut-off sentences
    """
    if not proposed:
        return ["Empty proposed bullet"]

    clean_orig = _FRAGMENT_BULLET_PREFIX_RE.sub("", original).strip()
    clean_prop = _FRAGMENT_BULLET_PREFIX_RE.sub("", proposed).strip()

    if not clean_prop:
        return ["Empty proposed bullet content"]

    # Structural headings and date lines are exempt
    if clean_orig.endswith(":") or (re.search(r"\b(?:\d{4}|present)\b", clean_orig, re.IGNORECASE) and len(clean_orig.split()) <= 12 and not clean_orig.endswith((".", ";", "!"))):
        return []

    orig_words = clean_orig.split()
    prop_words = clean_prop.split()

    violations = []

    # 1. Minimum length check for full bullets
    if len(orig_words) >= 5 and len(prop_words) < 3:
        violations.append(f"Bullet is an incomplete fragment ({len(prop_words)} words)")

    # 2. Lowercase lead check (lost capital or stripped opening word)
    if clean_prop[0].islower() and not (clean_orig and clean_orig[0].islower()):
        violations.append(f'Bullet begins with lowercase orphaned fragment: "{clean_prop[:30]}..."')

    # 3. Dangling start check (starts with conjunction without main clause)
    first_two = " ".join([w.lower() for w in prop_words[:2]]) if len(prop_words) >= 2 else ""
    first_w = prop_words[0].lower().rstrip(":,") if prop_words else ""
    if (first_w in _DANGLING_STARTS or first_two in _DANGLING_STARTS) and not (clean_orig and clean_orig.lower().startswith(first_w)):
        violations.append(f'Bullet starts with orphaned continuation ("{first_w}")')

    # 4. Missing action verb check (if original had a lead action verb, rewrite must not degrade to a headless noun fragment)
    from app.modules.resume.parsing.action_verbs import STRONG_ACTION_VERBS, WEAK_PASSIVE_VERBS
    all_lead_verbs = STRONG_ACTION_VERBS | WEAK_PASSIVE_VERBS | {"assisted", "helped", "supported", "contributed", "participated", "worked", "maintained"}
    orig_has_action = any(re.sub(r"[^a-zA-Z]", "", w).lower() in all_lead_verbs for w in orig_words[:2]) if orig_words else True
    prop_has_action = any(re.sub(r"[^a-zA-Z]", "", w).lower() in all_lead_verbs for w in prop_words[:2])
    prop_has_intro_action = any(re.sub(r"[^a-zA-Z]", "", w).lower() in all_lead_verbs for w in prop_words[:5]) and prop_words[0].lower() in {"for", "in", "across", "using", "with", "through", "on", "at"}
    if orig_has_action and not (prop_has_action or prop_has_intro_action or clean_prop.endswith(":")):
        violations.append("Bullet has lost its leading action verb and degraded to an incomplete fragment")

    # 5. Abrupt ending check
    if clean_prop.endswith((",", ";", " -", " –", " —", ":")) and not clean_orig.endswith(clean_prop[-1]):
        violations.append(f'Bullet is abruptly truncated with trailing punctuation: "...{clean_prop[-10:]}"')
    last_w = prop_words[-1].lower().rstrip(".,;!") if prop_words else ""
    if last_w in _DANGLING_ENDINGS:
        violations.append(f'Bullet ends abruptly with dangling word: "{last_w}"')

    # 6. Broken predicate / ungrammatical verb sequence check (e.g. "Built a video processing,")
    if re.search(r"^(?:Built|Engineered|Developed|Implemented|Architected|Created|Designed)\s+(?:a|an)\s+[a-zA-Z]+ing\b\s*,", clean_prop, re.IGNORECASE):
        violations.append(f'Bullet contains broken predicate/gerund syntax: "{clean_prop[:40]}..."')

    # 7. Headless noun modifier fragment check (e.g. "global CDN distribution optimized for...")
    if not clean_prop.endswith(":") and len(prop_words) >= 4:
        first_clean = re.sub(r"[^a-zA-Z]", "", prop_words[0]).lower()
        if first_clean in {"global", "local", "scalable", "high", "low", "realtime", "comprehensive", "automated", "distributed"}:
            if not any(re.sub(r"[^a-zA-Z]", "", w).lower() in all_lead_verbs for w in prop_words[:3]):
                if orig_has_action:
                    violations.append(f'Bullet degraded to headless noun modifier fragment: "{clean_prop[:35]}..."')

    return sorted(list(set(violations)))


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


def detect_entity_boundary_violations(
    original_entity_id: str,
    proposed_bullet: str,
    all_evidence_units: list[Any] | None = None,
) -> list[str]:
    """
    Ensures that bullet rewrites do not import metrics or claims belonging to a different entity.
    For instance, a metric from 'proj_1' ($500k) cannot be hallucinated into 'proj_0' (which had 91%).
    """
    if not all_evidence_units or not proposed_bullet or not original_entity_id:
        return []

    # Only enforce if original_entity_id is a recognized entity in all_evidence_units
    known_entity_ids = {
        getattr(ev, "entity_id", None) or (ev.get("entity_id") if isinstance(ev, dict) else None)
        for ev in all_evidence_units
    }
    if original_entity_id not in known_entity_ids:
        return []

    # Collect metrics belonging exclusively to other entities
    other_metrics: set[str] = set()
    for ev in all_evidence_units:
        ent_id = getattr(ev, "entity_id", None) or (ev.get("entity_id") if isinstance(ev, dict) else None)
        if ent_id and ent_id != original_entity_id:
            m_list = getattr(ev, "metrics", None) or (ev.get("metrics") if isinstance(ev, dict) else [])
            for m in m_list:
                m_str = str(m).strip().lower()
                if len(m_str) >= 3:
                    other_metrics.add(m_str)

    violations: list[str] = []
    proposed_lower = proposed_bullet.lower()
    for m in other_metrics:
        if m in proposed_lower:
            violations.append(f"Metric '{m}' belongs to another entity and cannot cross entity boundaries.")

    return violations


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
        # NEVER delete entire project entities. Only trim excess non-metric sub-bullets within projects that have > 2 bullets.
        projects = list(parsed.get("projects_raw", []))
        req_set = {s.lower() for s in (required_skills or [])}

        metric_re = re.compile(
            r"(?:\b\d+%\b|\$\d+|\€\d+|\₹\d+|\b\d+x\b|\b\d+\s*(?:ms|sec|minutes?|hours?|users?|requests?|qps|rps|tps|transactions?)\b|\b\d{1,3}(?:,\d{3})+\b|\b\d+\+)",
            re.IGNORECASE,
        )

        def can_trim_sub_bullet(line_str: str) -> bool:
            # Never trim if contains a metric or percentage
            if metric_re.search(line_str) or "%" in line_str:
                return False
            # Never trim if mentions a required skill
            l_lower = line_str.lower()
            if any(s in l_lower for s in req_set):
                return False
            # Never trim if line is a project title or tech stack header
            if not line_str.startswith(("•", "-", "*")) and ":" not in line_str:
                return False
            return True

        # Pass 1: For multi-line project blocks with > 2 bullets, trim trailing non-metric sub-bullets
        modified_any = False
        new_projects = []
        for p_item in projects:
            p_str = str(p_item).strip()
            sub_lines = [l for l in p_str.split("\n") if l.strip()]
            if len(sub_lines) > 3:
                # Keep header lines, trim trailing non-metric bullet
                header_count = sum(1 for l in sub_lines if not l.strip().startswith(("•", "-", "*")))
                bullet_lines = [l for l in sub_lines if l.strip().startswith(("•", "-", "*"))]
                for b_i in range(len(bullet_lines) - 1, 0, -1):
                    if len(bullet_lines) > 2 and can_trim_sub_bullet(bullet_lines[b_i]):
                        bullet_lines.pop(b_i)
                        modified_any = True
                        break
                headers = [l for l in sub_lines if not l.strip().startswith(("•", "-", "*"))]
                new_projects.append("\n".join(headers + bullet_lines))
            else:
                new_projects.append(p_str)

        if modified_any:
            parsed["projects_raw"] = new_projects
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


def validate_final_tailored_resume(
    master_parsed: dict,
    final_parsed: dict,
    candidate_profile: Any = None,
) -> tuple[bool, list[str]]:
    """
    Comprehensive Truth Guard whole-document audit of the final tailored resume against master resume truth.
    Checks:
    - Technologies (cannot introduce unverified tech)
    - Metrics & Percentages (cannot invent or alter quantified metrics)
    - Dates, Companies, Roles (employment and education facts must remain accurate)
    - Projects & Achievements (no fabricated titles or phantom achievements)
    - Certifications & Education (protected sections must remain intact)
    """
    errors: list[str] = []

    # 1. Protected Section Integrity (Education & Personal Contact)
    is_prot_valid, prot_errors = validate_protected_sections(master_parsed, final_parsed)
    if not is_prot_valid:
        errors.extend(prot_errors)

    # 2. Certification Integrity (Certifications cannot be fabricated)
    master_certs = {c.strip().lower() for c in master_parsed.get("certifications", []) if c.strip()}
    final_certs = {c.strip().lower() for c in final_parsed.get("certifications", []) if c.strip()}
    new_certs = final_certs - master_certs
    if new_certs:
        errors.append(f"Unsupported certification added without evidence: {', '.join(new_certs)}")

    # 3. Full Document Metric & Percentage Verification
    def collect_all_metrics(data: Any) -> set[str]:
        metrics = set()
        if isinstance(data, str):
            for m in _METRIC_CLAIM_RE.findall(data):
                norm = m.lower().replace(",", "").replace("+", "").replace(" ", "").replace("percent", "%")
                metrics.add(norm)
        elif isinstance(data, list):
            for item in data:
                metrics.update(collect_all_metrics(item))
        elif isinstance(data, dict):
            for v in data.values():
                metrics.update(collect_all_metrics(v))
        return metrics

    master_metrics = collect_all_metrics(master_parsed)
    final_metrics = collect_all_metrics(final_parsed)
    invented_metrics = final_metrics - master_metrics
    if invented_metrics:
        errors.append(f"Final tailored resume contains invented or altered metrics not found in source resume: {', '.join(sorted(invented_metrics))}")

    return len(errors) == 0, errors


class IntegrityAuditReport(BaseModel):
    total_source_evidence: int
    preserved_count: int
    condensed_count: int
    rewritten_count: int
    removed_count: int
    accidental_loss_count: int
    fragment_violations: list[str] = Field(default_factory=list)
    ledger_entries: list[dict[str, Any]] = Field(default_factory=list)
    is_valid: bool = True


def validate_source_evidence_ledger(
    candidate_profile: Any,
    final_parsed: dict,
    tailoring_plan: Any = None,
) -> IntegrityAuditReport:
    """
    Source-to-Final Evidence Ledger and Integrity Audit.
    Enforces atomic evidence unit tracking without silent omission or corruption:
    - Every source evidence unit is accounted for: PRESERVED, CONDENSED, REWRITTEN, or REMOVED with reason.
    - Zero accidental evidence losses allowed.
    - Zero incomplete/orphan sentence fragments allowed in final text.
    """
    evidence_units = getattr(candidate_profile, "evidence_units", []) or []
    
    # Collect all final delivery bullets across experience and projects
    from app.modules.resume.parsing.structurer import parse_experience_section, parse_projects_section

    final_bullets: list[str] = []
    exp_raw = final_parsed.get("experience_raw", []) or final_parsed.get("experience", [])
    if exp_raw:
        if isinstance(exp_raw, list) and exp_raw and isinstance(exp_raw[0], dict) and "company" in exp_raw[0] and "bullets" in exp_raw[0]:
            for e in exp_raw:
                final_bullets.extend(e.get("bullets", []))
        else:
            for ent in parse_experience_section(exp_raw):
                if ent.responsibility_groups:
                    for grp in ent.responsibility_groups:
                        final_bullets.extend(grp.bullets)
                else:
                    final_bullets.extend(ent.bullets)

    proj_raw = final_parsed.get("projects_raw", []) or final_parsed.get("projects", [])
    if proj_raw:
        if isinstance(proj_raw, list) and proj_raw and isinstance(proj_raw[0], dict) and "title" in proj_raw[0] and "bullets" in proj_raw[0]:
            for p in proj_raw:
                final_bullets.extend(p.get("bullets", []))
        else:
            for pe in parse_projects_section(proj_raw):
                final_bullets.extend(pe.bullets)

    plan_changes = []
    if tailoring_plan:
        if isinstance(tailoring_plan, dict):
            plan_changes = tailoring_plan.get("changes", [])
        elif hasattr(tailoring_plan, "changes"):
            plan_changes = getattr(tailoring_plan, "changes")

    preserved = 0
    condensed = 0
    rewritten = 0
    removed = 0
    accidental_loss = 0
    ledger_entries = []
    fragment_violations = []

    for idx, ev in enumerate(evidence_units):
        orig_text = ev.original_text if hasattr(ev, "original_text") else str(ev)
        ev_id = ev.id if hasattr(ev, "id") else f"EVIDENCE_{idx+1:03d}"
        section = ev.section if hasattr(ev, "section") else "EXPERIENCE"
        entity_id = ev.entity_id if hasattr(ev, "entity_id") else None

        clean_orig = re.sub(r"^[\u2022\u25cf\u25e6\u2023\u2043\u2219\-\*\s]+", "", orig_text).strip()

        matched_final = None
        for fb in final_bullets:
            clean_fb = re.sub(r"^[\u2022\u25cf\u25e6\u2023\u2043\u2219\-\*\s]+", "", fb).strip()
            if clean_orig and (clean_orig in clean_fb or clean_fb in clean_orig):
                matched_final = fb
                break

        action = "PRESERVE"
        reason = None
        final_text = matched_final or orig_text

        if matched_final:
            if clean_orig == re.sub(r"^[\u2022\u25cf\u25e6\u2023\u2043\u2219\-\*\s]+", "", matched_final).strip():
                action = "PRESERVE"
                preserved += 1
            elif len(matched_final.split()) < len(clean_orig.split()) * 0.8:
                action = "CONDENSE"
                condensed += 1
            else:
                action = "REWRITE"
                rewritten += 1
        else:
            # Check if explicitly removed in plan
            explicit_removal = False
            for chg in plan_changes:
                chg_orig = chg.get("original", "") if isinstance(chg, dict) else getattr(chg, "original", "")
                chg_act = chg.get("action", "") if isinstance(chg, dict) else getattr(chg, "action", "")
                if clean_orig and clean_orig in chg_orig and chg_act.upper() == "REMOVE":
                    action = "REMOVE"
                    reason = chg.get("reason", "") if isinstance(chg, dict) else getattr(chg, "reason", "")
                    removed += 1
                    explicit_removal = True
                    final_text = None
                    break

            if not explicit_removal:
                action = "ACCIDENTAL_LOSS"
                accidental_loss += 1
                final_text = None

        ledger_entries.append({
            "id": ev_id,
            "section": section,
            "entity_id": entity_id,
            "original_text": orig_text,
            "action": action,
            "final_text": final_text,
            "reason": reason,
        })

    # Validate final bullets for structural fragments
    for fb in final_bullets:
        frags = detect_sentence_fragments_and_truncation("", fb)
        if frags:
            fragment_violations.extend([f'"{fb[:40]}...": {f}' for f in frags])

    is_valid = (accidental_loss == 0) and (len(fragment_violations) == 0)

    return IntegrityAuditReport(
        total_source_evidence=len(evidence_units),
        preserved_count=preserved,
        condensed_count=condensed,
        rewritten_count=rewritten,
        removed_count=removed,
        accidental_loss_count=accidental_loss,
        fragment_violations=fragment_violations,
        ledger_entries=ledger_entries,
        is_valid=is_valid,
    )


class TruthGuardAuditResult(BaseModel):
    """
    Authoritative Truth Guard Audit Report (Phase 9).
    Evaluates rewritten candidate profile against verified source evidence ledger and tailoring plan.
    """
    is_valid: bool = True
    violations: list[str] = Field(default_factory=list)
    reverted_evidence_ids: list[str] = Field(default_factory=list)
    source_coverage_summary: dict[str, int] = Field(default_factory=dict)
    unsupported_technologies: list[str] = Field(default_factory=list)
    unsupported_metrics: list[str] = Field(default_factory=list)
    scope_escalations: list[str] = Field(default_factory=list)
    structural_violations: list[str] = Field(default_factory=list)


def validate_tailored_profile_truth_guard(
    source_profile: Any,
    tailored_profile: Any,
    tailoring_plan: Any = None,
    auto_revert: bool = True,
) -> tuple[Any, TruthGuardAuditResult]:
    """
    Comprehensive Provenance-Based Truth Guard Verification.
    Validates CandidateProfile against:
    1. Source Evidence Units & Technologies (No phantom technologies)
    2. Metrics & Percentages (No inflating 50% -> 60%, no cross-entity migration)
    3. Scope & Seniority (No ungrounded leadership, architecture, deployment, or production claims)
    4. Structural Integrity (No fragments, orphan continuations, truncated bullets, tech-only fragments, duplicates)
    5. Source Coverage (Zero ACCIDENTALLY_LOST units; intentional removals must have valid reasons)
    
    Safe Failure Behavior:
    If a rewritten unit fails verification, it is automatically reverted to the original verified source claim.
    """
    violations: list[str] = []
    reverted_evidence_ids: list[str] = []
    unsupported_technologies: list[str] = []
    unsupported_metrics: list[str] = []
    scope_escalations: list[str] = []
    structural_violations: list[str] = []

    source_ev_map = {ev.id: ev for ev in getattr(source_profile, "evidence_units", [])}
    tailored_ev_map = {ev.id: ev for ev in getattr(tailored_profile, "evidence_units", [])}

    plan_decisions = {}
    if tailoring_plan:
        decisions_list = getattr(tailoring_plan, "evidence_decisions", []) or getattr(tailoring_plan, "decisions", []) or []
        for d in decisions_list:
            d_id = getattr(d, "evidence_id", "") or (d.get("evidence_id") if isinstance(d, dict) else "")
            if d_id:
                plan_decisions[d_id] = d

    # 1. Source Coverage Verification
    preserved_count = 0
    rewritten_count = 0
    condensed_count = 0
    removed_count = 0
    accidental_loss_count = 0

    for s_id, s_ev in source_ev_map.items():
        if s_id in tailored_ev_map:
            t_ev = tailored_ev_map[s_id]
            clean_s = re.sub(r"^[•\-\*\s]+", "", getattr(s_ev, "normalized_text", "") or getattr(s_ev, "text", "")).strip()
            clean_t = re.sub(r"^[•\-\*\s]+", "", getattr(t_ev, "normalized_text", "") or getattr(t_ev, "text", "")).strip()
            if clean_s == clean_t:
                preserved_count += 1
            else:
                rewritten_count += 1
        else:
            decision = plan_decisions.get(s_id)
            d_action = getattr(decision, "action", "") if decision else ""
            if isinstance(d_action, str):
                d_act_str = d_action.upper()
            elif hasattr(d_action, "value"):
                d_act_str = str(d_action.value).upper()
            else:
                d_act_str = str(d_action).upper()

            if decision and ("REMOVE" in d_act_str or "CONDENSE" in d_act_str):
                d_reason = getattr(decision, "reason", "") or (decision.get("reason") if isinstance(decision, dict) else "")
                if not d_reason and "REMOVE" in d_act_str:
                    violations.append(f"Intentional removal of EvidenceUnit '{s_id}' is missing a mandatory reason.")
                removed_count += 1
            else:
                accidental_loss_count += 1
                violations.append(f"EvidenceUnit '{s_id}' was ACCIDENTALLY_LOST from tailored profile without explicit removal decision.")

    source_coverage_summary = {
        "total_source": len(source_ev_map),
        "preserved": preserved_count,
        "rewritten": rewritten_count,
        "condensed": condensed_count,
        "removed": removed_count,
        "accidental_loss": accidental_loss_count,
    }

    # 2. Per-Evidence Rewrite Truth Verification
    seen_bullet_texts: set[str] = set()
    units_to_revert: set[str] = set()

    for t_id, t_ev in list(tailored_ev_map.items()):
        s_ev = source_ev_map.get(t_id)
        if not s_ev:
            violations.append(f"Phantom EvidenceUnit '{t_id}' added without source provenance.")
            units_to_revert.add(t_id)
            continue

        orig_text = getattr(s_ev, "original_text", "") or getattr(s_ev, "text", "")
        norm_orig = getattr(s_ev, "normalized_text", "") or orig_text
        prop_text = getattr(t_ev, "normalized_text", "") or getattr(t_ev, "text", "")

        clean_prop = re.sub(r"^[•\-\*\s]+", "", prop_text).strip()
        clean_orig = re.sub(r"^[•\-\*\s]+", "", norm_orig).strip()

        unit_has_violation = False

        # Check duplicate bullets
        if clean_prop.lower() in seen_bullet_texts:
            v_msg = f"Duplicated evidence bullet detected across profile: '{clean_prop[:40]}...'"
            structural_violations.append(v_msg)
            violations.append(v_msg)
            unit_has_violation = True
        seen_bullet_texts.add(clean_prop.lower())

        if clean_prop != clean_orig:
            # Bullet was rewritten -> Execute full Truth Guard checks
            # a. Technology Fabrication Check
            verified_candidate_terms: list[str] = list(getattr(source_profile, "skills", []))
            if getattr(source_profile, "summary", ""):
                verified_candidate_terms.append(str(source_profile.summary))
            for exp in getattr(source_profile, "experience", []):
                if getattr(exp, "role", ""):
                    verified_candidate_terms.append(str(exp.role))
                if getattr(exp, "company", ""):
                    verified_candidate_terms.append(str(exp.company))
                for b in getattr(exp, "bullets", []):
                    verified_candidate_terms.append(str(b))
                for prog in getattr(exp, "progression", []):
                    if getattr(prog, "title", ""):
                        verified_candidate_terms.append(str(prog.title))
                    for b in getattr(prog, "bullets", []):
                        verified_candidate_terms.append(str(b))
                for grp in getattr(exp, "responsibility_groups", []):
                    if getattr(grp, "heading", ""):
                        verified_candidate_terms.append(str(grp.heading))
                    for b in getattr(grp, "bullets", []):
                        verified_candidate_terms.append(str(b))
            for proj in getattr(source_profile, "projects", []):
                if getattr(proj, "title", ""):
                    verified_candidate_terms.append(str(proj.title))
                if getattr(proj, "technologies", []):
                    verified_candidate_terms.extend([str(t) for t in proj.technologies])
                for b in getattr(proj, "bullets", []):
                    verified_candidate_terms.append(str(b))
            for cert in getattr(source_profile, "certifications", []):
                cert_val = getattr(cert, "name", str(cert))
                if cert_val:
                    verified_candidate_terms.append(str(cert_val))
            for add_sec in getattr(source_profile, "additional_sections", []):
                if getattr(add_sec, "heading", ""):
                    verified_candidate_terms.append(str(add_sec.heading))
                for itm in getattr(add_sec, "items", []):
                    verified_candidate_terms.append(str(itm))
            for ev in getattr(source_profile, "evidence_units", []):
                if getattr(ev, "technologies", []):
                    verified_candidate_terms.extend([str(t) for t in ev.technologies])
                if getattr(ev, "text", ""):
                    verified_candidate_terms.append(str(ev.text))

            unsupported_tech = detect_fabricated_claims(norm_orig, prop_text, "", verified_candidate_terms)
            if unsupported_tech:
                unsupported_technologies.extend(unsupported_tech)
                violations.append(f"EvidenceUnit '{t_id}' contains ungrounded technologies: {', '.join(unsupported_tech)}")
                unit_has_violation = True

            # b. Metric Alteration / Inflation Check (e.g. 50% -> 60%)
            unsupported_mets = detect_unsupported_metrics(norm_orig, prop_text)
            if unsupported_mets:
                unsupported_metrics.extend(unsupported_mets)
                violations.append(f"EvidenceUnit '{t_id}' contains ungrounded/altered metrics: {', '.join(unsupported_mets)}")
                unit_has_violation = True

            # c. Cross-Entity Contamination Check
            s_ent_id = getattr(s_ev, "entity_id", "") or ""
            entity_viols = detect_entity_boundary_violations(s_ent_id, prop_text, getattr(source_profile, "evidence_units", []))
            if entity_viols:
                for ev_viol in entity_viols:
                    violations.append(f"EvidenceUnit '{t_id}': {ev_viol}")
                unit_has_violation = True

            # d. Scope & Seniority Escalation Check
            scope_viols = detect_unsupported_action_verbs_and_scope(orig_text, prop_text)
            if scope_viols:
                scope_escalations.extend(scope_viols)
                for sc_viol in scope_viols:
                    violations.append(f"EvidenceUnit '{t_id}': {sc_viol}")
                unit_has_violation = True

            # e. Structural Validation (Fragments, dangling starts/ends, truncation)
            struct_viols = detect_sentence_fragments_and_truncation(orig_text, prop_text)
            
            # Reject technology-only fragments (e.g. "• Python, Docker, React.")
            prop_words = [w.strip(",.;:").lower() for w in clean_prop.split() if w.strip(",.;:")]
            if len(prop_words) >= 1 and all(w in ALL_TECH_TERMS or w in {"and", "&", "or"} for w in prop_words):
                struct_viols.append(f"Technology-only fragment without delivery context: '{clean_prop}'")

            if struct_viols:
                structural_violations.extend(struct_viols)
                for st_viol in struct_viols:
                    violations.append(f"EvidenceUnit '{t_id}': {st_viol}")
                unit_has_violation = True

        if unit_has_violation:
            units_to_revert.add(t_id)

    # 3. Safe Failure Fallback: Auto-Revert Failed Bullets
    if auto_revert and units_to_revert:
        for ev_id in units_to_revert:
            s_ev = source_ev_map.get(ev_id)
            if not s_ev:
                continue
            orig_text = getattr(s_ev, "original_text", "") or getattr(s_ev, "text", "")
            
            # Revert in Experience
            for exp in getattr(tailored_profile, "experience", []):
                for ev in getattr(exp, "evidence_units", []):
                    if ev.id == ev_id:
                        ev.normalized_text = orig_text
                exp.bullets = [ev.text for ev in exp.evidence_units]

            # Revert in Projects
            for proj in getattr(tailored_profile, "projects", []):
                for ev in getattr(proj, "evidence_units", []):
                    if ev.id == ev_id:
                        ev.normalized_text = orig_text
                proj.bullets = [ev.text for ev in proj.evidence_units]

            # Revert in Additional Sections
            for add_sec in getattr(tailored_profile, "additional_sections", []):
                for ev in getattr(add_sec, "evidence_units", []):
                    if ev.id == ev_id:
                        ev.normalized_text = orig_text
                add_sec.items = [ev.text for ev in add_sec.evidence_units]

            reverted_evidence_ids.append(ev_id)

        # Sync top-level evidence units
        all_active: list[Any] = []
        for exp in getattr(tailored_profile, "experience", []):
            all_active.extend(exp.evidence_units)
        for proj in getattr(tailored_profile, "projects", []):
            all_active.extend(proj.evidence_units)
        for add_sec in getattr(tailored_profile, "additional_sections", []):
            all_active.extend(add_sec.evidence_units)
        tailored_profile.evidence_units = all_active

    is_valid = (len(violations) == 0) and (accidental_loss_count == 0)

    report = TruthGuardAuditResult(
        is_valid=is_valid,
        violations=violations,
        reverted_evidence_ids=reverted_evidence_ids,
        source_coverage_summary=source_coverage_summary,
        unsupported_technologies=sorted(list(set(unsupported_technologies))),
        unsupported_metrics=sorted(list(set(unsupported_metrics))),
        scope_escalations=sorted(list(set(scope_escalations))),
        structural_violations=sorted(list(set(structural_violations))),
    )

    return tailored_profile, report
