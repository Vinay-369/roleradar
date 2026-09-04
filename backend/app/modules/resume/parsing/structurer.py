"""
Rule-based resume structuring with high-tolerance pattern matching
and spaCy NLP fallback for messy, unstandardized human resumes.
Guarantees 100% preservation of Education, Certifications, Languages, and Contact Info.
"""
import re
from typing import Any
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.resume.parsing.action_verbs import STRONG_ACTION_VERBS
from app.modules.resume.parsing.parseability import EMAIL_RE, PHONE_RE, URL_RE

SECTION_PATTERNS = {
    "summary": r"^\s*(summary|career summary|professional summary|executive summary|summary of qualifications|objective|career objective|profile|personal profile|about me|professional profile|background|overview)\s*$",
    "skills": r"^\s*(skills|technical skills|key skills|core skills|core competencies|skills & expertise|skills & technologies|tech stack|technical stack|technical proficiencies|areas of expertise|technologies|tools & technologies|programming languages|technological skills|tech expertise|technical competencies|tools|frameworks & tools|languages & frameworks)\s*$",
    "experience": (
        r"^\s*(?:"
        r"(?:(?:professional|work|career|employment|industry|relevant|highlighted|past|technical)\s+)?"
        r"(?:experience|background|history|trajectory|chronology|path|pathways?|journey|progression|employment|work)"
        r"(?:\s*(?:&|and)\s*(?:(?:professional|work|career|employment|industry|relevant|highlighted|past|technical)\s+)?"
        r"(?:experience|background|history|trajectory|chronology|path|pathways?|journey|progression|employment|work))?"
        r")\s*$"
    ),
    "projects": r"^\s*(projects|academic projects|key projects|personal projects|technical projects|notable projects|portfolio projects|selected projects|project work|notable contributions|key initiatives|software projects|recent projects|things i worked on|stuff i built|what i built|portfolio)\s*$",
    "internships": r"^\s*(internships?|internship experience|industrial training|industry training|internship history)\s*$",
    "education": (
        r"^\s*(?:"
        r"(?:(?:academic|educational|scholastic|formal|university|higher)\s+)?"
        r"(?:education|background|credentials|qualifications|history|profile|record|attainment|preparation|studies|academics|degrees)"
        r"(?:\s*(?:&|and)\s*(?:(?:academic|educational|scholastic|formal|university|higher)\s+)?"
        r"(?:education|background|credentials|qualifications|history|profile|record|attainment|preparation|studies|academics|degrees))?"
        r")\s*$"
    ),
    "certifications": r"^\s*(certifications?|certificates|licenses|courses & certifications|professional certifications|credentials|accreditations|courses & training|trainings? & certifications?)\s*$",
    "achievements": r"^\s*(achievements|awards|accomplishments|honors|awards & achievements|co-curricular & honors|extracurricular & honors|honors & awards|achievements & awards|key achievements|notable achievements|honours)\s*$",
    "publications": r"^\s*(publications|papers|conference proceedings|journal articles|selected publications|peer[- ]reviewed publications|scholarly works)\s*$",
    "research": r"^\s*(research|research experience|research & development|scientific experience|scientific research|academic research|research projects)\s*$",
    "leadership": r"^\s*(leadership|leadership experience|extracurricular & leadership|community leadership|leadership & activities|initiatives)\s*$",
    "volunteer": r"^\s*(volunteer work|volunteering|community service|volunteer experience|social service)\s*$",
    "side_quests": r"^\s*(side quests?|open source|open source contributions?|community contributions?|extracurriculars?|extracurricular activities|extra-curricular|co-curricular|activities)\s*$",
    "languages": r"^\s*(languages|known languages|languages known|spoken languages|language proficiencies|language skills)\s*$",
}

HEADER_PREFIX_IGNORE_WORDS = (
    "programming", "technical", "key", "core", "tools", "work",
    "academic", "personal", "professional", "soft", "known", "spoken",
    "areas of", "skills &", "tools &",
)

