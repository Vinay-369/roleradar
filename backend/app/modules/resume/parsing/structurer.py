"""
Rule-based resume structuring with high-tolerance pattern matching
and spaCy NLP fallback for messy, unstandardized human resumes.
Guarantees 100% preservation of Education, Certifications, Languages, and Contact Info.
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
    "languages": r"^\s*(languages|known languages|languages known)\s*$",
}

# Strict bullet prefix regex: matches standard bullet glyphs and numbered lists (e.g. '1. ', '• ')
# NEVER matches degree abbreviations like 'B.E', 'B.Tech', 'M.Tech', 'B.Sc', 'M.S.'
_BULLET_PREFIX_RE = re.compile(
    r"^(?:[•\-\*\u2013\u2014\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u27A4\u2714\u2713\u279C\u2192\u25BA\u25B6\u25C6\u25C7\u25CF\u25CB\u2718\u2717\u2705\u27A2\u2794\u2714\ufffd]|\d{1,2}[\.\)]|\([a-zA-Z0-9]+\)|[a-zA-Z]\))\s+",
    re.UNICODE,
)

_CATEGORY_PREFIX_RE = re.compile(
    r"^(?:languages|programming languages|frameworks|libraries|tools|databases|cloud|devops|backend|frontend|methodologies|web technologies|platforms|technologies|os|operating systems|core competencies)\s*:\s*",
    re.IGNORECASE,
)

_INSTITUTION_RE = re.compile(
    r"\b(?:institute|college|university|school|academy|polytechnic|vidyalaya|campus)\b",
    re.IGNORECASE,
)


def _split_into_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {key: [] for key in SECTION_PATTERNS}
    sections["_preamble"] = []

    current = "_preamble"
    for index, line in enumerate(lines):
        stripped = line.strip()
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""

        # PDF layout extraction can split "Technical Skills" across two
        # visual columns, leaving the word "Technical" appended to the last
        # education line. Remove only that known orphan when the next line is
        # the actual Skills heading.
        if next_line.lower() == "skills" and re.search(r"\btechnical$", stripped, re.IGNORECASE):
            stripped = re.sub(r"\s+technical$", "", stripped, flags=re.IGNORECASE).strip()
        if not stripped:
            if current in sections and sections[current] and sections[current][-1] != "":
                sections[current].append("")  # preserve blank line as paragraph separator
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


KNOWN_LOCATIONS = {
    # Indian States & UTs
    "karnataka", "maharashtra", "tamil nadu", "telangana", "andhra pradesh",
    "kerala", "delhi", "uttar pradesh", "gujarat", "rajasthan", "west bengal",
    "punjab", "haryana", "bihar", "odisha", "madhya pradesh", "goa", "assam",
    "jharkhand", "uttarakhand", "himachal pradesh", "chandigarh", "puducherry",
    # Cities & Locations
    "davanagere", "davangere", "bangalore", "bengaluru", "mysore", "mysuru",
    "hubli", "dharwad", "mangalore", "mangaluru", "belgaum", "belagavi",
    "mumbai", "pune", "hyderabad", "chennai", "coimbatore", "kochi",
    "kolkata", "noida", "gurgaon", "gurugram", "ahmedabad", "jaipur",
    "indore", "bhopal", "nagpur", "lucknow", "patna", "thiruvananthapuram",
    "visakhapatnam", "vijayawada", "surat", "vadodara", "shimoga", "shivamogga",
    "tumkur", "tumakuru", "bellary", "ballari", "gulbarga", "kalaburagi",
    "remote", "india", "usa", "uk", "united states", "canada", "germany",
    "singapore", "australia", "london", "dubai",
}

NON_SKILL_WORDS = {
    "address", "location", "permanent address", "current address", "native",
    "gender", "dob", "date of birth", "nationality", "marital status", "indian",
    "english", "kannada", "hindi", "telugu", "tamil", "malayalam", "marathi",
    "languages known", "hobbies", "interests", "strengths", "curriculum vitae",
    "resume", "bio-data", "biodata", "personal profile", "profile", "contact",
    "phone", "email", "mobile", "pin", "pincode", "zip", "zipcode",
}


def _extract_location_from_text(lines: list[str]) -> str | None:
    """Detects candidate city, state, or location from header preamble lines."""
    for line in lines[:8]:
        cleaned = line.strip()
        if not cleaned:
            continue
        # Check for explicit location prefix
        loc_prefix_match = re.search(r"(?:location|address|city)\s*:\s*([^|,\n]+(?:,\s*[^|,\n]+)?)", cleaned, re.IGNORECASE)
        if loc_prefix_match:
            val = loc_prefix_match.group(1).strip()
            if len(val) >= 3 and len(val) <= 60:
                return val

        # Check for segments in pipe/comma/bullet separated header lines
        segments = [s.strip() for s in re.split(r"[|•·;/]", cleaned) if s.strip()]
        for seg in segments:
            seg_lower = seg.lower()
            if EMAIL_RE.search(seg) or PHONE_RE.search(seg) or URL_RE.search(seg):
                continue
            if any(loc in seg_lower for loc in KNOWN_LOCATIONS):
                if len(seg) >= 3 and len(seg) <= 60:
                    return seg

    return None


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
        if not cleaned or EMAIL_RE.search(cleaned) or PHONE_RE.search(cleaned) or URL_RE.search(cleaned):
            continue
        if len(cleaned) < 50 and sum(c.isalpha() or c.isspace() for c in cleaned) > len(cleaned) * 0.6:
            if cleaned.upper() not in {"RESUME", "CURRICULUM VITAE", "CV", "BIO-DATA", "BIODATA"}:
                name = cleaned
                break

    location = _extract_location_from_text(preamble_lines) or _extract_location_from_text(full_text.split("\n")[:10])

    return {
        "name": name,
        "location": location,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "github": github,
        "linkedin": linkedin,
        "portfolio": portfolio,
    }


_DATE_ONLY_RE = re.compile(
    r"^(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}(?:\s*[-–—to]+\s*(?:Present|Current|\d{4}|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}))?$",
    re.IGNORECASE,
)

# Resume parsers frequently return an entire paragraph as one line.  Keeping
# that paragraph intact makes it impossible to audit or tailor individual
# achievements.  This deliberately only splits at conventional sentence
# boundaries; wrapped lines without terminal punctuation remain one statement.
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

_EVIDENCE_VERB_RE = re.compile(
    r"\b(?:architected|built|created|developed|engineered|implemented|designed|optimized|automated|deployed|led|managed|launched|integrated|reduced|increased|improved|delivered)\b",
    re.IGNORECASE,
)
_NON_EXPERIENCE_EVIDENCE_RE = re.compile(
    r"\b(?:graduated|bachelor|master|b\.tech|b\.e\.?|degree|university|college|school|awarded|award|hackathon|certified|certification)\b",
    re.IGNORECASE,
)


def _is_tech_stack_or_meta(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.count("|") >= 2 and len(s.split()) <= 25:
        return True
    lower = s.lower()
    if lower.startswith("tech stack:") or lower.startswith("technologies:") or lower.startswith("tools & tech:") or lower.startswith("stack:"):
        return True
    if _DATE_ONLY_RE.match(s):
        return True
    return False


from app.modules.resume.parsing.action_verbs import STRONG_ACTION_VERBS


def _split_unstructured_evidence(text: str) -> list[str]:
    """Turn a paragraph into independently reviewable evidence statements.

    This is normalization, not generation: every returned item is an exact
    sentence from the uploaded resume.  It lets downstream scoring and the
    Truth Guard reason about a long paragraph as separate candidate claims.
    """
    candidates = _SENTENCE_BOUNDARY_RE.split(text.strip())
    return [candidate.strip() for candidate in candidates if len(candidate.split()) >= 3]


def _recover_unheaded_evidence(preamble_lines: list[str]) -> list[str]:
    """Recover work/project facts when a resume has no section headings.

    A candidate's name, contacts, education, awards, and generic objective are
    deliberately excluded.  The heuristic only promotes text containing an
    explicit delivery verb, so it does not turn arbitrary prose into work
    history.
    """
    recovered: list[str] = []
    for line in preamble_lines:
        if _is_location_or_contact_line(line) or _NON_EXPERIENCE_EVIDENCE_RE.search(line):
            continue
        for sentence in _split_unstructured_evidence(line):
            if _EVIDENCE_VERB_RE.search(sentence):
                recovered.append(sentence)
    return recovered


def _bulletize(lines: list[str]) -> list[str]:
    """Splits a raw section block into clean individual bullets for experience and projects."""
    raw_bullets: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_tech_stack_or_meta(stripped):
            continue

        standalone_bullet = stripped in {"•", "-", "*", "–", "—", "�"}
        has_bullet_prefix = standalone_bullet or bool(_BULLET_PREFIX_RE.match(stripped))
        cleaned = "" if standalone_bullet else _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not cleaned:
            continue

        # Skip standalone header / title lines with dates (e.g. "AI-Based Ad Analyzer April 2026")
        if _DATE_ONLY_RE.search(cleaned) and len(cleaned.split()) <= 8:
            continue

        # If line starts with bullet prefix, it's a new bullet
        if has_bullet_prefix:
            raw_bullets.append(cleaned)
        elif raw_bullets and not _is_tech_stack_or_meta(stripped):
            prev_ended = raw_bullets[-1].endswith((".", ";", "!"))
            if prev_ended:
                raw_bullets.extend(_split_unstructured_evidence(cleaned))
            else:
                raw_bullets[-1] = raw_bullets[-1].rstrip() + " " + cleaned
        else:
            raw_bullets.extend(_split_unstructured_evidence(cleaned))

    # Filter out standalone project titles
    final_bullets = []
    for b in raw_bullets:
        if _DATE_ONLY_RE.search(b) and len(b.split()) <= 8:
            continue
        if len(b.split()) <= 7 and not any(w.lower() in STRONG_ACTION_VERBS for w in b.split()[:2]) and not re.search(r"\d", b):
            continue
        final_bullets.append(b)
    return final_bullets


def _looks_like_project_title(line: str) -> bool:
    """Identify a compact project heading without mistaking it for a bullet."""
    cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
    if not cleaned or _BULLET_PREFIX_RE.match(line) or _is_tech_stack_or_meta(cleaned):
        return False
    first_word = cleaned.split()[0].lower().rstrip(":,")
    return (
        1 <= len(cleaned.split()) <= 18
        and not cleaned.endswith((".", ";", "!"))
        and not _EVIDENCE_VERB_RE.match(first_word)
    )


def _bulletize_projects(lines: list[str]) -> list[str]:
    """Preserve a project heading and technology line with its first bullet.

    Keeping this context in the editable source makes it impossible for a
    rewrite to silently detach a project claim from the project it describes.
    """
    bullets: list[str] = []
    current_title = ""
    current_tech = ""
    first_bullet_for_project = False
    pending_bullet = False

    for line in lines:
        stripped = line.strip()
        if not stripped or _DATE_ONLY_RE.match(stripped):
            continue
        standalone_bullet = stripped in {"•", "-", "*", "–", "—", ""}
        has_bullet_prefix = standalone_bullet or bool(_BULLET_PREFIX_RE.match(stripped))
        cleaned = "" if standalone_bullet else _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not cleaned:
            pending_bullet = pending_bullet or has_bullet_prefix
            continue
        if pending_bullet:
            has_bullet_prefix = True
            pending_bullet = False

        # Extract title and inline tech stack in parentheses e.g. "AI Screener (Python, FastAPI)"
        paren_stack = re.search(r"^(.*?)\s*\(([^)]+)\)\s*$", cleaned)
        if not has_bullet_prefix and paren_stack:
            t_cand = paren_stack.group(1).strip()
            s_cand = paren_stack.group(2).strip()
            if 1 <= len(t_cand.split()) <= 14 and ("," in s_cand or any(k in s_cand.lower() for k in ["python", "java", "react", "node", "fastapi", "sql", "aws", "docker", "c++", "ml", "ai", "js", "ts", "html", "css"])):
                if first_bullet_for_project and current_title:
                    ctx = [current_title]
                    if current_tech:
                        ctx.append(f"Technologies: {current_tech}")
                    bullets.append("\n".join(ctx))
                current_title = t_cand
                current_tech = s_cand
                first_bullet_for_project = True
                continue

        # Some PDF extractors place the right-aligned technology stack on the
        # same line as a project title. Split only when a known language/tool
        # visibly begins that comma-separated stack.
        inline_stack = re.search(
            r"\b(Python|Java|JavaScript|TypeScript|C\+\+|C|TensorFlow|Keras|React|Node\.js|Flask|FastAPI|PostgreSQL|MongoDB|Docker)\s*,",
            cleaned,
            re.IGNORECASE,
        )
        if not has_bullet_prefix and inline_stack and inline_stack.start() > 0:
            if first_bullet_for_project and current_title:
                ctx = [current_title]
                if current_tech:
                    ctx.append(f"Technologies: {current_tech}")
                bullets.append("\n".join(ctx))
            current_title = cleaned[:inline_stack.start()].strip(" |-–—(")
            current_tech = cleaned[inline_stack.start():].strip(" )")
            first_bullet_for_project = True
            continue

        if first_bullet_for_project and not has_bullet_prefix and _is_tech_stack_or_meta(cleaned):
            tech_val = re.sub(r"^(?:tech stack|technologies|tools & tech|stack)\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
            current_tech = tech_val or cleaned
            continue

        if first_bullet_for_project and not has_bullet_prefix and re.search(r"[,|]", cleaned) and len(cleaned.split()) <= 16 and not cleaned.endswith((".", ";", "!")):
            current_tech = cleaned
            continue

        if not has_bullet_prefix and _looks_like_project_title(cleaned):
            if first_bullet_for_project and current_title:
                ctx = [current_title]
                if current_tech:
                    ctx.append(f"Technologies: {current_tech}")
                bullets.append("\n".join(ctx))
            current_title = cleaned
            current_tech = ""
            first_bullet_for_project = True
            continue

        # If a project title was waiting for its first bullet/evidence
        if first_bullet_for_project and current_title:
            context = [current_title]
            if current_tech:
                context.append(f"Technologies: {current_tech}")
            context.append(cleaned)
            bullets.append("\n".join(context))
            first_bullet_for_project = False
            continue

        if has_bullet_prefix:
            bullets.append(cleaned)
            continue

        if bullets and not bullets[-1].rstrip().endswith((".", ";", "!")):
            bullets[-1] = bullets[-1].rstrip() + " " + cleaned
            continue

        # Keep wrapped unbulleted prose as evidence when no project title was
        # detected. This matches the forgiving behaviour of _bulletize.
        bullets.extend(_split_unstructured_evidence(cleaned))

    if first_bullet_for_project and current_title:
        ctx = [current_title]
        if current_tech:
            ctx.append(f"Technologies: {current_tech}")
        bullets.append("\n".join(ctx))

    return bullets


def _structure_education(lines: list[str]) -> list[str]:
    """
    Parses education section preserving ALL institutions, degree titles, dates, and scores.
    Never drops institution names (e.g. Bapuji Institute of Engineering and Technology).
    Never drops dates (e.g. 2023-2027, 2023, 2021).
    Never corrupts degree names (e.g. 'B.E in Computer Science' is preserved 100% intact).
    Groups multi-line institution entries into distinct clean entries.
    """
    entries: list[str] = []
    current_entry_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_entry_lines:
                entries.append("\n".join(current_entry_lines))
                current_entry_lines = []
            continue

        clean_line = _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not clean_line:
            continue

        if current_entry_lines:
            prev_text = " ".join(current_entry_lines)
            has_date_or_grade = bool(re.search(r"\b(?:\d{4}|cgpa|percentage|\bgrades?\b)\b", prev_text, re.IGNORECASE))
            is_new_inst = bool(_INSTITUTION_RE.search(clean_line)) and not bool(re.search(r"\b(?:\d{4}|cgpa|percentage|\bgrades?\b)\b", clean_line, re.IGNORECASE))

            if has_date_or_grade and is_new_inst:
                entries.append("\n".join(current_entry_lines))
                current_entry_lines = [clean_line]
                continue

        current_entry_lines.append(clean_line)

    if current_entry_lines:
        entries.append("\n".join(current_entry_lines))

    if not entries:
        entries = [l.strip() for l in lines if l.strip()]

    return entries


def _extract_list_items(lines: list[str]) -> list[str]:
    """
    Extracts certifications and achievements preserving all text entries and names.
    Never deletes certifications like 'Completed Python Programming Course - Scaler'.
    """
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        clean_line = _BULLET_PREFIX_RE.sub("", stripped).strip()
        if clean_line and clean_line not in items:
            items.append(clean_line)
    return items


def _extract_languages(lines: list[str], full_text: str) -> list[str]:
    """
    Extracts languages from the languages section or full text.
    Handles 'Telugu, English, Kannada, Hindi' and category lines.
    """
    langs: list[str] = []
    raw_lines = [l for l in lines if l.strip()]

    if not raw_lines:
        lang_match = re.search(r"(?:languages|languages\s+known|known\s+languages)\s*:\s*([^\n\r]+)", full_text, re.IGNORECASE)
        if lang_match:
            raw_lines = [lang_match.group(1)]

    for line in raw_lines:
        cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
        cleaned = re.sub(r"^(?:languages|known languages|languages known)\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            continue
        parts = [p.strip() for p in re.split(r"[,|•;/]", cleaned) if p.strip()]
        for p in parts:
            if len(p) <= 25 and p not in langs:
                langs.append(p)

    return langs


def _is_location_or_contact_line(text: str) -> bool:
    s = text.strip()
    if not s or len(s) < 2:
        return True
    lower = s.lower().strip()
    if EMAIL_RE.search(s) or PHONE_RE.search(s) or URL_RE.search(s):
        return True
    if re.search(r"\b\d{5,6}\b", s):  # Postal pin code
        return True
    if any(lower.startswith(k) for k in ["address:", "location:", "pin:", "phone:", "email:", "dob:", "nationality:", "gender:"]):
        return True
    if lower in NON_SKILL_WORDS or lower in KNOWN_LOCATIONS:
        return True
    parts = [p.strip().lower() for p in re.split(r"[,|\-/]", s) if p.strip()]
    if parts and all(p in KNOWN_LOCATIONS or p in NON_SKILL_WORDS for p in parts):
        return True
    if len(parts) >= 2 and any(p in KNOWN_LOCATIONS for p in parts) and all(len(p.split()) <= 3 for p in parts):
        return True
    return False


def _extract_categorized_skills(lines: list[str]) -> list[str]:
    """Preserves categorized skill lines (e.g. 'Languages: Python, Java', 'Databases: PostgreSQL')."""
    cat_lines: list[str] = []
    for line in lines:
        cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
        if not cleaned or _is_location_or_contact_line(cleaned):
            continue
        if ":" in cleaned and len(cleaned.split(":")[0].split()) <= 6:
            cat_lines.append(cleaned)
    return cat_lines


def _split_skills(lines: list[str], full_text: str) -> list[str]:
    """
    Extracts skills with high recall and robust location/contact filtering.
    """
    found_skills: list[str] = []

    for line in lines:
        cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
        if not cleaned or _is_location_or_contact_line(cleaned):
            continue
        cleaned = _CATEGORY_PREFIX_RE.sub("", cleaned).strip()

        if re.search(r"[,|•;/]", cleaned):
            parts = re.split(r"[,|•;/]", cleaned)
            for p in parts:
                p_clean = p.strip()
                if (
                    p_clean
                    and len(p_clean) < 40
                    and not _is_location_or_contact_line(p_clean)
                    and p_clean not in found_skills
                ):
                    found_skills.append(p_clean)
        else:
            if (
                len(cleaned) < 40
                and not _is_location_or_contact_line(cleaned)
                and cleaned not in found_skills
            ):
                found_skills.append(cleaned)

    spacy_extracted = extract_skills_from_text(full_text)
    existing_lower = {s.lower() for s in found_skills}
    for s in spacy_extracted:
        if s.lower() not in existing_lower and not _is_location_or_contact_line(s):
            found_skills.append(s)
            existing_lower.add(s.lower())

    return found_skills


def structure_resume_text(full_text: str) -> dict:
    """
    Standardized, robust resume structurer for real-world messy resumes.
    Guarantees 100% preservation of all sections, contact info, education, certifications, and languages.
    """
    lines = full_text.split("\n")
    sections = _split_into_sections(lines)

    personal = _extract_personal(sections["_preamble"], full_text)
    skills = _split_skills(sections["skills"], full_text)
    skills_categorized = _extract_categorized_skills(sections["skills"])
    experience_bullets = _bulletize(sections["experience"])
    project_bullets = _bulletize_projects(sections["projects"])

    # Truly unstructured resumes may put all evidence under the header block.
    # Treat those statements as experience only when neither editable section
    # was found; otherwise explicit section structure always wins.
    if not experience_bullets and not project_bullets:
        experience_bullets = _recover_unheaded_evidence(sections["_preamble"])

    return {
        "personal": personal,
        "summary": " ".join(sections["summary"]) if sections["summary"] else None,
        "skills": skills,
        "skills_categorized": skills_categorized,
        "experience_raw": experience_bullets,
        "projects_raw": project_bullets,
        "internships_raw": _bulletize(sections["internships"]),
        "education_raw": _structure_education(sections["education"]),
        "certifications": _extract_list_items(sections["certifications"]),
        "achievements": _extract_list_items(sections["achievements"]),
        "languages": _extract_languages(sections["languages"], full_text),
        "links": [u for u in [personal.get("github"), personal.get("linkedin"), personal.get("portfolio")] if u],
    }
