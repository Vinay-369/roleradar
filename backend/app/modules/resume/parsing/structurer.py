"""
Rule-based resume structuring with high-tolerance pattern matching
and spaCy NLP fallback for messy, unstandardized human resumes.
"""
import re
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.resume.parsing.parseability import EMAIL_RE, PHONE_RE, URL_RE

SECTION_PATTERNS = {
    "summary": r"^\s*(summary|career summary|professional summary|objective|career objective|profile|personal profile|about me)\s*$",
    "skills": r"^\s*(skills|technical skills|key skills|core skills|core competencies|skills & expertise|skills & technologies|tech stack|technical proficiencies|areas of expertise|technologies|tools & technologies)\s*$",
    "experience": r"^\s*(experience|work experience|professional experience|employment history|work history|career history|experience & employment|relevant experience|employment)\s*$",
    "projects": r"^\s*(projects|academic projects|key projects|personal projects|technical projects|notable projects|portfolio projects|selected projects)\s*$",
    "internships": r"^\s*(internships?|internship experience|industrial training|industry training)\s*$",
    "education": r"^\s*(education|academic background|academics|qualifications|educational qualifications|academic profile|education & qualifications)\s*$",
    "certifications": r"^\s*(certifications?|certificates|licenses|courses & certifications|professional certifications)\s*$",
    "achievements": r"^\s*(achievements|awards|accomplishments|honors|extracurricular activities|extra-curricular|co-curricular|awards & achievements|co-curricular & honors|extracurricular & honors|honors & awards|achievements & awards)\s*$",
}

_BULLET_PREFIX_RE = re.compile(
    r"^(?:[•\-\*\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u27A4\u2714\u2713\u279C\u2192\u25BA\u25B6\u25C6\u25C7\u25CF\u25CB\u2718\u2717\u2705\u27A2\u2794\u2714]|\d{1,2}[\.\)]|[a-zA-Z][\.\)])\s*",
    re.UNICODE,
)

_CATEGORY_PREFIX_RE = re.compile(
    r"^(?:languages|programming languages|frameworks|libraries|tools|databases|cloud|devops|backend|frontend|methodologies|web technologies|platforms|technologies|os|operating systems|core competencies)\s*:\s*",
    re.IGNORECASE,
)


def _split_into_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {key: [] for key in SECTION_PATTERNS}
    sections["_preamble"] = []  # everything before the first recognized header

    current = "_preamble"
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Normalize punctuation and symbols ("Skills:", "## Skills", "-- SKILLS --")
        normalized = re.sub(r"^[#\-=*~\s]+|[#\-=*~\s:]+$", "", stripped)
        matched = None
        for key, pattern in SECTION_PATTERNS.items():
            if re.match(pattern, normalized, re.IGNORECASE):
                matched = key
                break
        if matched:
            current = matched
            continue
        sections[current].append(stripped)

    return sections


def _extract_personal(preamble_lines: list[str], full_text: str) -> dict:
    email_match = EMAIL_RE.search(full_text)
    phone_match = PHONE_RE.search(full_text)
    urls = URL_RE.findall(full_text)

    github = next((u for u in urls if "github.com" in u.lower()), None)
    linkedin = next((u for u in urls if "linkedin.com" in u.lower()), None)
    portfolio = next(
        (u for u in urls if u not in ({github, linkedin} - {None})), None
    )

    name = None
    for line in preamble_lines[:6]:
        cleaned = re.sub(r"^(?:name|candidate|profile)\s*:\s*", "", line, flags=re.IGNORECASE).strip()
        if EMAIL_RE.search(cleaned) or PHONE_RE.search(cleaned) or URL_RE.search(cleaned):
            continue
        if len(cleaned) < 50 and sum(c.isalpha() or c.isspace() for c in cleaned) > len(cleaned) * 0.6:
            # Avoid single generic words like "RESUME" or "CURRICULUM VITAE"
            if cleaned.upper() not in {"RESUME", "CURRICULUM VITAE", "CV", "BIO-DATA", "BIODATA"}:
                name = cleaned
                break

    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "github": github,
        "linkedin": linkedin,
        "portfolio": portfolio,
    }


def _bulletize(lines: list[str]) -> list[str]:
    """Splits a raw section block into clean individual bullets."""
    bullets = []
    for line in lines:
        cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
        if cleaned:
            bullets.append(cleaned)
    return bullets


def _split_skills(lines: list[str], full_text: str) -> list[str]:
    """
    Extracts skills with high recall:
    1. Parses category prefixes (e.g. 'Languages: Python, Java').
    2. Handles comma, pipe, bullet, or newline delimited lists.
    3. Runs spaCy PhraseMatcher across the full document so no skill is missed.
    """
    found_skills: list[str] = []

    for line in lines:
        cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
        if not cleaned:
            continue
        # Strip category headers if inline
        cleaned = _CATEGORY_PREFIX_RE.sub("", cleaned).strip()

        if re.search(r"[,|•;/]", cleaned):
            parts = re.split(r"[,|•;/]", cleaned)
            for p in parts:
                p_clean = p.strip()
                if p_clean and len(p_clean) < 40 and p_clean not in found_skills:
                    found_skills.append(p_clean)
        else:
            if len(cleaned) < 40 and cleaned not in found_skills:
                found_skills.append(cleaned)

    # Enhance with spaCy NLP extractor across full document for uncaptured skills
    spacy_extracted = extract_skills_from_text(full_text)
    existing_lower = {s.lower() for s in found_skills}
    for s in spacy_extracted:
        if s.lower() not in existing_lower:
            found_skills.append(s)
            existing_lower.add(s.lower())

    return found_skills


def structure_resume_text(full_text: str) -> dict:
    """
    Standardized, robust resume structurer for real-world messy resumes.
    """
    lines = full_text.split("\n")
    sections = _split_into_sections(lines)

    personal = _extract_personal(sections["_preamble"], full_text)
    skills = _split_skills(sections["skills"], full_text)

    return {
        "personal": personal,
        "summary": " ".join(sections["summary"]) if sections["summary"] else None,
        "skills": skills,
        "experience_raw": _bulletize(sections["experience"]),
        "projects_raw": _bulletize(sections["projects"]),
        "internships_raw": _bulletize(sections["internships"]),
        "education_raw": _bulletize(sections["education"]),
        "certifications": _bulletize(sections["certifications"]),
        "achievements": _bulletize(sections["achievements"]),
        "links": [u for u in [personal.get("github"), personal.get("linkedin"), personal.get("portfolio")] if u],
    }

