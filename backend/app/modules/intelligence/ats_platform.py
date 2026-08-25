"""
ATS Platform Compliance & Rules Engine (Tier 1 Feature).

Deterministic, rule-based checks tailored to major ATS architectures:
- Workday
- Taleo
- Greenhouse
- Lever
- iCIMS
- Generic / Standard ATS

Surfaces platform-specific quirks, layout warnings, and keyword-density
ceiling limits based on actual ATS parser behaviors.
"""
from enum import Enum
from typing import TypedDict


class ATSPlatform(str, Enum):
    WORKDAY = "workday"
    TALEO = "taleo"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ICIMS = "icims"
    GENERIC = "generic"


class PlatformWarning(TypedDict):
    severity: str  # "high" | "medium" | "info"
    title: str
    message: str


class PlatformComplianceResult(TypedDict):
    platform: str
    platform_name: str
    compliance_score: int  # 0 - 100
    is_compliant: bool
    warnings: list[PlatformWarning]
    tips: list[str]


PLATFORM_METADATA = {
    ATSPlatform.WORKDAY: {
        "name": "Workday",
        "badge_color": "blue",
        "description": "Enterprise ATS known for strict layout rules, table sensitivity, and keyword density thresholds.",
    },
    ATSPlatform.TALEO: {
        "name": "Oracle Taleo",
        "badge_color": "red",
        "description": "Legacy enterprise ATS strict on standard section names, clean single-column text, and standard fonts.",
    },
    ATSPlatform.GREENHOUSE: {
        "name": "Greenhouse",
        "badge_color": "emerald",
        "description": "Modern ATS with strong semantic search, prioritizing direct skill keywords and clear chronology.",
    },
    ATSPlatform.LEVER: {
        "name": "Lever",
        "badge_color": "purple",
        "description": "Fast-parsing ATS that emphasizes social/portfolio links (GitHub, LinkedIn) and clean text streams.",
    },
    ATSPlatform.ICIMS: {
        "name": "iCIMS",
        "badge_color": "amber",
        "description": "Structured enterprise ATS favoring standard date formats (MM/YYYY) and explicit section hierarchies.",
    },
    ATSPlatform.GENERIC: {
        "name": "Standard ATS",
        "badge_color": "teal",
        "description": "Universal ATS baseline evaluating parseability, structural headers, and contact information.",
    },
}


def detect_platform_from_url(url: str) -> ATSPlatform:
    if not url:
        return ATSPlatform.GENERIC
    url_lower = url.lower()
    if "myworkdayjobs.com" in url_lower or "workday" in url_lower:
        return ATSPlatform.WORKDAY
    if "taleo.net" in url_lower or "oracle" in url_lower:
        return ATSPlatform.TALEO
    if "greenhouse.io" in url_lower or "gh_jid" in url_lower:
        return ATSPlatform.GREENHOUSE
    if "lever.co" in url_lower:
        return ATSPlatform.LEVER
    if "icims.com" in url_lower:
        return ATSPlatform.ICIMS
    return ATSPlatform.GENERIC