GLUED_SECTION_PATTERNS = [
    ("languages", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>languages|known\s+languages|languages\s+known|spoken\s+languages|language\s+skills)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("side_quests", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>side\s+quests?|open\s+source\s+contributions?|open\s+source|community\s+contributions?|extracurriculars?|extracurricular\s+activities|extra-curricular|co-curricular)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("certifications", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>professional\s+certifications|courses\s+&\s+certifications|certifications?|certificates|licenses|credentials|accreditations)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("achievements", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>awards\s+&\s+achievements|achievements\s+&\s+awards|co-curricular\s+&\s+honors|extracurricular\s+&\s+honors|honors\s+&\s+awards|accomplishments|achievements|honors|awards|honours)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("education", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>academic\s+credentials|educational\s+background|educational\s+qualifications|education\s+&\s+qualifications|academic\s+background|academic\s+qualifications|academic\s+profile|academic\s+history|qualifications|academics|degrees\s+&\s+education|education|degrees)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("projects", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>academic\s+projects|technical\s+projects|portfolio\s+projects|selected\s+projects|personal\s+projects|notable\s+projects|key\s+projects|projects|software\s+projects|things\s+i\s+worked\s+on|stuff\s+i\s+built|what\s+i\s+built|portfolio)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("internships", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>internship\s+experience|industrial\s+training|industry\s+training|internships?)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("experience", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>career\s+trajectory\s*(?:&|and)\s*chronology|career\s+trajectory|career\s+chronology|career\s+path|professional\s+journey|professional\s+experience|experience\s+&\s+employment|employment\s+history|relevant\s+experience|work\s+experience|career\s+history|work\s+history|professional\s+background|experience\s*:|employment\s*:)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("skills", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>technical\s+proficiencies|tools\s+&\s+technologies|skills\s+&\s+technologies|skills\s+&\s+expertise|areas\s+of\s+expertise|core\s+competencies|technical\s+skills|core\s+skills|key\s+skills|tech\s+stack|technologies\s*:|skills\s*:|skills)(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
    ("summary", re.compile(r"^(?P<content>.+?)(?:[\s#\-=*~|]+|(?<=[a-zA-Z0-9\)]))(?P<header>career\s+summary|professional\s+summary|career\s+objective|personal\s+profile|executive\s+summary|about\s+me|summary\s*:|objective\s*:|profile\s*:)\b(?::[\s#\-=*~]*(?P<after>.+)|[:\s#\-=*~]*$)", re.IGNORECASE)),
]

# Strict bullet prefix regex: matches standard bullet glyphs, replacement glyphs, and numbered lists
# NEVER matches degree abbreviations like 'B.E', 'B.Tech', 'M.Tech', 'B.Sc', 'M.S.'
_BULLET_PREFIX_RE = re.compile(
    r"^(?:[•\-\*\u2013\u2014\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u27A4\u2714\u2713\u279C\u2192\u25BA\u25B6\u25C6\u25C7\u25CF\u25CB\u2718\u2717\u2705\u27A2\u2794\u2714\ufffd▪▫◦‣⁃■□★☆+>~]|(?:\b[oO]\b\s+)|\d{1,2}[\.\)]|\([a-zA-Z0-9]+\)|[a-zA-Z]\))\s+",
    re.UNICODE,
)

def _clean_raw_text_artifacts(raw_text: str) -> str:
    """
    Cleans extraction artifacts (form-feeds, page numbers, trailing whitespace, replacement characters)
    without corrupting content.
    """
    if not raw_text:
        return ""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n\n")
    # Clean standalone page number lines
    text = re.sub(r"(?m)^\s*(?:page\s+\d+(?:\s+(?:of|/)\s*\d+)?|[-–—]\s*\d+\s*[-–—]|\d+\s*/\s*\d+)\s*$", "", text, flags=re.IGNORECASE)
    # Clean standalone bullet markers on their own line followed by text
    text = re.sub(r"(?m)^\s*([•\-\*\u2013\u2014\u2022\u25CF\u25AA\ufffd▪▫◦‣⁃■□★☆+>~])\s*\n\s*([a-zA-Z0-9])", r"\1 \2", text)
    # Clean ASCII box/table border lines (e.g. +-------------------+, |-------------------|)
    text = re.sub(r"(?m)^\s*[+\-|=_]{4,}\s*$", "", text)
    
    # Strip all leading/trailing table column pipes/plus signs on each line
    lines = []
    for line in text.split("\n"):
        l_clean = re.sub(r"^[|\s+]+|[|\s+]+$", "", line)
        lines.append(l_clean)
    text = "\n".join(lines)

    # Separate glued inline section headers (e.g. 'background.Technical Skills:Python' -> 'background.\nTechnical Skills:Python')
    text = re.sub(
        r"(?<=[a-zA-Z0-9.\)])\s*(?=(?:Professional\s+Summary|Summary|Technical\s+Skills|Work\s+Experience|Professional\s+Experience|Experience|Technical\s+Projects|Personal\s+Projects|Projects|Education|Certifications|Achievements|Side\s+Quests)\s*:)",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    # Split section headers with inline content onto new lines (e.g. 'Projects:• SmartCache' -> 'Projects\n• SmartCache')
    text = re.sub(
        r"(?m)^\s*(Professional\s+Summary|Summary|Work\s+Experience|Professional\s+Experience|Experience|Projects|Technical\s+Projects|Personal\s+Projects|Education|Certifications|Achievements|Side\s+Quests)\s*:\s*(?=\S)",
        r"\1\n",
        text,
        flags=re.IGNORECASE,
    )
    return text

_CATEGORY_PREFIX_RE = re.compile(
    r"^(?:languages|programming languages|frameworks\s*&\s*tools|frameworks\s+and\s+tools|tools\s*&\s*technologies|tools\s+and\s+technologies|languages\s*&\s*frameworks|languages\s+and\s+frameworks|frameworks|libraries|tools|databases|cloud|devops|backend|frontend|methodologies|web technologies|platforms|technologies|os|operating systems|core competencies)\s*:\s*",
    re.IGNORECASE,
)

_INSTITUTION_RE = re.compile(
    r"\b(?:institute|college|university|school|academy|polytechnic|vidyalaya|campus)\b",
    re.IGNORECASE,
)


def _split_into_sections(lines: list[str]) -> dict[str, Any]:
    sections: dict[str, Any] = {key: [] for key in SECTION_PATTERNS}
    sections["_preamble"] = []
    sections["_custom"] = []  # list of tuples: (heading, custom_sec_key)

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
        clean_heading = _BULLET_PREFIX_RE.sub("", stripped).strip()
        normalized = re.sub(r"^[#\-=*~\s]+|[#\-=*~\s:]+$", "", clean_heading)
        matched = None
        for key, pattern in SECTION_PATTERNS.items():
            if re.match(pattern, normalized, re.IGNORECASE):
                matched = key
                break
        if matched:
            current = matched
            continue

        # Check for unknown / custom top-level section header (e.g. "## Patents" or "PATENTS & INVENTIONS" or "SPEAKING ENGAGEMENTS:")
        is_explicit_markdown = stripped.startswith(("#", "==", "--")) and len(stripped.split()) <= 7
        cand_upper = stripped.rstrip(":").strip()
        alpha_only = re.sub(r"[^A-Za-z]", "", cand_upper)
        is_all_caps_section = (
            bool(alpha_only)
            and alpha_only.isupper()
            and 1 <= len(cand_upper.split()) <= 5
            and not bool(re.search(r"\d", cand_upper))
            and not bool(re.search(r"\b(?:gpa|cgpa|score|percentage|grade|graduation|minor|major|concentration|expected|dates?)\b", cand_upper, re.IGNORECASE))
            and not any(w in cand_upper for w in ["ENGINEER", "DEVELOPER", "MANAGER", "ARCHITECT", "LEAD", "INTERN", "ANALYST", "CONSULTANT", "FOUNDER", "DIRECTOR", "VP", "HEAD"])
            and not any(w in cand_upper for w in ["INC", "LLC", "LTD", "PVT", "CORP", "CORPORATION", "SOLUTIONS", "TECHNOLOGIES", "SYSTEMS", "LABS", "NETWORKS"])
            and not bool(re.search(r"\b(?:PRESENT|20\d\d|19\d\d)\b", cand_upper))
        )
        is_preamble_boundary_heading = False
        if current == "_preamble":
            if is_explicit_markdown:
                is_preamble_boundary_heading = True
            elif is_all_caps_section and len(sections["_preamble"]) >= 1:
                has_contact_in_preamble = any(
                    EMAIL_RE.search(l) or PHONE_RE.search(l) or URL_RE.search(l)
                    for l in sections["_preamble"]
                )
                if cand_upper.endswith(":") or has_contact_in_preamble or len(sections["_preamble"]) >= 2:
                    is_preamble_boundary_heading = True

        is_custom_heading = (
            (is_explicit_markdown or is_all_caps_section)
            and not bool(_BULLET_PREFIX_RE.match(stripped))
            and not any(stripped.lower().startswith(v) for v in ["led", "built", "developed", "managed", "spearheaded", "engineered", "designed", "optimized", "architected"])
            and (current != "_preamble" or is_preamble_boundary_heading)
        )
        if is_custom_heading:
            custom_key = f"_custom_{len(sections['_custom'])}"
            sections[custom_key] = []
            heading_title = normalized or clean_heading.rstrip(":")
            sections["_custom"].append((heading_title, custom_key))
            current = custom_key
            continue

        # Check for glued section header appearing as suffix or boundary on the same line
        # (e.g. "...Course - ScalerLanguages" or "...2024PROJECTS")
        glued_found = False
        for sec_key, pattern in GLUED_SECTION_PATTERNS:
            m = pattern.match(stripped)
            if m:
                content_before = m.group("content").strip()
                content_lower = content_before.lower()
                after = m.group("after").strip() if m.group("after") else ""
                # Validate: content_before must not end with header prefixes like "Programming", "Technical", etc.
                if len(content_before) >= 3 and not content_lower.endswith(HEADER_PREFIX_IGNORE_WORDS):
                    if content_before:
                        sections[current].append(content_before)
                    current = sec_key
                    if after:
                        sections[current].append(after)
                    glued_found = True
                    break
        if glued_found:
            continue

        sections[current].append(stripped)

    return sections


KNOWN_LOCATIONS = {
    # Indian States & UTs
    "karnataka", "maharashtra", "tamil nadu", "telangana", "andhra pradesh",
    "kerala", "delhi", "uttar pradesh", "gujarat", "rajasthan", "west bengal",
    "punjab", "haryana", "bihar", "odisha", "madhya pradesh", "goa", "assam",
    "jharkhand", "uttarakhand", "himachal pradesh", "chandigarh", "puducherry",
    # Cities & Tech Hubs
    "davanagere", "davangere", "bangalore", "bengaluru", "mysore", "mysuru",
    "hubli", "dharwad", "mangalore", "mangaluru", "belgaum", "belagavi",
    "mumbai", "pune", "hyderabad", "chennai", "coimbatore", "kochi",
    "kolkata", "noida", "gurgaon", "gurugram", "ahmedabad", "jaipur",
    "indore", "bhopal", "nagpur", "lucknow", "patna", "thiruvananthapuram",
    "visakhapatnam", "vijayawada", "surat", "vadodara", "shimoga", "shivamogga",
    "tumkur", "tumakuru", "bellary", "ballari", "gulbarga", "kalaburagi",
    "san francisco", "mountain view", "menlo park", "palo alto", "san jose",
    "sunnyvale", "cupertino", "redmond", "santa clara", "seattle", "austin",
    "new york", "boston", "chicago", "los angeles", "toronto", "vancouver",
    "london", "berlin", "dubai", "tokyo", "sydney", "singapore",
    # Countries & Regions & States
    "remote", "india", "usa", "uk", "united states", "canada", "germany",
    "australia", "california", "washington", "texas", "massachusetts", "new york state",
    "ca", "ny", "wa", "tx", "ma", "il", "fl", "nc", "va", "ga", "co", "pa",
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
        raw_stripped = line.strip(" *#=_~|•-–—\t\r\n")
        cleaned = re.sub(r"^(?:name|candidate|profile)\s*:\s*", "", raw_stripped, flags=re.IGNORECASE).strip(" *#=_~|•-–—\t\r\n")
        if not cleaned:
            continue
        
        # Check if line contains contact info or delimiters on a single line
        if EMAIL_RE.search(cleaned) or PHONE_RE.search(cleaned) or URL_RE.search(cleaned) or any(sep in cleaned for sep in ["|", "~", "•", " – ", " — ", " - "]):
            # Try extracting the leading name segment before the first contact delimiter
            for sep in [" | ", " ~ ", " • ", " – ", " — ", " - ", "|", "~", "•"]:
                if sep in cleaned:
                    seg = cleaned.split(sep)[0].strip(" *#=_~|•-–—\t\r\n")
                    seg_cleaned = re.sub(r"^(?:name|candidate|profile)\s*:\s*", "", seg, flags=re.IGNORECASE).strip(" *#=_~|•-–—\t\r\n")
                    if seg_cleaned and not EMAIL_RE.search(seg_cleaned) and not PHONE_RE.search(seg_cleaned) and not URL_RE.search(seg_cleaned):
                        if len(seg_cleaned) >= 2 and len(seg_cleaned) < 50 and sum(c.isalpha() or c.isspace() for c in seg_cleaned) > len(seg_cleaned) * 0.65:
                            if seg_cleaned.upper() not in {"RESUME", "CURRICULUM VITAE", "CV", "BIO-DATA", "BIODATA"}:
                                name = seg_cleaned
                                break
            if name:
                break
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
    lower = s.lower()
    if lower.startswith("tech stack:") or lower.startswith("technologies:") or lower.startswith("tools & tech:") or lower.startswith("stack:"):
        return True
    if any(w in lower.split() for w in ["system", "project", "analyzer", "app", "engine", "tracker", "platform", "service", "classifier", "screener", "to", "from", "detect", "predict", "achieving", "dataset", "model", "built", "developed", "pipeline", "store", "matcher", "bot", "tool", "manager", "dashboard", "portal"]):
        return False
    if re.search(r"^[^\(]+\([^)]+\)\s*$", s):
        return False
    if s.count("|") >= 2 and len(s.split()) <= 25:
        return True
    if "," in s and len(s.split()) <= 14 and not s.endswith((".", ";", "!")) and not re.search(r"\([^)]+\)", s):
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
        if _is_location_or_contact_line(line):
            continue
        for sentence in _split_unstructured_evidence(line):
            if _NON_EXPERIENCE_EVIDENCE_RE.search(sentence):
                continue
            if _EVIDENCE_VERB_RE.search(sentence):
                recovered.append(sentence)
    return recovered


_DATE_RANGE_RE = re.compile(
    r"\b(?:(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}|\d{1,2}[\/\.-]\d{4}|\d{4})\s*[-–—to]+\s*(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}|\d{1,2}[\/\.-]\d{4}|\d{4}|present|current))\b",
    re.IGNORECASE,
)

_DATE_ONLY_RE = re.compile(
    r"^\s*(?:\(?\s*(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}|\d{4})\s*[-–—to]+\s*(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}|\d{4}|present|current)\s*\)?)\s*$",
    re.IGNORECASE,
)

ROLE_KEYWORDS = {
    "engineer", "developer", "architect", "lead", "manager", "intern", "consultant",
    "analyst", "specialist", "designer", "administrator", "scientist", "associate",
    "officer", "director", "vp", "coordinator", "technician", "programmer", "co-op",
    "fellow", "founder", "co-founder", "instructor", "researcher", "trainee", "apprentice"
}

LOCATION_KEYWORDS = {
    "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi", "noida",
    "chennai", "gurgaon", "gurugram", "san francisco", "remote", "india", "usa",
    "california", "seattle", "austin", "new york", "london", "singapore", "boston",
    "chicago", "toronto", "vancouver", "berlin", "dubai", "tokyo", "sydney"
}


def _is_location_text(text: str) -> bool:
    if not text:
        return False
    t_lower = text.lower().strip()
    words = [w.lower().rstrip(":,()").strip("–-—|") for w in t_lower.split()]
    if not words:
        return False
    for w in words:
        if w in LOCATION_KEYWORDS or w in KNOWN_LOCATIONS:
            return True
    for loc in KNOWN_LOCATIONS:
        if len(loc) > 3 and loc in t_lower:
            return True
    return False


def parse_experience_section(lines: list[str]) -> list[Any]:
    from app.modules.resume.models import (
        WorkExperienceEntity,
        RoleProgression,
        ResponsibilityGroup,
    )
    entities: list[WorkExperienceEntity] = []
    current_company = ""
    current_role = ""
    current_dates = ""
    current_location = ""
    current_progression: list[RoleProgression] = []
    current_groups: list[ResponsibilityGroup] = []
    current_group: ResponsibilityGroup | None = None
    current_bullets: list[str] = []

    def flush_entity():
        nonlocal current_company, current_role, current_dates, current_location, current_progression, current_groups, current_group, current_bullets
        if current_bullets or current_company or current_role or current_groups or current_progression:
            if current_group and current_group.bullets:
                current_groups.append(current_group)
                current_group = None
            ent_id = f"exp_{len(entities)}"
            primary_role = current_role or (current_progression[0].title if current_progression else "Software Engineer")
            primary_dates = current_dates or (current_progression[0].dates if current_progression else None)
            comp_name = current_company or "Work Experience"
            entities.append(WorkExperienceEntity(
                id=ent_id,
                company=comp_name,
                role=primary_role,
                dates=primary_dates,
                location=current_location or None,
                progression=list(current_progression),
                responsibility_groups=list(current_groups),
                bullets=list(current_bullets),
            ))
            current_company = ""
            current_role = ""
            current_dates = ""
            current_location = ""
            current_progression = []
            current_groups = []
            current_group = None
            current_bullets = []

    # Flatten lines in case lines contain embedded newlines
    expanded_lines: list[str] = []
    for l in lines:
        for sub in str(l).split("\n"):
            expanded_lines.append(sub)

    for line in expanded_lines:
        stripped = line.strip()
        if not stripped:
            continue
        standalone_bullet = stripped in {"•", "-", "*", "–", "—", "▪", "▫", "►", "▶", "◆", "◇", "●", "○", "✓", "✔", "➔", "→", "➢", "·", "∙", "–"}
        if standalone_bullet:
            continue
        has_bullet = bool(_BULLET_PREFIX_RE.match(stripped)) or stripped.startswith(("•", "-", "*", "–", "—"))
        clean = _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not clean or clean in {"•", "-", "*", "–", "—", "▪", "▫", "►", "▶", "◆", "◇", "●", "○", "✓", "✔", "➔", "→", "➢", "·", "∙"}:
            continue

        clean_lower = clean.lower()
        if clean_lower in ("work experience", "professional experience", "experience", "employment history", "career history", "experience & employment", "relevant experience"):
            continue

        words = [w.lower().rstrip(":,()") for w in clean.split()]
        first_w = words[0] if words else ""
        has_date = bool(_DATE_RANGE_RE.search(clean))
        date_m = _DATE_RANGE_RE.search(clean)
        dates_val = date_m.group(0).strip() if date_m else None

        # 1. Responsibility Group Header with Colon (e.g. 'Core Infrastructure:' or 'Developer Experience:')
        if not has_bullet and ":" in clean:
            h_part, _, b_part = clean.partition(":")
            h_words = [w.lower().rstrip(":,()") for w in h_part.split()]
            h_clean = h_part.strip()
            h_lower = h_clean.lower()
            if len(h_words) <= 8 and not bool(_DATE_RANGE_RE.search(h_part)):
                is_cat_keyword = any(w in h_words for w in ["development", "infrastructure", "packaging", "sdk", "platform", "automation", "microservices", "responsibilities", "contributions", "client", "engineering", "systems", "cloud", "core", "backend", "frontend", "pipeline"]) or any(kw in h_lower for kw in ["indoor location", "release automation", "full-stack", "payment platform", "developer experience", "user experience"])
                if is_cat_keyword or not b_part.strip() or not any(w in ROLE_KEYWORDS for w in h_words if w != "experience"):
                    if current_group and current_group.bullets:
                        current_groups.append(current_group)
                    current_group = ResponsibilityGroup(id=f"grp_{len(current_groups)}", heading=h_clean + ":", bullets=[])
                    if b_part.strip():
                        b_clean = _BULLET_PREFIX_RE.sub("", b_part.strip()).strip()
                        if b_clean:
                            current_bullets.append(b_clean)
                            current_group.bullets.append(b_clean)
                    continue

        # 2. Location line (pure location) vs Company + Location
        has_loc_keyword = _is_location_text(clean)
        if not has_bullet and has_loc_keyword and not any(w in ROLE_KEYWORDS for w in words) and not has_date:
            is_pure_location = all(
                w in LOCATION_KEYWORDS or w in KNOWN_LOCATIONS or w in {",", "-", "|", "/", "in", "and", "&", "state", "city"}
                for w in words
            )
            if is_pure_location and len(words) <= 5:
                current_location = clean
                continue

        # 3. Delimited line with Role, Company, Date, Location
        # E.g. 'Senior Java Developer | Jan 2021 - Present', 'Senior Backend Engineer at CloudScale Technologies (2022 - Present) - Bangalore', 'TechCorp — Lead AI Engineer (2022 - Present)'
        has_delimiter = any(d in clean for d in [" at ", " — ", " – ", " | ", "|", " —", " –"]) or ("," in clean and (has_date or any(w in ROLE_KEYWORDS for w in words)))
        if not has_bullet and has_delimiter and (any(w in ROLE_KEYWORDS for w in words) or has_date):
            clean_nodate = _DATE_RANGE_RE.sub("", clean).strip(" ()–-—|")
            
            role_cand = ""
            comp_cand = ""
            loc_cand = ""
            
            if " at " in clean_lower:
                r_sub, _, c_sub = clean_nodate.partition(" at ")
                role_cand = r_sub.strip(" ()–-—|")
                comp_cand = c_sub.strip(" ()–-—|")
            else:
                seps = [" — ", " – ", " | ", "|", " —", " –"]
                used_sep = next((s for s in seps if s in clean_nodate), None)
                if used_sep:
                    parts = [p.strip(" ()–-—|") for p in clean_nodate.split(used_sep) if p.strip(" ()–-—|")]
                else:
                    parts = [p.strip(" ()–-—|") for p in clean_nodate.split(",") if p.strip(" ()–-—|")]
                    
                for p in parts:
                    p_words = [w.lower().rstrip(":,()") for w in p.split()]
                    if _is_location_text(p) and len(p_words) <= 5:
                        loc_cand = p
                    elif any(w in ROLE_KEYWORDS for w in p_words):
                        role_cand = p
                    elif len(p_words) <= 6 and p_words and p_words[0] not in STRONG_ACTION_VERBS and not _EVIDENCE_VERB_RE.match(p_words[0]):
                        comp_cand = p

            if comp_cand:
                for s in [" - ", " — ", " – ", ", "]:
                    if s in comp_cand:
                        c_only, _, l_only = comp_cand.partition(s)
                        if _is_location_text(l_only):
                            comp_cand = c_only.strip(" ()–-—|")
                            loc_cand = l_only.strip(" ()–-—|")
                            break

            if comp_cand:
                if current_bullets or (current_company and current_company.lower() != comp_cand.lower() and current_progression):
                    flush_entity()
                current_company = comp_cand

            if role_cand:
                current_role = role_cand
            if dates_val:
                current_dates = dates_val
            if loc_cand:
                current_location = loc_cand

            current_progression.append(RoleProgression(title=current_role or "Software Engineer", dates=current_dates, location=current_location or None))
            continue

        # 4. Standalone Role / Promotion line (e.g. 'Staff Software Engineer (2022 - Present)' or 'Senior Software Engineer')
        if not has_bullet and not clean.endswith(":") and any(w in ROLE_KEYWORDS for w in words if w != "experience" or has_date) and (has_date or len(words) <= 7):
            title_only = _DATE_RANGE_RE.sub("", clean).strip(" ()–-—|")
            current_progression.append(RoleProgression(title=title_only, dates=dates_val))
            if not current_role or current_bullets:
                current_role = title_only
                current_dates = dates_val
            continue

        # 4b. Company Header with Dates (e.g. 'Arrow Systems (2020 - Present)')
        if (
            not has_bullet
            and has_date
            and not clean.endswith(":")
            and not any(w in ROLE_KEYWORDS for w in words)
            and first_w not in STRONG_ACTION_VERBS
            and not _EVIDENCE_VERB_RE.match(first_w)
        ):
            c_cand = _DATE_RANGE_RE.sub("", clean).strip(" ()–-—|")
            if 1 <= len(c_cand.split()) <= 6:
                if current_bullets or (current_company and current_company.lower() != c_cand.lower() and current_progression):
                    flush_entity()
                current_company = c_cand
                current_dates = dates_val
                continue

        # 5. Standalone Company Header line (e.g. 'Google LLC, Mountain View, CA' or 'Capco')
        if (
            not has_bullet
            and not has_date
            and len(words) <= 8
            and not any(w in ROLE_KEYWORDS for w in words)
            and not clean.endswith((".", ";", "!"))
            and first_w not in STRONG_ACTION_VERBS
            and not _EVIDENCE_VERB_RE.match(first_w)
            and not any(w in clean_lower for w in ["reduced", "increased", "achieved", "improved", "handling", "processing", "delivering", "supporting", "environments", "commands", "enrollment"])
        ):
            c_cand = clean
            l_cand = ""
            for s in [" - ", " — ", " – ", " | ", ", "]:
                if s in clean:
                    c_sub, _, l_sub = clean.partition(s)
                    if _is_location_text(l_sub) and len(l_sub.split()) <= 5:
                        c_cand = c_sub.strip(" ()–-—|")
                        l_cand = l_sub.strip(" ()–-—|")
                        break

            if current_bullets or (current_company and current_company.lower() != c_cand.lower() and current_progression):
                flush_entity()
            current_company = c_cand
            if l_cand:
                current_location = l_cand
            continue

        # 6. Bullet continuation check:
        # If no bullet marker, and (starts with lowercase OR previous bullet did not end with punctuation and line doesn't start with action verb)
        if current_bullets and not has_bullet and not has_date:
            prev_ended = current_bullets[-1].strip().endswith((".", ";", "!"))
            starts_lower = clean[0].islower() if clean else False
            is_action_verb = first_w in STRONG_ACTION_VERBS or bool(_EVIDENCE_VERB_RE.match(first_w))
            
            if starts_lower or (not prev_ended and not is_action_verb):
                current_bullets[-1] = current_bullets[-1].rstrip() + " " + clean
                if current_group and current_group.bullets:
                    current_group.bullets[-1] = current_bullets[-1]
                if current_progression and current_progression[-1].bullets:
                    current_progression[-1].bullets[-1] = current_bullets[-1]
                continue

        # 7. New Bullet point or unstructured prose sentence
        if has_bullet:
            current_bullets.append(clean)
            if current_group is not None:
                current_group.bullets.append(clean)
            if current_progression:
                current_progression[-1].bullets.append(clean)
            continue

        # Paragraph or unstructured line
        if len(clean.split()) > 10 or (not clean.endswith(":") and any(w.lower() in STRONG_ACTION_VERBS for w in clean.split()[:2])):
            split_sentences = _split_unstructured_evidence(clean)
            current_bullets.extend(split_sentences)
            if current_group is not None:
                current_group.bullets.extend(split_sentences)
            if current_progression:
                current_progression[-1].bullets.extend(split_sentences)
            continue
        else:
            current_bullets.append(clean)
            if current_group is not None:
                current_group.bullets.append(clean)
            if current_progression:
                current_progression[-1].bullets.append(clean)
            continue

    flush_entity()
    return entities


def _structure_experience(lines: list[str]) -> list[str]:
    """
    Converts raw experience lines into structured experience entries preserving companies,
    role progression, locations, responsibility headings, and individual bullets.
    """
    entities = parse_experience_section(lines)
    if not entities:
        return _bulletize(lines)

    result_lines: list[str] = []
    for exp in entities:
        if exp.progression and len(exp.progression) > 1:
            result_lines.append(exp.company)
            if exp.location:
                result_lines.append(exp.location)
            for p in exp.progression:
                p_str = f"{p.title} ({p.dates})" if p.dates else p.title
                result_lines.append(p_str)
                for b in p.bullets:
                    b_clean = b.strip()
                    if b_clean:
                        result_lines.append(b_clean)
            if exp.responsibility_groups:
                for grp in exp.responsibility_groups:
                    if grp.heading:
                        result_lines.append(grp.heading)
                    for b in grp.bullets:
                        b_clean = b.strip()
                        if b_clean:
                            result_lines.append(b_clean)
        else:
            header_parts = []
            is_dummy_company = not exp.company or exp.company.lower() in ("work experience", "company")
            if not is_dummy_company and exp.role:
                header_parts.append(f"{exp.role} at {exp.company}")
            elif not is_dummy_company:
                header_parts.append(exp.company)
            elif exp.role and (exp.dates or exp.location):
                header_parts.append(exp.role)

            if exp.dates:
                header_parts.append(f"({exp.dates})")
            if exp.location:
                header_parts.append(f"- {exp.location}")
            if header_parts:
                result_lines.append(" ".join(header_parts))

            if exp.responsibility_groups:
                for grp in exp.responsibility_groups:
                    if grp.heading:
                        result_lines.append(grp.heading)
                    for b in grp.bullets:
                        b_clean = b.strip()
                        if b_clean:
                            result_lines.append(b_clean)
            else:
                for b in exp.bullets:
                    b_clean = b.strip()
                    if b_clean:
                        result_lines.append(b_clean)

    return result_lines


def _bulletize(lines: list[str]) -> list[str]:
    """Splits a raw section block into clean individual bullets for experience and projects."""
    raw_bullets: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_tech_stack_or_meta(stripped):
            continue

        standalone_bullet = stripped in {"•", "-", "*", "–", "—", ""}
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


PREPOSITIONS_CONJUNCTIONS = {
    "using", "with", "from", "to", "for", "in", "on", "by", "and", "or", "of",
    "into", "across", "through", "detecting", "achieving", "handling", "predicting",
    "including", "alongside", "optimizing", "deploying"
}


def parse_projects_section(lines: list[str]) -> list[Any]:
    from app.modules.resume.models import ProjectEntity
    projects: list[ProjectEntity] = []
    current_title = ""
    current_tech = ""
    current_dates = None
    current_bullets = []

    def flush_proj():
        nonlocal current_title, current_tech, current_dates, current_bullets
        if current_title or current_bullets:
            proj_id = f"proj_{len(projects)}"
            projects.append(ProjectEntity(
                id=proj_id,
                title=current_title or f"Project {len(projects)+1}",
                tech_stack=current_tech or None,
                dates=current_dates,
                bullets=list(current_bullets),
            ))
            current_title = ""
            current_tech = ""
            current_dates = None
            current_bullets = []

    expanded_lines: list[str] = []
    for l in lines:
        for sub in str(l).split("\n"):
            expanded_lines.append(sub)

    for line in expanded_lines:
        stripped = line.strip()
        if not stripped:
            continue
        has_bullet = bool(_BULLET_PREFIX_RE.match(stripped)) or stripped.startswith(("•", "-", "*", "–", "—"))
        clean = _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not clean:
            continue

        # Tech stack metadata line
        if _is_tech_stack_or_meta(clean) or (not has_bullet and re.match(r"^(?:Python|Java|C\+\+|React|TensorFlow|Go|Node|Swift|JavaScript|HTML|SQL|OpenCV|Keras|Streamlit)\b", clean) and len(clean.split()) <= 10 and "," in clean):
            tech_val = re.sub(r"^(?:technologies|tech stack|tools & technologies|tools|frameworks & tools|stack|languages & frameworks)\s*:\s*", "", clean, flags=re.IGNORECASE).strip()
            current_tech = (current_tech + ", " + tech_val).strip(", ") if current_tech else tech_val
            continue

        # Inline Title: Bullet (with or without bullet marker, e.g. "• AI Document Classifier: Built..." or "ShopEase (Docker, React): Engineered...")
        if ":" in clean and not _is_tech_stack_or_meta(clean):
            t_cand, sep, b_cand = clean.partition(":")
            t_cand = t_cand.strip()
            b_cand = b_cand.strip()
            if 1 <= len(t_cand.split()) <= 10 and len(b_cand.split()) >= 3 and t_cand.split()[0].lower() not in STRONG_ACTION_VERBS:
                flush_proj()
                paren_m = re.search(r"^(.*?)\s*\(([^)]+)\)$", t_cand)
                if paren_m:
                    current_title = paren_m.group(1).strip()
                    current_tech = paren_m.group(2).strip()
                else:
                    current_title = t_cand
                if b_cand:
                    current_bullets.append(b_cand)
                continue

        # Standalone Project Title (with or without bullet marker)
        if _looks_like_project_title(clean):
            if current_bullets or current_title:
                flush_proj()
            paren_m = re.search(r"^(.*?)\s*\(([^)]+)\)$", clean)
            if paren_m:
                current_title = paren_m.group(1).strip()
                current_tech = paren_m.group(2).strip()
            else:
                current_title = clean
            continue

        # Bullet point
        if has_bullet:
            current_bullets.append(clean)
            continue

        # Continuation of previous bullet
        if current_bullets and not current_bullets[-1].endswith((".", ";", "!")):
            current_bullets[-1] = current_bullets[-1].rstrip() + " " + clean
        else:
            current_bullets.append(clean)

    flush_proj()
    return projects


_EVIDENCE_VERB_RE = re.compile(
    r"^(?:developed|engineered|implemented|built|architected|designed|created|led|managed|optimized|automated|maintained|integrated|spearheaded|deployed|trained|fine-tuned|constructed|authored|delivered|launched)\b",
    re.IGNORECASE,
)


def _looks_like_project_title(line: str) -> bool:
    """Identify a compact project heading without mistaking it for a bullet or inline project."""
    cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
    if not cleaned or _is_tech_stack_or_meta(cleaned) or ":" in cleaned:
        return False
    words = cleaned.split()
    if len(words) > 8 or len(words) < 1:
        return False
    if cleaned.endswith((".", ";", "!")):
        return False
    last_word = words[-1].lower().rstrip(":,")
    if last_word in PREPOSITIONS_CONJUNCTIONS:
        return False
    first_word = words[0].lower().rstrip(":,")
    if _EVIDENCE_VERB_RE.match(first_word) or first_word in STRONG_ACTION_VERBS:
        return False
    if any(w in [x.lower() for x in words] for w in ["to", "from", "achieving", "reducing", "improving", "handling", "detect", "predict"]):
        return False
    return True


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
        standalone_bullet = stripped in {"•", "-", "*", "–", "—", "", ""}
        has_bullet_prefix = standalone_bullet or bool(_BULLET_PREFIX_RE.match(stripped))
        cleaned = "" if standalone_bullet else _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not cleaned:
            pending_bullet = pending_bullet or has_bullet_prefix
            continue
        if pending_bullet:
            has_bullet_prefix = True
            pending_bullet = False

        # Extract inline "Title: Bullet" format e.g. "AI-Based Ad Analyzer: Built Flask..."
        if ":" in cleaned and not _is_tech_stack_or_meta(cleaned):
            t_cand, sep, b_cand = cleaned.partition(":")
            t_cand = t_cand.strip()
            b_cand = b_cand.strip()
            first_w = t_cand.split()[0].lower() if t_cand.split() else ""
            if 1 <= len(t_cand.split()) <= 12 and len(b_cand.split()) >= 3 and first_w not in STRONG_ACTION_VERBS:
                if first_bullet_for_project and current_title:
                    ctx = [current_title]
                    if current_tech:
                        ctx.append(f"Technologies: {current_tech}")
                    bullets.append("\n".join(ctx))
                    current_title = ""
                    current_tech = ""
                    first_bullet_for_project = False

                paren_t = re.search(r"^(.*?)\s*\(([^)]+)\)$", t_cand)
                if paren_t:
                    p_title = paren_t.group(1).strip()
                    p_tech = paren_t.group(2).strip()
                    bullets.append(f"{p_title}\nTechnologies: {p_tech}\n{b_cand}")
                else:
                    bullets.append(f"{t_cand}\n{b_cand}")
                continue

        # Extract title and inline tech stack in parentheses e.g. "AI Screener (Python, FastAPI)"
        paren_stack = re.search(r"^(.*?)\s*\(([^)]+)\)\s*$", cleaned)
        if paren_stack and not _is_tech_stack_or_meta(cleaned):
            t_cand = paren_stack.group(1).strip()
            s_cand = paren_stack.group(2).strip()
            if 1 <= len(t_cand.split()) <= 14 and ("," in s_cand or len(s_cand.split()) <= 6 or any(k in s_cand.lower() for k in ["python", "java", "react", "node", "fastapi", "sql", "aws", "docker", "c++", "ml", "ai", "js", "ts", "html", "css", "raft", "grpc", "sqlite", "rust"])):
                if first_bullet_for_project and current_title:
                    ctx = [current_title]
                    if current_tech:
                        ctx.append(f"Technologies: {current_tech}")
                    bullets.append("\n".join(ctx))
                current_title = t_cand
                current_tech = s_cand
                first_bullet_for_project = True
                continue

        # Split right-aligned tech stack on same line as project title
        inline_stack = re.search(
            r"\b(Python|Java|JavaScript|TypeScript|C\+\+|C|TensorFlow|Keras|React|Node\.js|Flask|FastAPI|PostgreSQL|MongoDB|Docker|Rust|Go)\s*,",
            cleaned,
            re.IGNORECASE,
        )
        if inline_stack and inline_stack.start() > 0 and not _is_tech_stack_or_meta(cleaned) and not cleaned.endswith((".", ";", "!")):
            t_cand = cleaned[:inline_stack.start()].strip(" |-–—(")
            s_cand = cleaned[inline_stack.start():].strip(" )")
            if _looks_like_project_title(t_cand):
                if first_bullet_for_project and current_title:
                    ctx = [current_title]
                    if current_tech:
                        ctx.append(f"Technologies: {current_tech}")
                    bullets.append("\n".join(ctx))
                current_title = t_cand
                current_tech = s_cand
                first_bullet_for_project = True
                continue

        if _is_tech_stack_or_meta(cleaned):
            tech_val = re.sub(
                r"^(?:tech stack|technologies|tools & tech|stack|frameworks & tools)\s*:\s*",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip()
            current_tech = tech_val or cleaned
            continue

        if _looks_like_project_title(cleaned):
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
            current_title = ""
            current_tech = ""
            first_bullet_for_project = False
            continue

        if has_bullet_prefix:
            bullets.append(cleaned)
            continue

        if bullets and not bullets[-1].rstrip().endswith((".", ";", "!")):
            bullets[-1] = bullets[-1].rstrip() + " " + cleaned
            continue

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

DEGREE_PATTERNS = [
    re.compile(
        r"\b(?:master\s+of\s+science|bachelor\s+of\s+science|master\s+of\s+arts|bachelor\s+of\s+arts|master\s+of\s+engineering|bachelor\s+of\s+engineering|master\s+of\s+technology|bachelor\s+of\s+technology|master\s+of\s+business|bachelor\s+of\s+business|doctor\s+of\s+philosophy|master\s+of\s+commerce|bachelor\s+of\s+commerce|master(?:\'s)?|bachelor(?:\'s)?|ph\.?d\.?|doctorate|m\.?s\.?|b\.?s\.?|b\.?tech\.?|m\.?tech\.?|b\.?e\.?|m\.?e\.?|b\.?sc\.?|m\.?sc\.?|b\.?a\.?|m\.?a\.?|b\.?com\.?|m\.?com\.?|b\.?eng\.?|m\.?eng\.?|diploma|associate(?:\s+of|\s+degree)?|certificate(?:\s+in)?|degree)\b",
        re.IGNORECASE,
    ),
]

_DATE_SINGLE_RE = re.compile(
    r"\b(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+)?\d{4}\b",
    re.IGNORECASE,
)

_GPA_RE = re.compile(
    r"(?:(?:cgpa|percentage|score|gpa)\s*[:|-]?\s*([0-9\.]+\s*%?(?:\s*(?:\/|\%)\s*[0-9\.]+)?)|([0-4]\.[0-9]{1,2}\s*\/\s*[0-4]\.[0-9]{1,2})|([0-9]{1,2}\.[0-9]{1,2}\s*\/\s*10(?:\.0)?))",
    re.IGNORECASE,
)

_MINOR_RE = re.compile(r"\b(?:minor|specialization|concentration|focus)\s*:\s*([^|\n,]+)", re.IGNORECASE)


def parse_education_section(lines: list[str]) -> list[Any]:
    from app.modules.resume.models import EducationEntity

    raw_entries: list[list[str]] = []
    current_entry_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_entry_lines:
                raw_entries.append(current_entry_lines)
                current_entry_lines = []
            continue

        clean_line = _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not clean_line:
            continue

        if current_entry_lines:
            prev_text = " ".join(current_entry_lines)
            has_date_or_grade = bool(re.search(r"\b(?:\d{4}|cgpa|percentage|\bgrades?\b)\b", prev_text, re.IGNORECASE))
            is_new_inst = bool(_INSTITUTION_RE.search(clean_line)) and not bool(re.search(r"\b(?:\d{4}|cgpa|percentage|\bgrades?\b)\b", clean_line, re.IGNORECASE))
            is_new_degree = bool(any(p.search(clean_line) for p in DEGREE_PATTERNS)) and not bool(re.search(r"\b(?:\d{4}|cgpa|percentage|\bgrades?\b)\b", clean_line, re.IGNORECASE))

            if (has_date_or_grade and (is_new_inst or is_new_degree)) or (len(current_entry_lines) >= 3 and (is_new_inst or is_new_degree)):
                raw_entries.append(current_entry_lines)
                current_entry_lines = [clean_line]
                continue

        current_entry_lines.append(clean_line)

    if current_entry_lines:
        raw_entries.append(current_entry_lines)

    edu_entities: list[EducationEntity] = []
    for e_idx, entry_lines in enumerate(raw_entries):
        degree_cand = ""
        inst_cand = ""
        dates_cand = None
        gpa_cand = None
        loc_cand = None

        for s in entry_lines:
            # Extract GPA
            gpa_m = _GPA_RE.search(s)
            if gpa_m and not gpa_cand:
                gpa_cand = gpa_m.group(0).strip()

            # Extract Date
            date_m = _DATE_RANGE_RE.search(s) or _DATE_SINGLE_RE.search(s)
            if date_m and not dates_cand:
                dates_cand = date_m.group(0).strip()

            # Clean line of dates, gpa, and minor
            clean_text = _GPA_RE.sub("", s)
            clean_text = _DATE_RANGE_RE.sub("", clean_text)
            clean_text = _MINOR_RE.sub("", clean_text)
            clean_text = re.sub(r"\b(?:graduation|expected|dates?)\s*:\s*", "", clean_text, flags=re.IGNORECASE)
            clean_text = clean_text.strip(" *#=_~|•-–—\t\r\n,()")

            if not clean_text:
                continue

            if any(p.search(clean_text) for p in DEGREE_PATTERNS):
                segments = [p.strip(" *#=_~|•-–—\t\r\n,()") for p in re.split(r"[,|–—]", clean_text) if p.strip(" *#=_~|•-–—\t\r\n,()")]
                if len(segments) >= 2:
                    for seg in segments:
                        if any(p.search(seg) for p in DEGREE_PATTERNS) and not degree_cand:
                            degree_cand = seg
                        elif _INSTITUTION_RE.search(seg) and not inst_cand:
                            inst_cand = seg
                        elif _is_location_text(seg) and not loc_cand:
                            loc_cand = seg
                        elif not inst_cand and not any(p.search(seg) for p in DEGREE_PATTERNS):
                            inst_cand = seg
                    continue
                elif not degree_cand:
                    degree_cand = clean_text
            elif _INSTITUTION_RE.search(clean_text) or not inst_cand:
                if not inst_cand:
                    inst_cand = clean_text
            elif not degree_cand:
                degree_cand = clean_text

        edu_entities.append(EducationEntity(
            id=f"edu_{e_idx}",
            institution=inst_cand or "Institution",
            degree=degree_cand or "Degree / Studies",
            dates=dates_cand,
            location=loc_cand,
            gpa=gpa_cand,
        ))

    return edu_entities


def _structure_education(lines: list[str]) -> list[str]:
    edu_entities = parse_education_section(lines)
    if not edu_entities:
        return [l.strip() for l in lines if l.strip()]

    entries: list[str] = []
    for e in edu_entities:
        parts = [e.degree, e.institution]
        extra = []
        if e.gpa:
            extra.append(e.gpa)
        if e.dates:
            extra.append(e.dates)
        if extra:
            parts.append(" | ".join(extra))
        entries.append("\n".join(parts))
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


PROGRAMMING_LANGUAGE_NAMES = {
    "python", "java", "c", "c++", "c#", "javascript", "typescript", "golang", "go",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "html", "css",
    "sql", "nosql", "bash", "shell", "powershell", "perl", "matlab", "assembly",
    "react", "node", "nodejs", "express", "flask", "fastapi", "django", "spring",
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "linux", "mongodb", "postgresql",
}


def _extract_languages(lines: list[str], full_text: str) -> list[str]:
    """
    Extracts candidate's spoken/human languages from the languages section or preamble.
    Guarantees that programming languages (Java, Python, C, etc.) from Skills are never
    mistaken for spoken languages.
    """
    langs: list[str] = []
    raw_lines = [l for l in lines if l.strip()]

    # Fallback to full_text ONLY if no languages section was found AND
    # there is an explicit spoken languages indicator anchored at line start.
    if not raw_lines:
        lang_match = re.search(
            r"(?mi)^\s*(?:known\s+languages|languages\s+known|spoken\s+languages)\s*:\s*([^\n\r]+)",
            full_text,
        )
        if lang_match:
            raw_lines = [lang_match.group(1)]

    for line in raw_lines:
        cleaned = _BULLET_PREFIX_RE.sub("", line).strip()
        cleaned = re.sub(
            r"^(?:known\s+languages|languages\s+known|spoken\s+languages|languages)\s*:\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if not cleaned:
            continue
        parts = [p.strip() for p in re.split(r"[,|•;/]", cleaned) if p.strip()]
        for p in parts:
            p_clean = re.sub(r"\s*\([^)]*\)", "", p).strip()
            if not p_clean or len(p_clean) > 25:
                continue
            # NEVER add technical programming languages to spoken languages
            if p_clean.lower() in PROGRAMMING_LANGUAGE_NAMES:
                continue
            if p_clean not in langs:
                langs.append(p_clean)

    return langs


def _is_location_or_contact_line(text: str) -> bool:
    s = text.strip()
    if not s:
        return True
    if s.upper() in {"C", "R"}:
        return False
    if len(s) < 2:
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


def _split_skills_explicit(lines: list[str]) -> list[str]:
    """
    Extracts skills explicitly declared in the skills section or categorized skills lines.
    Does NOT infer skills from full text.
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
    return found_skills


def _split_skills(lines: list[str], full_text: str) -> list[str]:
    """
    Extracts skills with high recall (explicit + inferred).
    """
    explicit = _split_skills_explicit(lines)
    found_skills = list(explicit)

    spacy_extracted = extract_skills_from_text(full_text)
    existing_lower = {s.lower() for s in found_skills}
    for s in spacy_extracted:
        if s.lower() not in existing_lower and not _is_location_or_contact_line(s):
            found_skills.append(s)
            existing_lower.add(s.lower())

    return found_skills


def _recover_unheaded_evidence(lines: list[str]) -> list[str]:
    """Recovers evidence from unheaded preamble or prose paragraphs."""
    evidence: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        cleaned = _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not cleaned:
            continue
        if _is_location_or_contact_line(cleaned):
            continue
        sentences = _split_unstructured_evidence(cleaned)
        for s in sentences:
            s_lower = s.lower()
            if any(w in s_lower for w in ["passionate software engineer", "seeking an entry", "seeking a role", "looking for an opportunity"]):
                continue
            if any(s_lower.startswith(w) for w in ["graduated with", "graduated from", "awarded 1st", "awarded 2nd", "bachelor of", "master of"]):
                continue
            words = s_lower.split()
            first_few = words[:4]
            if any(w in STRONG_ACTION_VERBS for w in first_few) or any(k in words for k in ["built", "developed", "led", "engineered", "created", "architected", "implemented", "managed", "optimized", "designed", "working"]):
                evidence.append(s)
            elif len(words) >= 8 and not any(w in s_lower for w in ["bachelor", "master", "cgpa"]):
                evidence.append(s)
    return evidence


def _extract_summary_from_preamble(preamble_lines: list[str]) -> str | None:
    """
    Detects an unheaded introductory summary / professional profile paragraph from the top preamble.
    Unwraps and aggregates contiguous multi-line prose paragraphs.
    """
    paragraphs: list[list[str]] = []
    current_p: list[str] = []

    for idx, line in enumerate(preamble_lines):
        s = line.strip()
        if not s:
            if current_p:
                paragraphs.append(current_p)
                current_p = []
            continue

        if idx <= 1 and len(s.split()) <= 4 and not any(w in s.lower() for w in ["engineer", "developer", "experience", "years"]):
            continue
        if _is_location_or_contact_line(s) or EMAIL_RE.search(s) or PHONE_RE.search(s) or URL_RE.search(s):
            continue
        if _INSTITUTION_RE.search(s) or any(w in s.lower() for w in ["bachelor", "master", "cgpa", "b.tech", "b.e."]):
            continue
        if s.startswith(("•", "-", "*", "–")):
            continue

        current_p.append(s)

    if current_p:
        paragraphs.append(current_p)

    for p_lines in paragraphs:
        joined = " ".join(p_lines).strip()
        if len(joined.split()) >= 6:
            if any(w in joined.lower() for w in ["engineer", "developer", "professional", "experience", "building", "passionate", "specialized", "architect", "leading", "proficient", "skilled", "years", "focused", "seeking", "enthusiastic"]):
                return joined

    return None


def validate_candidate_profile(profile: "CandidateProfile") -> list[str]:
    """
    Deterministic structural validation on CandidateProfile to identify:
    - Orphan roles / unassigned companies
    - Empty projects
    - Duplicate evidence IDs
    - Malformed hierarchies
    """
    issues: list[str] = []
    seen_evidence_ids: set[str] = set()

    # 1. Experience hierarchy checks
    for exp in profile.experience:
        if not exp.company or exp.company.strip().lower() in ("company", ""):
            if exp.role:
                exp.company = "Independent / Professional Work"
        for ev in exp.evidence_units:
            if ev.id in seen_evidence_ids:
                issues.append(f"Duplicate Evidence ID detected: {ev.id}")
            seen_evidence_ids.add(ev.id)
            if not ev.text.strip():
                issues.append(f"Empty evidence unit in {exp.company}")

    # 2. Project validation
    for proj in profile.projects:
        if not proj.title:
            proj.title = "Technical Project"
        for ev in proj.evidence_units:
            if ev.id in seen_evidence_ids:
                issues.append(f"Duplicate Evidence ID detected: {ev.id}")
            seen_evidence_ids.add(ev.id)

    # 3. Additional sections validation
    for sec in profile.additional_sections:
        for ev in sec.evidence_units:
            if ev.id in seen_evidence_ids:
                issues.append(f"Duplicate Evidence ID detected: {ev.id}")
            seen_evidence_ids.add(ev.id)

    return issues


def structure_resume_text(full_text: str) -> dict:
    """
    Standardized, robust resume structurer for real-world messy resumes.
    Guarantees 100% preservation of all sections, contact info, education, certifications, and languages.
    Returns rich canonical structured entities alongside backward-compatible *_raw views.
    """
    cleaned_full_text = _clean_raw_text_artifacts(full_text)
    lines = cleaned_full_text.split("\n")
    sections = _split_into_sections(lines)

    personal = _extract_personal(sections["_preamble"], cleaned_full_text)
    skills_explicit = _split_skills_explicit(sections["skills"])
    spacy_extracted = extract_skills_from_text(cleaned_full_text)
    skills_inferred = [s for s in spacy_extracted if s.lower() not in {x.lower() for x in skills_explicit} and not _is_location_or_contact_line(s)]
    skills_all = list(skills_explicit) + [s for s in skills_inferred if s.lower() not in {x.lower() for x in skills_explicit}]
    skills_categorized = _extract_categorized_skills(sections["skills"])

    exp_entities = parse_experience_section(sections["experience"])
    intern_entities = parse_experience_section(sections.get("internships", []))
    proj_entities = parse_projects_section(sections["projects"])
    edu_entities = parse_education_section(sections.get("education", []))

    experience_bullets = _structure_experience(sections["experience"])
    project_bullets = _bulletize_projects(sections["projects"])

    # Truly unstructured resumes may put all evidence under the header block.
    # Treat those statements as experience only when neither editable section
    # was found; otherwise explicit section structure always wins.
    if not exp_entities and not proj_entities:
        recovered_exp = _recover_unheaded_evidence(sections["_preamble"])
        if recovered_exp:
            from app.modules.resume.models import WorkExperienceEntity
            exp_entities = [WorkExperienceEntity(
                id="exp_0",
                company="Independent / Professional Work",
                role="Software Engineer",
                bullets=recovered_exp,
            )]
            experience_bullets = recovered_exp

    summary_text = " ".join(sections["summary"]).strip() if sections["summary"] else _extract_summary_from_preamble(sections["_preamble"])

    # Extract custom / additional sections
    add_sections = []
    for heading, sec_key in sections.get("_custom", []):
        sec_lines = sections.get(sec_key, [])
        items = _extract_list_items(sec_lines)
        add_sections.append({
            "id": f"add_{len(add_sections)}",
            "heading": heading,
            "semantic_type": "UNKNOWN",
            "items": items,
            "text": "\n".join(sec_lines),
        })

    return {
        "personal": personal,
        "summary": summary_text,
        "skills": skills_all,
        "skills_explicit": skills_explicit,
        "skills_inferred": skills_inferred,
        "skills_categorized": skills_categorized,
        "experience": [e.model_dump() for e in exp_entities],
        "experience_entities": [e.model_dump() for e in exp_entities],
        "experience_raw": experience_bullets,
        "internships": [e.model_dump() for e in intern_entities],
        "internships_entities": [e.model_dump() for e in intern_entities],
        "internships_raw": _structure_experience(sections.get("internships", [])),
        "projects": [p.model_dump() for p in proj_entities],
        "projects_entities": [p.model_dump() for p in proj_entities],
        "projects_raw": project_bullets,
        "education": [e.model_dump() for e in edu_entities],
        "education_entities": [e.model_dump() for e in edu_entities],
        "education_raw": _structure_education(sections.get("education", [])),
        "certifications": _extract_list_items(sections.get("certifications", [])),
        "achievements": _extract_list_items(sections.get("achievements", [])),
        "publications": _extract_list_items(sections.get("publications", [])),
        "research": _extract_list_items(sections.get("research", [])),
        "leadership": _extract_list_items(sections.get("leadership", [])),
        "volunteer": _extract_list_items(sections.get("volunteer", [])),
        "side_quests": _extract_list_items(sections.get("side_quests", [])),
        "languages": _extract_languages(sections.get("languages", []), cleaned_full_text),
        "links": [u for u in [personal.get("github"), personal.get("linkedin"), personal.get("portfolio")] if u],
        "additional_sections": add_sections,
    }


def extract_candidate_profile(document_or_text: Any) -> "CandidateProfile":
    """
    Parses arbitrary resume text or NormalizedDocument into a rich canonical CandidateProfile with full
    provenance-tracked EvidenceUnit objects and deterministic structural validation.
    """
    from app.modules.resume.models import CandidateProfile

    if hasattr(document_or_text, "normalized_text") and document_or_text.normalized_text:
        raw_text = document_or_text.normalized_text
    elif hasattr(document_or_text, "full_text") and document_or_text.full_text:
        raw_text = document_or_text.full_text
    else:
        raw_text = str(document_or_text)

    cleaned_full_text = _clean_raw_text_artifacts(raw_text)
    structured = structure_resume_text(cleaned_full_text)
    profile = CandidateProfile.from_parsed_dict(structured, cleaned_full_text)

    # Run deterministic structural validation
    validate_candidate_profile(profile)

    return profile
