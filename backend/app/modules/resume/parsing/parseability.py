"""
Parseability Engine — deterministic, rule-based, zero LLM calls.

This is what makes the "RoleRadar ATS Compatibility Score" defensible
rather than a vibe number from an LLM: it reconstructs structural facts
about the document the same way a real ATS parser would, and flags
exactly what would break, with a reason a candidate can act on.
"""
import re
from dataclasses import dataclass, field

STANDARD_SECTION_HEADERS = [
    "summary", "objective", "profile",
    "skills", "technical skills", "core competencies",
    "experience", "work experience", "professional experience", "employment history",
    "projects", "academic projects",
    "internships", "internship experience",
    "education", "academic background",
    "certifications", "certificates",
    "achievements", "awards", "accomplishments",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s-]?)?\d{10}\b")
# Matches full URLs (http/www) as well as bare professional-profile
# domains without a scheme, since resumes very commonly write
# "github.com/user" or "linkedin.com/in/user" with no http:// prefix.
URL_RE = re.compile(
    r"https?://\S+"
    r"|(?:www\.)\S+\.\S+"
    r"|(?:github\.com|gitlab\.com|linkedin\.com|bitbucket\.org)/\S+"
)


@dataclass
class ParseabilityIssue:
    code: str
    severity: str  # "high" | "medium" | "low"
    message: str


@dataclass
class ParseabilityResult:
    score: int  # 0-100
    issues: list[ParseabilityIssue] = field(default_factory=list)
    detected_sections: list[str] = field(default_factory=list)
    missing_standard_sections: list[str] = field(default_factory=list)
    contact_info_found: dict = field(default_factory=dict)
    likely_multi_column: bool = False
    word_count: int = 0


def _detect_multi_column(blocks: list[dict]) -> bool:
    """
    Heuristic: group text blocks into rows by overlapping y-ranges. If a
    meaningful share of rows contain 2+ blocks whose x-ranges don't
    overlap, the layout is very likely multi-column — which many real
    ATS parsers read left-to-right straight through and garble.
    """
    if not blocks:
        return False

    # Only meaningful for PDFs where we have real coordinates.
    rows: list[list[dict]] = []
    sorted_blocks = sorted(blocks, key=lambda b: (b["page"], b["y0"]))
    for b in sorted_blocks:
        placed = False
        for row in rows:
            # same page, overlapping y-range with anything already in the row
            if any(b["page"] == r["page"] and not (b["y1"] < r["y0"] or b["y0"] > r["y1"]) for r in row):
                row.append(b)
                placed = True
                break
        if not placed:
            rows.append([b])

    multi_col_rows = 0
    considered_rows = 0
    for row in rows:
        if len(row) < 2:
            continue
        considered_rows += 1
        xs_ranges = sorted(row, key=lambda b: b["x0"])
        non_overlapping = all(
            xs_ranges[i]["x1"] <= xs_ranges[i + 1]["x0"] + 5  # small tolerance
            for i in range(len(xs_ranges) - 1)
        )
        if non_overlapping:
            multi_col_rows += 1

    if considered_rows == 0:
        return False
    return (multi_col_rows / considered_rows) > 0.25


def _detect_sections(text: str) -> tuple[list[str], list[str]]:
    lower = text.lower()
    detected = [h for h in STANDARD_SECTION_HEADERS if re.search(rf"\b{re.escape(h)}\b", lower)]
    # Collapse to canonical groups so "work experience" and "experience"
    # don't both count as missing/present separately.
    canonical_groups = {
        "summary": ["summary", "objective", "profile"],
        "skills": ["skills", "technical skills", "core competencies"],
        "experience": ["experience", "work experience", "professional experience", "employment history"],
        "projects": ["projects", "academic projects"],
        "education": ["education", "academic background"],
    }
    present_canonical = set()
    for canon, variants in canonical_groups.items():
        if any(v in detected for v in variants):
            present_canonical.add(canon)

    has_practical = "experience" in present_canonical or "projects" in present_canonical or any("internship" in d for d in detected)
    missing = []
    if "skills" not in present_canonical:
        missing.append("skills")
    if "education" not in present_canonical:
        missing.append("education")
    if not has_practical:
        missing.append("experience")

    return detected, sorted(missing)


def analyze_parseability(text: str, blocks: list[dict], file_type: str, has_tables: bool | None) -> ParseabilityResult:
    issues: list[ParseabilityIssue] = []
    score = 100

    word_count = len(text.split())
    if word_count < 80:
        issues.append(ParseabilityIssue(
            "TEXT_TOO_SHORT", "high",
            "Very little text could be extracted — the file may be an image-based PDF "
            "(scanned resume) that machine parsers cannot read at all.",
        ))
        score -= 30

    detected_sections, missing_sections = _detect_sections(text)
    for section in missing_sections:
        issues.append(ParseabilityIssue(
            f"MISSING_SECTION_{section.upper()}", "medium",
            f"No standard '{section.title()}' section header was found. ATS parsers "
            f"often rely on standard headers to bucket your content correctly.",
        ))
        score -= 8

    contact_info = {
        "email": bool(EMAIL_RE.search(text)),
        "phone": bool(PHONE_RE.search(text)),
        "links": bool(URL_RE.search(text)),
    }
    if not contact_info["email"]:
        issues.append(ParseabilityIssue(
            "MISSING_EMAIL", "high", "No email address could be detected in the document body.",
        ))
        score -= 15
    if not contact_info["phone"]:
        issues.append(ParseabilityIssue(
            "MISSING_PHONE", "low", "No phone number could be detected in the document body.",
        ))
        score -= 5

    multi_column = False
    if file_type == "pdf":
        multi_column = _detect_multi_column(blocks)
        if multi_column:
            issues.append(ParseabilityIssue(
                "MULTI_COLUMN_LAYOUT", "high",
                "This resume appears to use a multi-column layout. Many ATS parsers read "
                "left-to-right across the whole page and will interleave text from "
                "different columns, scrambling your content.",
            ))
            score -= 20

    if has_tables:
        issues.append(ParseabilityIssue(
            "CONTAINS_TABLES", "medium",
            "This document contains tables. ATS parsers frequently fail to extract "
            "content inside table cells correctly.",
        ))
        score -= 10

    if word_count > 1200:
        issues.append(ParseabilityIssue(
            "TOO_LONG", "low",
            "This resume is quite long (over ~2 pages of content). For most roles, "
            "recruiters and ATS ranking both favor a focused 1-page (fresher) or "
            "1-2 page (experienced) resume.",
        ))
        score -= 5

    score = max(0, min(100, score))

    return ParseabilityResult(
        score=score,
        issues=issues,
        detected_sections=sorted(set(detected_sections)),
        missing_standard_sections=missing_sections,
        contact_info_found=contact_info,
        likely_multi_column=multi_column,
        word_count=word_count,
    )
