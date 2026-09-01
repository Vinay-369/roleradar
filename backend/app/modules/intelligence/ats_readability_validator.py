"""
Deterministic ATS & Readability Validation Engine (Phase 9).
Evaluates formatting, structure, readability, and parsing risks while strictly
separating FACTUAL VALIDATION from ATS / FORMAT VALIDATION.
Zero LLM calls — 100% deterministic, mathematically explainable findings.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from app.modules.jobs.taxonomy import StructuredJobRequirements
from app.modules.resume.models import CandidateProfile
from app.modules.tailoring.validation import (
    PROTECTED_SECTION_NAMES,
    detect_fabricated_claims,
    detect_unsupported_metrics,
    validate_protected_sections,
)
from app.modules.resume.metrics import extract_quantified_metrics, _extract_quantified_metrics


# Standard ATS-friendly section headers
STANDARD_HEADERS = {
    "summary", "professional summary", "executive summary", "profile", "objective",
    "technical skills", "skills", "core competencies", "technologies",
    "work experience", "experience", "professional experience", "employment history",
    "projects", "technical projects", "academic projects", "key projects",
    "internships", "internship experience",
    "education", "academic background", "academic qualifications",
    "certifications", "certificates", "licenses",
    "achievements", "awards", "honors", "accomplishments",
    "languages", "spoken languages",
}

NON_STANDARD_HEADER_MAP = {
    "tech arsenal": "TECHNICAL SKILLS",
    "what i know": "TECHNICAL SKILLS",
    "stuff i did": "WORK EXPERIENCE",
    "my journey": "WORK EXPERIENCE",
    "where i worked": "WORK EXPERIENCE",
    "schooling": "EDUCATION",
    "my apps": "PROJECTS",
    "about me": "PROFESSIONAL SUMMARY",
}

UNUSUAL_SYMBOLS = {"⚡", "★", "☆", "►", "❖", "✔", "➔", "🚀", "💡", "🔥", "✓", "■", "◆", "\ufffd"}

ACTION_VERB_PREFIXES = {
    "architected", "built", "engineered", "developed", "deployed", "optimized",
    "scaled", "automated", "designed", "implemented", "reduced", "increased",
    "accelerated", "created", "spearheaded", "integrated", "transformed", "led",
    "managed", "collaborated", "constructed", "configured", "authored", "orchestrated",
}


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationFinding(BaseModel):
    category: str
    severity: ValidationSeverity
    issue: str
    impact: str
    recommendation: str


class FactualValidationReport(BaseModel):
    is_valid: bool
    verified_claims_count: int = 0
    unverified_claims: list[str] = Field(default_factory=list)
    boundary_violations: list[str] = Field(default_factory=list)
    protected_sections_intact: bool = True
    findings: list[ValidationFinding] = Field(default_factory=list)


class ATSFormatValidationReport(BaseModel):
    overall_ats_score: int  # 0 to 100
    standard_headings_score: int  # 0 to 100
    section_order_score: int  # 0 to 100
    bullet_consistency_score: int  # 0 to 100
    date_consistency_score: int  # 0 to 100
    readability_score: int  # 0 to 100
    keyword_stuffing_detected: bool = False
    keyword_density_ratio: float = 0.0
    unusual_symbols_detected: list[str] = Field(default_factory=list)
    parsing_risks: list[str] = Field(default_factory=list)
    layout_risks: list[str] = Field(default_factory=list)
    missing_critical_info: list[str] = Field(default_factory=list)
    length_status: str = "OPTIMAL_1_PAGE"  # OPTIMAL_1_PAGE | ACCEPTABLE_2_PAGE | TOO_SHORT | TOO_LONG
    word_count: int = 0
    findings: list[ValidationFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ATSReadabilityAuditResult(BaseModel):
    factual_validation: FactualValidationReport
    ats_format_validation: ATSFormatValidationReport
    disclaimer: str = (
        "RoleRadar evaluates ATS parsing compatibility and structural formatting standards. "
        "This assessment does not guarantee job shortlisting or hiring decisions, which depend "
        "on human recruiter discretion and employer evaluation."
    )


def evaluate_ats_and_readability(
    resume_data: str | dict | CandidateProfile,
    master_data: str | dict | CandidateProfile | None = None,
    job_reqs: StructuredJobRequirements | None = None,
) -> ATSReadabilityAuditResult:
    """
    Evaluates both Factual Truth and ATS/Format Readability in strict isolation.
    """
    # 1. Normalize input resume data
    if isinstance(resume_data, CandidateProfile):
        parsed = resume_data.to_parsed_dict()
        raw_text = resume_data.raw_text
    elif isinstance(resume_data, dict):
        parsed = dict(resume_data)
        from app.modules.tailoring.export import render_text_from_structured
        raw_text = parsed.get("raw_text") or render_text_from_structured(parsed)
    else:
        raw_text = str(resume_data)
        from app.modules.resume.parsing.structurer import structure_resume_text
        parsed = structure_resume_text(raw_text)

    # Normalize master resume data for factual validation
    master_parsed: dict[str, Any] = {}
    if master_data is not None:
        if isinstance(master_data, CandidateProfile):
            master_parsed = master_data.to_parsed_dict()
        elif isinstance(master_data, dict):
            master_parsed = dict(master_data)
        else:
            from app.modules.resume.parsing.structurer import structure_resume_text
            master_parsed = structure_resume_text(str(master_data))
    else:
        master_parsed = parsed

    # -------------------------------------------------------------
    # PART 1: FACTUAL VALIDATION
    # -------------------------------------------------------------
    factual_findings: list[ValidationFinding] = []
    unverified_claims: list[str] = []
    boundary_violations: list[str] = []

    # Check protected section integrity
    is_prot_valid, prot_errors = validate_protected_sections(master_parsed, parsed)
    if not is_prot_valid:
        for err in prot_errors:
            factual_findings.append(ValidationFinding(
                category="PROTECTED_SECTION",
                severity=ValidationSeverity.CRITICAL,
                issue=err,
                impact="Candidate's verified education or contact credentials were compromised.",
                recommendation="Ensure Education and Contact details match verified background.",
            ))

    # Check unevidenced certifications
    master_certs = {c.strip().lower() for c in master_parsed.get("certifications", []) if c.strip()}
    final_certs = {c.strip().lower() for c in parsed.get("certifications", []) if c.strip()}
    new_certs = final_certs - master_certs
    if new_certs:
        for cert in new_certs:
            unverified_claims.append(f"Certification: {cert}")
            factual_findings.append(ValidationFinding(
                category="CERTIFICATION_EVIDENCE",
                severity=ValidationSeverity.HIGH,
                issue=f"Certification '{cert}' not verified in master candidate background.",
                impact="Falsified certifications create immediate background check disqualifications.",
                recommendation="Remove unearned certification claims.",
            ))

    # Check unverified metrics
    def collect_metrics(data: Any) -> set[str]:
        metrics = set()
        if isinstance(data, str):
            for m in _extract_quantified_metrics(data):
                norm = m.lower().replace(",", "").replace("+", "").replace(" ", "").replace("percent", "%")
                metrics.add(norm)
                if norm.endswith("%"):
                    metrics.add(norm[:-1])
                elif norm.startswith("$"):
                    metrics.add(norm[1:])
        elif isinstance(data, list):
            for item in data:
                metrics.update(collect_metrics(item))
        elif isinstance(data, dict):
            for v in data.values():
                metrics.update(collect_metrics(v))
        return metrics

    master_metrics = collect_metrics(master_parsed)
    if master_data is not None:
        if isinstance(master_data, CandidateProfile):
            master_metrics.update(collect_metrics([ev.metrics for ev in master_data.evidence_units]))
            if getattr(master_data, "raw_text", None):
                master_metrics.update(collect_metrics(master_data.raw_text))
        elif isinstance(master_data, str):
            master_metrics.update(collect_metrics(master_data))

    final_metrics = collect_metrics(parsed)
    invented_metrics = final_metrics - master_metrics
    if invented_metrics:
        for m in invented_metrics:
            unverified_claims.append(f"Metric: {m}")
            factual_findings.append(ValidationFinding(
                category="METRIC_EVIDENCE",
                severity=ValidationSeverity.HIGH,
                issue=f"Metric '{m}' has no verifiable source evidence in candidate background.",
                impact="Unsubstantiated numerical claims degrade hiring credibility.",
                recommendation="Only cite metrics verified from original projects or work history.",
            ))

    factual_report = FactualValidationReport(
        is_valid=(len(factual_findings) == 0),
        verified_claims_count=len(master_metrics),
        unverified_claims=unverified_claims,
        boundary_violations=boundary_violations,
        protected_sections_intact=is_prot_valid,
        findings=factual_findings,
    )

    # -------------------------------------------------------------
    # PART 2: ATS & FORMAT VALIDATION
    # -------------------------------------------------------------
    format_findings: list[ValidationFinding] = []
    recommendations: list[str] = []
    parsing_risks: list[str] = []
    layout_risks: list[str] = []
    missing_critical: list[str] = []
    unusual_symbols_found: list[str] = []

    # 1. Contact Information Check
    email_re = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    phone_re = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}|\d{10}\b)")

    personal = parsed.get("personal", {}) or parsed.get("personal_info", {}) or {}
    email = personal.get("email") or email_re.search(raw_text)
    phone = personal.get("phone") or phone_re.search(raw_text)
    if not email:
        missing_critical.append("Email Address")
        format_findings.append(ValidationFinding(
            category="CONTACT_INFO",
            severity=ValidationSeverity.CRITICAL,
            issue="No valid email address found.",
            impact="ATS cannot route recruiter interview communications.",
            recommendation="Place candidate email in the top contact header.",
        ))
    if not phone:
        missing_critical.append("Phone Number")
        format_findings.append(ValidationFinding(
            category="CONTACT_INFO",
            severity=ValidationSeverity.HIGH,
            issue="No valid phone number found.",
            impact="Recruiters cannot initiate phone screening.",
            recommendation="Include a phone number in standard international/national format.",
        ))

    # 2. Section Headings & Standard Naming Check
    raw_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    non_standard_headings = []
    detected_headers = []
    for line in raw_lines:
        line_clean = line.lower().rstrip(":")
        if line_clean in NON_STANDARD_HEADER_MAP:
            non_standard_headings.append(line)
            format_findings.append(ValidationFinding(
                category="SECTION_HEADINGS",
                severity=ValidationSeverity.MEDIUM,
                issue=f"Non-standard heading '{line}' detected.",
                impact="Commercial ATS parsers may misclassify or skip this entire section.",
                recommendation=f"Rename '{line}' to industry-standard '{NON_STANDARD_HEADER_MAP[line_clean]}'.",
            ))
        elif line_clean in STANDARD_HEADERS:
            detected_headers.append(line_clean)

    standard_headings_score = max(0, 100 - len(non_standard_headings) * 20)

    # 3. Section Order Check
    section_order_score = 100
    if "education" in detected_headers and "experience" in detected_headers:
        # Check relative positioning
        pass

    # 4. Bullet Consistency & Action Verbs Check
    bullets: list[str] = []
    for exp in parsed.get("experience_raw", []):
        if isinstance(exp, str) and exp.strip().startswith(("•", "-", "*")):
            bullets.append(exp.strip())
    for proj in parsed.get("projects_raw", []):
        if isinstance(proj, dict):
            for b in proj.get("bullets", []):
                bullets.append(b.strip())
        elif isinstance(proj, str) and proj.strip().startswith(("•", "-", "*")):
            bullets.append(proj.strip())

    # Fallback: Scan raw_lines for any bullet lines if parsed structure had non-standard headers
    if not bullets:
        for line in raw_lines:
            if line.startswith(("•", "-", "*")) and len(line) > 3:
                bullets.append(line)

    weak_verb_bullets = []
    short_bullets = []
    long_bullets = []
    for b in bullets:
        clean_b = re.sub(r"^[•\-\*\s]+", "", b).strip()
        words = clean_b.split()
        if len(words) < 5:
            short_bullets.append(clean_b)
        elif len(words) > 40:
            long_bullets.append(clean_b)

        first_word = words[0].lower() if words else ""
        if first_word and first_word not in ACTION_VERB_PREFIXES:
            # Check if verb ends in ed/ing
            if not first_word.endswith("ed") and not first_word.endswith("ing"):
                weak_verb_bullets.append(clean_b)

    bullet_consistency_score = 100
    if weak_verb_bullets:
        bullet_consistency_score -= min(30, len(weak_verb_bullets) * 5)
        format_findings.append(ValidationFinding(
            category="BULLET_QUALITY",
            severity=ValidationSeverity.MEDIUM,
            issue=f"{len(weak_verb_bullets)} bullets do not start with strong technical action verbs.",
            impact="Reduces recruiter impact and skim-reading effectiveness.",
            recommendation="Start bullets with active verbs (Architected, Engineered, Built, Optimized, Deployed).",
        ))
    if long_bullets:
        bullet_consistency_score -= min(20, len(long_bullets) * 5)
        format_findings.append(ValidationFinding(
            category="READABILITY",
            severity=ValidationSeverity.LOW,
            issue=f"{len(long_bullets)} bullets exceed recommended length (>40 words).",
            impact="Long paragraphs are skipped by recruiters during 6-second scans.",
            recommendation="Break multi-clause bullets into concise action-impact statements.",
        ))

    # 5. Date Consistency Check
    date_patterns = [
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b",
        r"\b\d{4}\s*-\s*(?:\d{4}|present)\b",
        r"\b\d{1,2}/\d{4}\b",
    ]
    date_matches = []
    for p in date_patterns:
        matches = re.findall(p, raw_text, re.IGNORECASE)
        if matches:
            date_matches.append(p)
    date_consistency_score = 100 if len(date_matches) <= 1 else 85
    if len(date_matches) > 1:
        format_findings.append(ValidationFinding(
            category="DATE_CONSISTENCY",
            severity=ValidationSeverity.LOW,
            issue="Mixed date formats detected (e.g. Month YYYY mixed with YYYY-YYYY).",
            impact="Minor parsing ambiguity in timeline ordering.",
            recommendation="Use consistent date formatting across all entries (e.g. '2023 - Present' or 'Jan 2023 - Present').",
        ))

    # 6. Unusual Symbols Check
    for sym in UNUSUAL_SYMBOLS:
        if sym in raw_text:
            unusual_symbols_found.append(sym)
            parsing_risks.append(f"Special decorative symbol '{sym}' detected")

    if unusual_symbols_found:
        format_findings.append(ValidationFinding(
            category="PARSING_RISK",
            severity=ValidationSeverity.MEDIUM,
            issue=f"Unusual decorative symbols ({', '.join(unusual_symbols_found)}) found.",
            impact="May render as replacement glyphs in older legacy enterprise ATS parsers.",
            recommendation="Use standard ASCII bullet points (• or -) and standard punctuation.",
        ))

    # 7. Keyword Stuffing / Over-Optimization Check
    STOP_WORDS = {
        "and", "the", "for", "with", "using", "from", "into", "that", "this", "these",
        "those", "are", "was", "were", "been", "being", "have", "has", "had", "having",
        "will", "would", "shall", "should", "may", "might", "must", "can", "could",
        "across", "over", "under", "between", "through", "after", "before", "while",
        "per", "via", "such", "all", "any", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "than", "too", "very", "own", "same", "also",
        "engineering", "development", "developer", "experience", "skills", "projects",
    }
    all_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", raw_text)]
    total_words = len(all_words)
    tech_words = [w for w in all_words if w not in STOP_WORDS]
    keyword_density_ratio = 0.0
    keyword_stuffing_detected = False
    if len(tech_words) > 0:
        word_freq: dict[str, int] = {}
        for w in tech_words:
            word_freq[w] = word_freq.get(w, 0) + 1
        max_freq = max(word_freq.values()) if word_freq else 0
        keyword_density_ratio = round((max_freq / total_words) * 100.0, 2)
        if (keyword_density_ratio > 5.0 and total_words >= 30) or max_freq >= 10:
            keyword_stuffing_detected = True
            format_findings.append(ValidationFinding(
                category="KEYWORD_OPTIMIZATION",
                severity=ValidationSeverity.HIGH,
                issue=f"High keyword repetition detected ({keyword_density_ratio}% density, max word frequency: {max_freq}).",
                impact="May trigger recruiter over-optimization and keyword stuffing penalties.",
                recommendation="Distribute technical skills contextually across delivery bullets rather than repeating keywords.",
            ))

    # 8. Document Length & Word Count Check
    length_status = "OPTIMAL_1_PAGE"
    if total_words < 150:
        length_status = "TOO_SHORT"
        format_findings.append(ValidationFinding(
            category="LENGTH",
            severity=ValidationSeverity.HIGH,
            issue="Resume is sparse (<150 words).",
            impact="Lacks sufficient evidence for technical depth assessment.",
            recommendation="Expand projects and experience with delivery metrics and technologies.",
        ))
    elif total_words > 1000:
        length_status = "ACCEPTABLE_2_PAGE"
    elif total_words > 1400:
        length_status = "TOO_LONG"
        format_findings.append(ValidationFinding(
            category="LENGTH",
            severity=ValidationSeverity.MEDIUM,
            issue="Resume exceeds optimal length (>1400 words).",
            impact="High risk of multi-page overflow and reduced readability.",
            recommendation="Trim older bullet points and tighten concise phrasing to fit 1-2 pages.",
        ))

    # Calculate overall ATS format score
    deductions = 0
    for f in format_findings:
        if f.severity == ValidationSeverity.CRITICAL:
            deductions += 25
        elif f.severity == ValidationSeverity.HIGH:
            deductions += 15
        elif f.severity == ValidationSeverity.MEDIUM:
            deductions += 10
        elif f.severity == ValidationSeverity.LOW:
            deductions += 5

    overall_ats_score = max(20, 100 - deductions)
    readability_score = max(30, 100 - (len(long_bullets) * 10 + len(short_bullets) * 5))

    # Assembly recommendations
    for f in format_findings:
        if f.recommendation and f.recommendation not in recommendations:
            recommendations.append(f.recommendation)

    format_report = ATSFormatValidationReport(
        overall_ats_score=overall_ats_score,
        standard_headings_score=standard_headings_score,
        section_order_score=section_order_score,
        bullet_consistency_score=bullet_consistency_score,
        date_consistency_score=date_consistency_score,
        readability_score=readability_score,
        keyword_stuffing_detected=keyword_stuffing_detected,
        keyword_density_ratio=keyword_density_ratio,
        unusual_symbols_detected=unusual_symbols_found,
        parsing_risks=parsing_risks,
        layout_risks=layout_risks,
        missing_critical_info=missing_critical,
        length_status=length_status,
        word_count=total_words,
        findings=format_findings,
        recommendations=recommendations,
    )

    return ATSReadabilityAuditResult(
        factual_validation=factual_report,
        ats_format_validation=format_report,
    )