def evaluate_platform_compliance(
    resume_text: str,
    parseability_data: dict,
    platform: ATSPlatform | str | None = ATSPlatform.GENERIC,
    keyword_density: float = 0.0,
) -> PlatformComplianceResult:
    if isinstance(platform, ATSPlatform):
        pass
    elif isinstance(platform, str):
        try:
            platform = ATSPlatform(platform.lower())
        except ValueError:
            platform = ATSPlatform.GENERIC
    else:
        platform = ATSPlatform.GENERIC

    meta = PLATFORM_METADATA.get(platform, PLATFORM_METADATA[ATSPlatform.GENERIC])
    warnings: list[PlatformWarning] = []
    tips: list[str] = []
    compliance_score = parseability_data.get("score", 85)

    likely_multi_column = parseability_data.get("likely_multi_column", False)
    missing_sections = parseability_data.get("missing_standard_sections", [])
    contact_info = parseability_data.get("contact_info_found", {})
    word_count = parseability_data.get("word_count", len(resume_text.split()))

    if platform == ATSPlatform.WORKDAY:
        if likely_multi_column:
            warnings.append({
                "severity": "high",
                "title": "Workday Multi-Column Vulnerability",
                "message": "Workday's text extractor parses left-to-right across columns, scrambling content from side-by-side columns.",
            })
            compliance_score -= 15

        if keyword_density >= 3.5:
            warnings.append({
                "severity": "high",
                "title": "Workday Keyword Density Ceiling Exceeded",
                "message": f"Peak keyword density is {keyword_density:.1f}% (>=3.5%). Workday triggers keyword-stuffing flags when key terms repeat excessively.",
            })
            compliance_score -= 10
        elif keyword_density > 2.8:
            warnings.append({
                "severity": "medium",
                "title": "Approaching Keyword Density Ceiling",
                "message": f"Peak keyword density is {keyword_density:.1f}%. Target 1.0%–2.5% for natural Workday parsing.",
            })

        if missing_sections:
            warnings.append({
                "severity": "medium",
                "title": "Workday Section Mapping Issue",
                "message": f"Missing standard headers ({', '.join(missing_sections)}). Workday pre-populates application forms from detected headers.",
            })
            compliance_score -= 8

        tips.append("Use clean single-column layout without header/footer contact boxes.")
        tips.append("Keep keyword density under 3% per 100 words to avoid automated spam filters.")
        tips.append("Ensure standard section headers: WORK EXPERIENCE, EDUCATION, SKILLS.")

    elif platform == ATSPlatform.TALEO:
        if likely_multi_column:
            warnings.append({
                "severity": "high",
                "title": "Taleo Layout Disruption",
                "message": "Taleo's legacy parsing engine frequently fails on multi-column layouts and text frames.",
            })
            compliance_score -= 20

        if missing_sections:
            warnings.append({
                "severity": "high",
                "title": "Strict Section Header Requirement",
                "message": f"Taleo requires exact section titles. Missing: {', '.join(missing_sections)}.",
            })
            compliance_score -= 12

        tips.append("Use standard bullet points (•) and avoid fancy graphics or custom font symbols.")
        tips.append("Format dates clearly as MM/YYYY or Month Year (e.g. 05/2022 - Present).")

    elif platform == ATSPlatform.GREENHOUSE:
        if not contact_info.get("email") or not contact_info.get("phone"):
            warnings.append({
                "severity": "high",
                "title": "Candidate Contact Extraction",
                "message": "Greenhouse requires clear email and phone in document body to create candidate profiles automatically.",
            })
            compliance_score -= 15

        tips.append("Greenhouse ranks candidate profiles on direct skill keyword matches.")
        tips.append("Keep project descriptions concise with quantified outcomes.")

    elif platform == ATSPlatform.LEVER:
        if not contact_info.get("links"):
            warnings.append({
                "severity": "medium",
                "title": "Portfolio / Profile Links Missing",
                "message": "Lever prominently displays candidate links (GitHub, LinkedIn, Portfolio) in its recruiter view.",
            })
            compliance_score -= 8

        tips.append("Include clickable GitHub and LinkedIn profile URLs.")
        tips.append("Lever presents a clean plain-text preview to recruiters.")

    elif platform == ATSPlatform.ICIMS:
        if word_count > 1000:
            warnings.append({
                "severity": "medium",
                "title": "Document Length Alert",
                "message": "iCIMS summary views favor concise 1–2 page resumes.",
            })
            compliance_score -= 5

        tips.append("Keep dates in chronological order with explicit company and job title hierarchy.")
        tips.append("Group technical skills by category (Languages, Frameworks, Tools).")

    else:  # GENERIC
        if likely_multi_column:
            warnings.append({
                "severity": "medium",
                "title": "Multi-Column Layout Detected",
                "message": "Some ATS parsers read multi-column layouts horizontally across columns.",
            })
            compliance_score -= 10
        tips.append("Aim for 75%–85% match rate for balanced ATS and human recruiter review.")
        tips.append("Ensure contact info is placed directly in the main document body.")

    compliance_score = max(0, min(100, compliance_score))

    return {
        "platform": platform.value,
        "platform_name": meta["name"],
        "compliance_score": compliance_score,
        "is_compliant": compliance_score >= 70 and len([w for w in warnings if w["severity"] == "high"]) == 0,
        "warnings": warnings,
        "tips": tips,
    }
