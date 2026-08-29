import io
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.modules.resume.parsing.structurer import SECTION_PATTERNS


def _sanitize_text(text: str) -> str:
    """Normalizes Unicode dashes, spaces, and quotes to standard ASCII for perfect ATS parser extraction."""
    if not text:
        return ""
    replacements = {
        "\u2013": "-",  # en-dash
        "\u2014": "-",  # em-dash
        "\u2012": "-",
        "\u2212": "-",  # minus sign
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u00a0": " ",  # non-breaking space
        "\ufffd": "-",  # replacement char
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def render_text_from_structured(parsed_data: dict) -> str:
    """
    Renders clean, structured markdown/plain-text directly from a parsed dictionary.
    Zero regex text-splicing — pure deterministic formatting.
    """
    if not parsed_data:
        return ""

    personal = parsed_data.get("personal", {}) or parsed_data.get("personal_info", {}) or {}
    name = personal.get("name") or personal.get("full_name") or "Candidate"
    contacts = []
    if personal.get("location"):
        contacts.append(personal["location"])
    elif personal.get("city") or personal.get("address"):
        loc = ", ".join(filter(None, [personal.get("city"), personal.get("address")]))
        if loc:
            contacts.append(loc)
    if personal.get("email"):
        contacts.append(personal["email"])
    if personal.get("phone"):
        contacts.append(personal["phone"])
    if personal.get("linkedin"):
        contacts.append(personal["linkedin"])
    if personal.get("github"):
        contacts.append(personal["github"])
    if personal.get("portfolio"):
        contacts.append(personal["portfolio"])

    lines = [name]
    if contacts:
        lines.append(" • ".join(contacts))
    lines.append("")

    # Summary
    summary = parsed_data.get("summary") or parsed_data.get("objective")
    if summary and str(summary).strip():
        lines.append("PROFESSIONAL SUMMARY")
        lines.append(str(summary).strip())
        lines.append("")

    # Skills
    skills_cat = parsed_data.get("skills_categorized", [])
    skills = parsed_data.get("skills", [])
    if skills_cat and isinstance(skills_cat, list):
        lines.append("TECHNICAL SKILLS")
        for sc in skills_cat:
            lines.append(str(sc).strip())
        lines.append("")
    elif isinstance(skills, dict):
        lines.append("TECHNICAL SKILLS")
        for cat, val in skills.items():
            val_str = ", ".join(str(v) for v in val) if isinstance(val, list) else str(val)
            lines.append(f"{cat}: {val_str}")
        lines.append("")
    elif skills:
        lines.append("TECHNICAL SKILLS")
        if isinstance(skills, list):
            # Check if list already has category lines with colons
            has_categories = any(":" in str(s) and len(str(s).split(":")[0].split()) <= 6 for s in skills)
            if has_categories:
                for s in skills:
                    lines.append(str(s).strip())
            else:
                lines.append(", ".join(str(s) for s in skills if s))
        else:
            lines.append(str(skills))
        lines.append("")

    # Experience
    exp = parsed_data.get("experience_raw", []) or parsed_data.get("experience", []) or parsed_data.get("work_experience", [])
    if exp:
        lines.append("PROFESSIONAL EXPERIENCE")
        for b in exp:
            if isinstance(b, dict):
                comp = b.get("company", "")
                role = b.get("role", "") or b.get("title", "")
                dates = b.get("dates", "")
                title_line = f"{role} - {comp}" if role and comp else (role or comp)
                if dates:
                    title_line += f" ({dates})"
                if title_line:
                    lines.append(title_line)
                tech = b.get("tech_stack") or b.get("technologies")
                if tech:
                    lines.append(f"Tech Stack: {tech}")
                for bullet in b.get("bullets", []):
                    prefix = "" if str(bullet).strip().startswith(("•", "-", "*")) else "• "
                    lines.append(f"{prefix}{str(bullet).strip()}")
            else:
                b_str = str(b).strip()
                if b_str:
                    prefix = "" if b_str.startswith(("•", "-", "*")) else "• "
                    lines.append(f"{prefix}{b_str}")
        lines.append("")

    # Projects
    # Projects
    proj = parsed_data.get("projects_raw", []) or parsed_data.get("projects", [])
    if proj:
        lines.append("TECHNICAL PROJECTS")
        for b in proj:
            if isinstance(b, dict):
                title = b.get("title") or b.get("name", "")
                dates = b.get("dates", "")
                title_line = title + (f" ({dates})" if dates else "")
                if title_line:
                    lines.append(title_line)
                tech = b.get("tech_stack") or b.get("technologies")
                if tech:
                    lines.append(f"Technologies: {tech}")
                for bullet in b.get("bullets", []):
                    prefix = "" if str(bullet).strip().startswith(("•", "-", "*")) else "• "
                    lines.append(f"{prefix}{str(bullet).strip()}")
            else:
                b_str = str(b).strip()
                if not b_str:
                    continue
                sub_lines = [l.strip() for l in b_str.split("\n") if l.strip()]
                for sub_idx, sub_clean in enumerate(sub_lines):
                    if _is_tech_stack_line(sub_clean):
                        lines.append(sub_clean)
                    elif _clean_title_and_date(sub_clean) and sub_idx == 0:
                        t_str, d_str = _clean_title_and_date(sub_clean)
                        lines.append(f"{t_str} ({d_str})" if d_str else t_str)
                    elif _is_project_title_line(sub_clean):
                        lines.append(sub_clean)
                    else:
                        prefix = "" if sub_clean.startswith(("•", "-", "*")) else "• "
                        lines.append(f"{prefix}{sub_clean}")
        lines.append("")

    # Education
    edu = parsed_data.get("education_raw", []) or parsed_data.get("education", [])
    if edu:
        lines.append("EDUCATION")
        for e in edu:
            if isinstance(e, dict):
                inst = e.get("institution") or e.get("school") or ""
                deg = e.get("degree") or ""
                gpa = e.get("cgpa") or e.get("percentage") or e.get("gpa") or ""
                dates = e.get("dates") or e.get("year") or ""
                loc = e.get("location") or ""
                if inst:
                    lines.append(inst + (f", {loc}" if loc else ""))
                deg_gpa = deg + (f" | {gpa}" if gpa else "")
                if dates:
                    deg_gpa += f" ({dates})"
                if deg_gpa:
                    lines.append(deg_gpa)
                lines.append("")
            else:
                e_str = str(e).strip()
                if e_str:
                    lines.append(e_str)
                    lines.append("")
        if lines and lines[-1] != "":
            lines.append("")

    # Certifications
    certs = parsed_data.get("certifications", []) or parsed_data.get("certifications_raw", []) or parsed_data.get("certificates", [])
    if certs:
        lines.append("CERTIFICATIONS")
        for c in certs:
            c_str = str(c).strip()
            if c_str:
                prefix = "" if c_str.startswith(("•", "-", "*")) else "• "
                lines.append(f"{prefix}{c_str}")
        lines.append("")

    # Achievements
    ach = parsed_data.get("achievements", []) or parsed_data.get("achievements_raw", []) or parsed_data.get("awards", [])
    if ach:
        lines.append("ACHIEVEMENTS")
        for a in ach:
            a_str = str(a).strip()
            if a_str:
                prefix = "" if a_str.startswith(("•", "-", "*")) else "• "
                lines.append(f"{prefix}{a_str}")
        lines.append("")

    # Languages
    langs = parsed_data.get("languages", []) or parsed_data.get("languages_raw", []) or parsed_data.get("languages_known", [])
    if langs:
        lines.append("LANGUAGES")
        if isinstance(langs, list):
            lines.append(", ".join(str(l) for l in langs if l))
        else:
            lines.append(str(langs))
        lines.append("")

    return "\n".join(lines).strip()


INK_900 = "#111827"
INK_700 = "#374151"
INK_500 = "#6b7280"
SIGNAL_600 = "#0d766e"
CLASSIC_ACCENT = "#111827"
TECH_ACCENT = "#1e3a8a"

# Strict bullet prefix regex: matches standard bullet glyphs and numbered lists
# NEVER matches degree abbreviations like 'B.E', 'B.Tech', 'M.Tech', 'B.Sc', 'M.S.'
_BULLET_PREFIX_RE = re.compile(
    r"^(?:[•\-\*\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u27A4\u2714\u2713\u279C\u2192\u25BA\u25B6\u25C6\u25C7\u25CF\u25CB\u2718\u2717\u2705\u27A2\u2794\u2714]|\d{1,2}[\.\)]|\([a-zA-Z0-9]+\)|[a-zA-Z]\))\s+",
    re.UNICODE,
)

_DATE_PATTERN_RE = re.compile(
    r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}(?:\s*[-–—to]+\s*(?:Present|Current|\d{4}|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}))?)\b",
    re.IGNORECASE,
)


def _is_section_header(line: str) -> bool:
    """Accurately identifies section headers including markdown ##, **, underlines, and colons."""
    normalized = re.sub(r"^[#\-=*~_ \t]+|[#\-=*~_:\t ]+$", "", line.strip())
    if not normalized or len(normalized) > 50:
        return False
    return any(re.match(pattern, normalized, re.IGNORECASE) for pattern in SECTION_PATTERNS.values())


def _looks_like_contact_line(line: str) -> bool:
    return bool(re.search(r"@|\b\+?\d{1,3}[-.\s]?\d{10}\b|linkedin\.com|github\.com|portfolio|https?://", line, re.IGNORECASE))


def _split_name_contact_body(resume_text: str) -> tuple[str, list[str], list[str]]:
    """Returns (name, contact_lines, remaining_lines)."""
    lines = [l for l in resume_text.split("\n")]
    non_empty = [(i, l) for i, l in enumerate(lines) if l.strip()]
    if not non_empty:
        return "", [], []

    name_idx, name = non_empty[0]
    # Clean leading markdown # from name if present
    name = re.sub(r"^[#\s*]+", "", name).strip()
    contact_lines: list[str] = []
    body_start_idx = name_idx + 1

    for i in range(name_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if _is_section_header(stripped):
            body_start_idx = i
            break
        if _looks_like_contact_line(stripped) or ("|" in stripped or "•" in stripped or "·" in stripped):
            contact_lines.append(stripped)
            body_start_idx = i + 1
        elif len(contact_lines) == 0 and len(stripped.split()) <= 5 and not _is_section_header(stripped):
            # Might be location line e.g. "Davangere, Karnataka"
            contact_lines.append(stripped)
            body_start_idx = i + 1
        else:
            body_start_idx = i
            break

    return name.strip(), contact_lines, lines[body_start_idx:]


def _clean_title_and_date(line: str) -> tuple[str, str] | None:
    """Extracts clean (title_or_institution, right_aligned_date) if line contains a date span."""
    if line.startswith("•") or line.startswith("-") or line.startswith("*"):
        return None

    date_match = re.search(
        r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}(?:\s*[-–—to]+\s*(?:Present|Current|\d{4}|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}))?)\b\)?\s*$",
        line,
        re.IGNORECASE,
    )
    if not date_match:
        return None

    date_str = date_match.group(1).strip()
    raw_title = line
    raw_title = re.sub(r"\(\s*" + re.escape(date_str) + r"\s*\)", "", raw_title)
    raw_title = raw_title.replace(date_str, "")
    raw_title = re.sub(r"\(\s*\)", "", raw_title)
    raw_title = re.sub(r"\[\s*\]", "", raw_title)
    raw_title = raw_title.strip(" |–-—, \t")

    if not raw_title:
        return "", date_str
    return raw_title, date_str


def _is_skill_category(line: str) -> bool:
    clean = _BULLET_PREFIX_RE.sub("", line).strip()
    return ":" in clean and not clean.startswith("http") and len(clean.split(":")[0].split()) <= 6


def _is_tech_stack_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if lower.startswith("tech stack:") or lower.startswith("technologies:") or lower.startswith("tools & tech:") or lower.startswith("stack:"):
        return True
    if stripped.count("|") >= 2 and len(stripped.split()) <= 25 and not _looks_like_contact_line(stripped):
        return True
    return False


def _is_project_title_line(line: str) -> bool:
    """Recognize a project heading in a structured multi-line project item."""
    clean = _BULLET_PREFIX_RE.sub("", line).strip()
    if not clean or line.strip().startswith(("•", "-", "*")) or _is_tech_stack_line(clean):
        return False
    if _clean_title_and_date(clean) is not None:
        return True
    first_word = clean.split()[0].lower().rstrip(":,")
    from app.modules.resume.parsing.structurer import _EVIDENCE_VERB_RE
    return (
        1 <= len(clean.split()) <= 18
        and not clean.endswith((".", ";", "!"))
        and not _EVIDENCE_VERB_RE.match(first_word)
    )


def _split_into_bullet_points(text: str) -> list[str]:
    """Splits a block of text into distinct bullet points if multiple sentences/bullets exist."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) > 1:
        res = []
        for l in lines:
            res.extend(_split_into_bullet_points(l))
        return res

    raw = lines[0] if lines else text.strip()
    if not raw:
        return []

    cleaned = _BULLET_PREFIX_RE.sub("", raw).strip()
    # Split sentences ending in . or ; that are followed by capital letter
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z][a-z0-9A-Z_]+(?:\s+|$))", cleaned)
    if len(parts) > 1:
        valid_parts = [p.strip() for p in parts if len(p.strip()) > 10]
        if len(valid_parts) == len(parts):
            return valid_parts

    return [cleaned]


def render_pdf_from_structured(
    parsed_data: dict, candidate_name: str = "", template: str = "modern", experience_level: str = "fresher"
) -> bytes:
    """
    Renders an ATS-optimized, beautifully styled PDF directly from a structured resume dictionary.
    No regex text-splicing — pure structured flowable generation.
    """
    template = template.lower() if template else "modern"
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.4 * inch, bottomMargin=0.4 * inch,
        leftMargin=0.45 * inch, rightMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()

    font_family = "Helvetica"
    font_bold = "Helvetica-Bold"
    font_italic = "Helvetica-Oblique"
    accent_color = SIGNAL_600
    name_align = 1  # center

    if template in ("classic", "harvard"):
        font_family = "Times-Roman"
        font_bold = "Times-Bold"
        font_italic = "Times-Italic"
        accent_color = CLASSIC_ACCENT
        name_align = 1
    elif template in ("technical", "stanford"):
        font_family = "Helvetica"
        font_bold = "Helvetica-Bold"
        font_italic = "Helvetica-Oblique"
        accent_color = TECH_ACCENT
        name_align = 0  # left-aligned
    elif template == "minimal":
        font_family = "Helvetica"
        font_bold = "Helvetica-Bold"
        font_italic = "Helvetica-Oblique"
        accent_color = INK_900
        name_align = 0

    usable_width = A4[0] - (0.9 * inch)

    name_style = ParagraphStyle(
        "Name", parent=styles["Normal"], fontName=font_bold, fontSize=15,
        leading=18, textColor=HexColor(INK_900), alignment=name_align, spaceAfter=2,
    )
    contact_style = ParagraphStyle(
        "Contact", parent=styles["Normal"], fontName=font_family, fontSize=8.5,
        leading=11, textColor=HexColor(INK_700), alignment=name_align, spaceAfter=3,
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Normal"], fontName=font_bold, fontSize=9.5,
        leading=12, textColor=HexColor(accent_color), spaceBefore=10, spaceAfter=2,
        letterSpacing=0.6,
    )
    subhead_left = ParagraphStyle(
        "SubheadLeft", parent=styles["Normal"], fontName=font_bold, fontSize=8.5,
        leading=11, textColor=HexColor(INK_900), spaceAfter=1,
    )
    subhead_right = ParagraphStyle(
        "SubheadRight", parent=styles["Normal"], fontName=font_bold if template in ("classic", "harvard") else font_family,
        fontSize=8.0, leading=11, textColor=HexColor(INK_700), alignment=2, rightIndent=8,
    )
    tech_stack_style = ParagraphStyle(
        "TechStack", parent=styles["Normal"], fontName=font_italic, fontSize=8.0,
        leading=10.5, textColor=HexColor(INK_700), spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontName=font_family, fontSize=8.5,
        textColor=HexColor(INK_900), leading=11, spaceAfter=1.5,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=styles["Normal"], fontName=font_family, fontSize=8.5,
        textColor=HexColor(INK_900), leading=11, leftIndent=12, firstLineIndent=-8, spaceAfter=1.5,
    )

    def esc(s: str) -> str:
        clean = _sanitize_text(str(s))
        return clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    personal = parsed_data.get("personal", {}) or parsed_data.get("personal_info", {}) or {}
    name = personal.get("name") or personal.get("full_name") or candidate_name or "Candidate"
    name = re.sub(r"^[#\s*]+", "", str(name)).strip()

    contacts = []
    if personal.get("location"):
        contacts.append(personal["location"])
    elif personal.get("city") or personal.get("address"):
        loc = ", ".join(filter(None, [personal.get("city"), personal.get("address")]))
        if loc:
            contacts.append(loc)
    if personal.get("email"):
        contacts.append(personal["email"])
    if personal.get("phone"):
        contacts.append(personal["phone"])
    if personal.get("linkedin"):
        contacts.append(personal["linkedin"])
    if personal.get("github"):
        contacts.append(personal["github"])
    if personal.get("portfolio"):
        contacts.append(personal["portfolio"])

    story = []
    if name:
        story.append(Paragraph(esc(name), name_style))
    if contacts:
        formatted_contacts = " • ".join(str(c).strip(" •·|") for c in contacts if str(c).strip())
        story.append(Paragraph(esc(formatted_contacts), contact_style))
    if name or contacts:
        divider_color = HexColor(accent_color if template in ("technical", "harvard") else INK_700)
        story.append(HRFlowable(width="100%", thickness=0.6, color=divider_color, spaceAfter=3))

    def add_section_header(title: str):
        story.append(Paragraph(esc(title.upper()), heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor(accent_color if template == "classic" else INK_500), spaceAfter=2))

    # 1. Summary
    summary = parsed_data.get("summary") or parsed_data.get("objective")
    if summary and str(summary).strip():
        add_section_header("Professional Summary")
        story.append(Paragraph(esc(str(summary).strip()), body_style))

    # 2. Skills
    skills_cat = parsed_data.get("skills_categorized", [])
    skills = parsed_data.get("skills", [])
    if skills_cat or skills:
        add_section_header("Technical Skills")
        if skills_cat and isinstance(skills_cat, list):
            for sc in skills_cat:
                sc_str = str(sc).strip()
                if ":" in sc_str:
                    parts = sc_str.split(":", 1)
                    story.append(Paragraph(f"<b>{esc(parts[0].strip())}:</b> {esc(parts[1].strip())}", body_style))
                else:
                    story.append(Paragraph(esc(sc_str), body_style))
        elif isinstance(skills, dict):
            for cat, val in skills.items():
                val_str = ", ".join(str(v) for v in val) if isinstance(val, list) else str(val)
                story.append(Paragraph(f"<b>{esc(cat)}:</b> {esc(val_str)}", body_style))
        elif isinstance(skills, list):
            has_cat = any(":" in str(s) and len(str(s).split(":")[0].split()) <= 6 for s in skills)
            if has_cat:
                for s in skills:
                    s_str = str(s).strip()
                    if ":" in s_str:
                        parts = s_str.split(":", 1)
                        story.append(Paragraph(f"<b>{esc(parts[0].strip())}:</b> {esc(parts[1].strip())}", body_style))
                    else:
                        story.append(Paragraph(esc(s_str), body_style))
            else:
                story.append(Paragraph(esc(", ".join(str(s) for s in skills if s)), body_style))
        else:
            story.append(Paragraph(esc(str(skills)), body_style))

    # 3. Experience
    exp = parsed_data.get("experience_raw", []) or parsed_data.get("experience", []) or parsed_data.get("work_experience", [])
    if exp:
        add_section_header("Work Experience")
        for item in exp:
            if isinstance(item, dict):
                comp = item.get("company", "")
                role = item.get("role", "") or item.get("title", "")
                dates = item.get("dates", "")
                title_str = f"{role} - {comp}" if role and comp else (role or comp)
                if title_str and dates:
                    tbl = Table(
                        [[Paragraph(esc(title_str), subhead_left), Paragraph(esc(dates), subhead_right)]],
                        colWidths=[usable_width * 0.72, usable_width * 0.28],
                        hAlign='LEFT',
                    )
                    tbl.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (0, -1), 0),
                        ("RIGHTPADDING", (1, 0), (1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ]))
                    story.append(tbl)
                elif title_str:
                    story.append(Paragraph(esc(title_str), subhead_left))
                tech = item.get("tech_stack") or item.get("technologies")
                if tech:
                    story.append(Paragraph(esc(f"Technologies: {tech}"), tech_stack_style))
                for b in item.get("bullets", []):
                    clean_b = _BULLET_PREFIX_RE.sub("", str(b)).strip()
                    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{esc(clean_b)}", bullet_style))
            else:
                item_str = str(item).strip()
                if not item_str:
                    continue
                sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
                for sub_idx, sub_clean in enumerate(sub_lines):
                    if _is_tech_stack_line(sub_clean):
                        story.append(Paragraph(esc(sub_clean), tech_stack_style))
                    elif _clean_title_and_date(sub_clean) and sub_idx == 0:
                        t_str, d_str = _clean_title_and_date(sub_clean)
                        tbl = Table(
                            [[Paragraph(esc(t_str), subhead_left), Paragraph(esc(d_str), subhead_right)]],
                            colWidths=[usable_width * 0.72, usable_width * 0.28],
                            hAlign='LEFT',
                        )
                        tbl.setStyle(TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (0, -1), 0),
                            ("RIGHTPADDING", (1, 0), (1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ]))
                        story.append(tbl)
                    else:
                        clean_b = _BULLET_PREFIX_RE.sub("", sub_clean).strip()
                        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{esc(clean_b)}", bullet_style))

    # 4. Projects
    proj = parsed_data.get("projects_raw", []) or parsed_data.get("projects", [])
    if proj:
        add_section_header("Technical Projects")
        for item in proj:
            if isinstance(item, dict):
                title = item.get("title") or item.get("name", "")
                dates = item.get("dates", "")
                if title and dates:
                    tbl = Table(
                        [[Paragraph(esc(title), subhead_left), Paragraph(esc(dates), subhead_right)]],
                        colWidths=[usable_width * 0.72, usable_width * 0.28],
                        hAlign='LEFT',
                    )
                    tbl.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (0, -1), 0),
                        ("RIGHTPADDING", (1, 0), (1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ]))
                    story.append(tbl)
                elif title:
                    story.append(Paragraph(esc(title), subhead_left))
                tech = item.get("tech_stack") or item.get("technologies")
                if tech:
                    story.append(Paragraph(esc(f"Technologies: {tech}"), tech_stack_style))
                for b in item.get("bullets", []):
                    clean_b = _BULLET_PREFIX_RE.sub("", str(b)).strip()
                    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{esc(clean_b)}", bullet_style))
            else:
                item_str = str(item).strip()
                if not item_str:
                    continue
                sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
                for sub_idx, sub_clean in enumerate(sub_lines):
                    if _is_tech_stack_line(sub_clean):
                        story.append(Paragraph(esc(sub_clean), tech_stack_style))
                    elif sub_idx == 0 and _is_project_title_line(sub_clean):
                        story.append(Paragraph(esc(sub_clean), subhead_left))
                    elif _clean_title_and_date(sub_clean) and sub_idx == 0:
                        t_str, d_str = _clean_title_and_date(sub_clean)
                        tbl = Table(
                            [[Paragraph(esc(t_str), subhead_left), Paragraph(esc(d_str), subhead_right)]],
                            colWidths=[usable_width * 0.72, usable_width * 0.28],
                            hAlign='LEFT',
                        )
                        tbl.setStyle(TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (0, -1), 0),
                            ("RIGHTPADDING", (1, 0), (1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ]))
                        story.append(tbl)
                    else:
                        clean_b = _BULLET_PREFIX_RE.sub("", sub_clean).strip()
                        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{esc(clean_b)}", bullet_style))

    # 5. Education
    edu = parsed_data.get("education_raw", []) or parsed_data.get("education", [])
    if edu:
        add_section_header("Education")
        for idx, item in enumerate(edu):
            if isinstance(item, dict):
                inst = item.get("institution") or item.get("school") or item.get("name") or ""
                degree = item.get("degree") or item.get("qualification") or ""
                dates = item.get("dates") or item.get("date_range") or item.get("year") or ""
                loc = item.get("location") or ""
                gpa = item.get("gpa") or item.get("cgpa") or item.get("percentage") or item.get("score") or ""

                if inst:
                    inst_text = inst + (f", {loc}" if loc else "")
                    if dates:
                        tbl = Table(
                            [[Paragraph(esc(inst_text), subhead_left), Paragraph(esc(dates), subhead_right)]],
                            colWidths=[usable_width * 0.72, usable_width * 0.28],
                            hAlign='LEFT',
                        )
                        tbl.setStyle(TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (0, -1), 0),
                            ("RIGHTPADDING", (1, 0), (1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ]))
                        story.append(tbl)
                    else:
                        story.append(Paragraph(esc(inst_text), subhead_left))

                deg_parts = []
                if degree:
                    deg_parts.append(degree)
                if gpa:
                    deg_parts.append(gpa if ("cgpa" in gpa.lower() or "percentage" in gpa.lower() or "%" in gpa) else f"CGPA: {gpa}")
                if deg_parts:
                    story.append(Paragraph(esc(" | ".join(deg_parts)), body_style))
            else:
                item_str = str(item).strip()
                if not item_str:
                    continue
                sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
                for sub_idx, sub_clean in enumerate(sub_lines):
                    # Zero destructive bullet stripping on education lines (preserves 'B.E', 'B.Tech')
                    cleaned = _clean_title_and_date(sub_clean)
                    if cleaned and cleaned[0] and cleaned[1] and sub_idx == 0:
                        title_str, date_str = cleaned
                        tbl = Table(
                            [[Paragraph(esc(title_str), subhead_left), Paragraph(esc(date_str), subhead_right)]],
                            colWidths=[usable_width * 0.72, usable_width * 0.28],
                            hAlign='LEFT',
                        )
                        tbl.setStyle(TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (0, -1), 0),
                            ("RIGHTPADDING", (1, 0), (1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ]))
                        story.append(tbl)
                    else:
                        style_to_use = subhead_left if sub_idx == 0 else body_style
                        story.append(Paragraph(esc(sub_clean), style_to_use))

            # Visual spacing between distinct education blocks
            if idx < len(edu) - 1:
                story.append(Spacer(1, 3))

    # 6. Certifications
    certs = parsed_data.get("certifications", []) or parsed_data.get("certifications_raw", []) or parsed_data.get("certificates", [])
    if certs:
        add_section_header("Certifications")
        for item in certs:
            item_str = str(item).strip()
            if not item_str:
                continue
            cleaned_bullet = _BULLET_PREFIX_RE.sub("", item_str).strip()
            bullet_text = f"&bull;&nbsp;&nbsp;{esc(cleaned_bullet)}"
            story.append(Paragraph(bullet_text, bullet_style))

    # 7. Achievements
    ach = parsed_data.get("achievements", []) or parsed_data.get("achievements_raw", []) or parsed_data.get("awards", [])
    if ach:
        add_section_header("Achievements")
        for item in ach:
            item_str = str(item).strip()
            if not item_str:
                continue
            cleaned_bullet = _BULLET_PREFIX_RE.sub("", item_str).strip()
            bullet_text = f"&bull;&nbsp;&nbsp;{esc(cleaned_bullet)}"
            story.append(Paragraph(bullet_text, bullet_style))

    # 8. Languages
    langs = parsed_data.get("languages", []) or parsed_data.get("languages_raw", []) or parsed_data.get("languages_known", [])
    if langs:
        add_section_header("Languages")
        if isinstance(langs, list):
            story.append(Paragraph(esc(", ".join(str(l) for l in langs if l)), body_style))
        else:
            story.append(Paragraph(esc(str(langs)), body_style))

    doc.build(story)
    return buffer.getvalue()


def generate_pdf(content: str | dict, candidate_name: str = "", template: str = "modern", experience_level: str = "fresher") -> bytes:
    """
    Primary PDF generation entrypoint.
    If content is dict, renders directly.
    If content is string, parses structure deterministically and renders structured flowables.
    """
    if isinstance(content, dict):
        return render_pdf_from_structured(content, candidate_name=candidate_name, template=template, experience_level=experience_level)

    from app.modules.resume.parsing.structurer import structure_resume_text
    structured = structure_resume_text(str(content))
    return render_pdf_from_structured(structured, candidate_name=candidate_name, template=template, experience_level=experience_level)


def _set_run_color(run, hex_color: str):
    run.font.color.rgb = RGBColor.from_string(hex_color.lstrip("#"))


def _add_bottom_border(paragraph, hex_color: str = SIGNAL_600):
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), hex_color.lstrip("#"))
    borders.append(bottom)
    p_pr.append(borders)


def render_docx_from_structured(
    parsed_data: dict, candidate_name: str = "", template: str = "modern"
) -> bytes:
    """
    Renders an ATS-optimized, beautifully styled DOCX document directly from a structured resume dictionary.
    No regex text-splicing — pure structured document generation.
    """
    template = template.lower() if template else "modern"
    document = Document()

    # Set 0.45 in page margins
    sections = document.sections
    for section in sections:
        section.top_margin = Inches(0.4)
        section.bottom_margin = Inches(0.4)
        section.left_margin = Inches(0.45)
        section.right_margin = Inches(0.45)

    font_name = "Calibri"
    accent_color = SIGNAL_600
    alignment = WD_ALIGN_PARAGRAPH.CENTER

    if template in ("classic", "harvard"):
        font_name = "Times New Roman"
        accent_color = CLASSIC_ACCENT
        alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif template in ("technical", "stanford"):
        font_name = "Arial"
        accent_color = TECH_ACCENT
        alignment = WD_ALIGN_PARAGRAPH.LEFT
    elif template == "minimal":
        font_name = "Calibri"
        accent_color = INK_900
        alignment = WD_ALIGN_PARAGRAPH.LEFT

    normal = document.styles["Normal"]
    normal.font.name = font_name
    normal.font.size = Pt(9.0)

    personal = parsed_data.get("personal", {}) or parsed_data.get("personal_info", {}) or {}
    name = personal.get("name") or personal.get("full_name") or candidate_name or "Candidate"
    name = re.sub(r"^[#\s*]+", "", str(name)).strip()

    contacts = []
    if personal.get("location"):
        contacts.append(personal["location"])
    elif personal.get("city") or personal.get("address"):
        loc = ", ".join(filter(None, [personal.get("city"), personal.get("address")]))
        if loc:
            contacts.append(loc)
    if personal.get("email"):
        contacts.append(personal["email"])
    if personal.get("phone"):
        contacts.append(personal["phone"])
    if personal.get("linkedin"):
        contacts.append(personal["linkedin"])
    if personal.get("github"):
        contacts.append(personal["github"])
    if personal.get("portfolio"):
        contacts.append(personal["portfolio"])

    if name:
        p_name = document.add_paragraph()
        p_name.alignment = alignment
        p_name.paragraph_format.space_before = Pt(0)
        p_name.paragraph_format.space_after = Pt(1)
        r_name = p_name.add_run(name)
        r_name.bold = True
        r_name.font.size = Pt(15)
        _set_run_color(r_name, INK_900)

    if contacts:
        p_contact = document.add_paragraph()
        p_contact.alignment = alignment
        p_contact.paragraph_format.space_before = Pt(0)
        p_contact.paragraph_format.space_after = Pt(3)
        formatted_contacts = " • ".join(str(c).strip(" •·|") for c in contacts if str(c).strip())
        r_contact = p_contact.add_run(formatted_contacts)
        r_contact.font.size = Pt(8.5)
        _set_run_color(r_contact, INK_700)

    def add_section_header(title: str):
        p_head = document.add_paragraph()
        p_head.paragraph_format.space_before = Pt(10)
        p_head.paragraph_format.space_after = Pt(2)
        p_head.paragraph_format.keep_with_next = True
        r_head = p_head.add_run(title.upper())
        r_head.bold = True
        r_head.font.size = Pt(10)
        _set_run_color(r_head, accent_color)
        _add_bottom_border(p_head, accent_color)

    # 1. Summary
    summary = parsed_data.get("summary") or parsed_data.get("objective")
    if summary and str(summary).strip():
        add_section_header("Professional Summary")
        p_sum = document.add_paragraph()
        p_sum.paragraph_format.space_before = Pt(0)
        p_sum.paragraph_format.space_after = Pt(2)
        r_sum = p_sum.add_run(str(summary).strip())
        r_sum.font.size = Pt(8.5)
        _set_run_color(r_sum, INK_900)

    # 2. Skills
    skills_cat = parsed_data.get("skills_categorized", [])
    skills = parsed_data.get("skills", [])
    if skills_cat or skills:
        add_section_header("Technical Skills")
        if skills_cat and isinstance(skills_cat, list):
            for sc in skills_cat:
                sc_str = str(sc).strip()
                p_sk = document.add_paragraph()
                p_sk.paragraph_format.space_before = Pt(0)
                p_sk.paragraph_format.space_after = Pt(1.5)
                if ":" in sc_str:
                    parts = sc_str.split(":", 1)
                    r_pre = p_sk.add_run(parts[0].strip() + ": ")
                    r_pre.bold = True
                    r_pre.font.size = Pt(8.5)
                    _set_run_color(r_pre, INK_900)
                    r_val = p_sk.add_run(parts[1].strip())
                    r_val.font.size = Pt(8.5)
                    _set_run_color(r_val, INK_900)
                else:
                    r_val = p_sk.add_run(sc_str)
                    r_val.font.size = Pt(8.5)
                    _set_run_color(r_val, INK_900)
        elif isinstance(skills, dict):
            for cat, val in skills.items():
                p_sk = document.add_paragraph()
                p_sk.paragraph_format.space_before = Pt(0)
                p_sk.paragraph_format.space_after = Pt(1.5)
                r_pre = p_sk.add_run(f"{cat}: ")
                r_pre.bold = True
                r_pre.font.size = Pt(8.5)
                _set_run_color(r_pre, INK_900)
                val_str = ", ".join(str(v) for v in val) if isinstance(val, list) else str(val)
                r_val = p_sk.add_run(val_str)
                r_val.font.size = Pt(8.5)
                _set_run_color(r_val, INK_900)
        elif isinstance(skills, list):
            has_cat = any(":" in str(s) and len(str(s).split(":")[0].split()) <= 6 for s in skills)
            if has_cat:
                for s in skills:
                    s_str = str(s).strip()
                    p_sk = document.add_paragraph()
                    p_sk.paragraph_format.space_before = Pt(0)
                    p_sk.paragraph_format.space_after = Pt(1.5)
                    if ":" in s_str:
                        parts = s_str.split(":", 1)
                        r_pre = p_sk.add_run(parts[0].strip() + ": ")
                        r_pre.bold = True
                        r_pre.font.size = Pt(8.5)
                        _set_run_color(r_pre, INK_900)
                        r_val = p_sk.add_run(parts[1].strip())
                        r_val.font.size = Pt(8.5)
                        _set_run_color(r_val, INK_900)
                    else:
                        r_val = p_sk.add_run(s_str)
                        r_val.font.size = Pt(8.5)
                        _set_run_color(r_val, INK_900)
            else:
                p_sk = document.add_paragraph()
                p_sk.paragraph_format.space_before = Pt(0)
                p_sk.paragraph_format.space_after = Pt(2)
                r_sk = p_sk.add_run(", ".join(str(s) for s in skills if s))
                r_sk.font.size = Pt(8.5)
                _set_run_color(r_sk, INK_900)
        else:
            p_sk = document.add_paragraph()
            p_sk.paragraph_format.space_before = Pt(0)
            p_sk.paragraph_format.space_after = Pt(2)
            r_sk = p_sk.add_run(str(skills))
            r_sk.font.size = Pt(8.5)
            _set_run_color(r_sk, INK_900)

    # 3. Experience
    exp = parsed_data.get("experience_raw", []) or parsed_data.get("experience", []) or parsed_data.get("work_experience", [])
    if exp:
        add_section_header("Work Experience")
        for item in exp:
            if isinstance(item, dict):
                comp = item.get("company", "")
                role = item.get("role", "") or item.get("title", "")
                dates = item.get("dates", "")
                title_str = f"{role} - {comp}" if role and comp else (role or comp)
                if title_str:
                    p_tit = document.add_paragraph()
                    p_tit.paragraph_format.space_before = Pt(2)
                    p_tit.paragraph_format.space_after = Pt(1)
                    if dates:
                        p_tit.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
                        r1 = p_tit.add_run(title_str)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                        r2 = p_tit.add_run(f"\t{dates}")
                        r2.bold = True if template in ("classic", "harvard") else False
                        r2.font.size = Pt(8.5)
                        _set_run_color(r2, INK_700)
                    else:
                        r1 = p_tit.add_run(title_str)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                tech = item.get("tech_stack") or item.get("technologies")
                if tech:
                    p_tech = document.add_paragraph()
                    p_tech.paragraph_format.space_before = Pt(0)
                    p_tech.paragraph_format.space_after = Pt(2)
                    r_tech = p_tech.add_run(f"Technologies: {tech}")
                    r_tech.italic = True
                    r_tech.font.size = Pt(8.0)
                    _set_run_color(r_tech, INK_700)
                for b in item.get("bullets", []):
                    clean_b = _BULLET_PREFIX_RE.sub("", str(b)).strip()
                    p_b = document.add_paragraph(style="List Bullet")
                    p_b.paragraph_format.space_before = Pt(0)
                    p_b.paragraph_format.space_after = Pt(1)
                    p_b.paragraph_format.left_indent = Inches(0.2)
                    r_b = p_b.add_run(clean_b)
                    r_b.font.size = Pt(8.5)
                    _set_run_color(r_b, INK_900)
            else:
                item_str = str(item).strip()
                if not item_str:
                    continue
                sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
                for sub_idx, sub_clean in enumerate(sub_lines):
                    if _is_tech_stack_line(sub_clean):
                        p_tech = document.add_paragraph()
                        p_tech.paragraph_format.space_before = Pt(0)
                        p_tech.paragraph_format.space_after = Pt(2)
                        r_tech = p_tech.add_run(sub_clean)
                        r_tech.italic = True
                        r_tech.font.size = Pt(8.0)
                        _set_run_color(r_tech, INK_700)
                    elif sub_idx == 0 and _is_project_title_line(sub_clean):
                        p_title = document.add_paragraph()
                        p_title.paragraph_format.space_before = Pt(2)
                        p_title.paragraph_format.space_after = Pt(1)
                        r_title = p_title.add_run(sub_clean)
                        r_title.bold = True
                        r_title.font.size = Pt(8.5)
                        _set_run_color(r_title, INK_900)
                    elif _clean_title_and_date(sub_clean) and sub_idx == 0:
                        t_str, d_str = _clean_title_and_date(sub_clean)
                        p_sub = document.add_paragraph()
                        p_sub.paragraph_format.space_before = Pt(2)
                        p_sub.paragraph_format.space_after = Pt(1)
                        p_sub.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
                        r1 = p_sub.add_run(t_str)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                        r2 = p_sub.add_run(f"\t{d_str}")
                        r2.bold = True if template in ("classic", "harvard") else False
                        r2.font.size = Pt(8.5)
                        _set_run_color(r2, INK_700)
                    else:
                        clean_b = _BULLET_PREFIX_RE.sub("", sub_clean).strip()
                        p_b = document.add_paragraph(style="List Bullet")
                        p_b.paragraph_format.space_before = Pt(0)
                        p_b.paragraph_format.space_after = Pt(1)
                        p_b.paragraph_format.left_indent = Inches(0.2)
                        r_b = p_b.add_run(clean_b)
                        r_b.font.size = Pt(8.5)
                        _set_run_color(r_b, INK_900)

    # 4. Projects
    proj = parsed_data.get("projects_raw", []) or parsed_data.get("projects", [])
    if proj:
        add_section_header("Technical Projects")
        for item in proj:
            if isinstance(item, dict):
                title = item.get("title") or item.get("name", "")
                dates = item.get("dates", "")
                if title:
                    p_tit = document.add_paragraph()
                    p_tit.paragraph_format.space_before = Pt(2)
                    p_tit.paragraph_format.space_after = Pt(1)
                    if dates:
                        p_tit.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
                        r1 = p_tit.add_run(title)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                        r2 = p_tit.add_run(f"\t{dates}")
                        r2.bold = True if template in ("classic", "harvard") else False
                        r2.font.size = Pt(8.5)
                        _set_run_color(r2, INK_700)
                    else:
                        r1 = p_tit.add_run(title)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                tech = item.get("tech_stack") or item.get("technologies")
                if tech:
                    p_tech = document.add_paragraph()
                    p_tech.paragraph_format.space_before = Pt(0)
                    p_tech.paragraph_format.space_after = Pt(2)
                    r_tech = p_tech.add_run(f"Technologies: {tech}")
                    r_tech.italic = True
                    r_tech.font.size = Pt(8.0)
                    _set_run_color(r_tech, INK_700)
                for b in item.get("bullets", []):
                    clean_b = _BULLET_PREFIX_RE.sub("", str(b)).strip()
                    p_b = document.add_paragraph(style="List Bullet")
                    p_b.paragraph_format.space_before = Pt(0)
                    p_b.paragraph_format.space_after = Pt(1)
                    p_b.paragraph_format.left_indent = Inches(0.2)
                    r_b = p_b.add_run(clean_b)
                    r_b.font.size = Pt(8.5)
                    _set_run_color(r_b, INK_900)
            else:
                item_str = str(item).strip()
                if not item_str:
                    continue
                sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
                for sub_idx, sub_clean in enumerate(sub_lines):
                    if _is_tech_stack_line(sub_clean):
                        p_tech = document.add_paragraph()
                        p_tech.paragraph_format.space_before = Pt(0)
                        p_tech.paragraph_format.space_after = Pt(2)
                        r_tech = p_tech.add_run(sub_clean)
                        r_tech.italic = True
                        r_tech.font.size = Pt(8.0)
                        _set_run_color(r_tech, INK_700)
                    elif _clean_title_and_date(sub_clean) and sub_idx == 0:
                        t_str, d_str = _clean_title_and_date(sub_clean)
                        p_sub = document.add_paragraph()
                        p_sub.paragraph_format.space_before = Pt(2)
                        p_sub.paragraph_format.space_after = Pt(1)
                        p_sub.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
                        r1 = p_sub.add_run(t_str)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                        r2 = p_sub.add_run(f"\t{d_str}")
                        r2.bold = True if template in ("classic", "harvard") else False
                        r2.font.size = Pt(8.5)
                        _set_run_color(r2, INK_700)
                    elif _is_project_title_line(sub_clean):
                        p_title = document.add_paragraph()
                        p_title.paragraph_format.space_before = Pt(2)
                        p_title.paragraph_format.space_after = Pt(1)
                        r_title = p_title.add_run(sub_clean)
                        r_title.bold = True
                        r_title.font.size = Pt(8.5)
                        _set_run_color(r_title, INK_900)
                    else:
                        clean_b = _BULLET_PREFIX_RE.sub("", sub_clean).strip()
                        p_b = document.add_paragraph(style="List Bullet")
                        p_b.paragraph_format.space_before = Pt(0)
                        p_b.paragraph_format.space_after = Pt(1)
                        p_b.paragraph_format.left_indent = Inches(0.2)
                        r_b = p_b.add_run(clean_b)
                        r_b.font.size = Pt(8.5)
                        _set_run_color(r_b, INK_900)

    # 5. Education
    edu = parsed_data.get("education_raw", []) or parsed_data.get("education", [])
    if edu:
        add_section_header("Education")
        for idx, item in enumerate(edu):
            if isinstance(item, dict):
                inst = item.get("institution") or item.get("school") or item.get("name") or ""
                degree = item.get("degree") or item.get("qualification") or ""
                dates = item.get("dates") or item.get("date_range") or item.get("year") or ""
                loc = item.get("location") or ""
                gpa = item.get("gpa") or item.get("cgpa") or item.get("percentage") or item.get("score") or ""

                if inst:
                    p_inst = document.add_paragraph()
                    p_inst.paragraph_format.space_before = Pt(3 if idx > 0 else 0)
                    p_inst.paragraph_format.space_after = Pt(1)
                    inst_text = inst + (f", {loc}" if loc else "")
                    if dates:
                        p_inst.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
                        r1 = p_inst.add_run(inst_text)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                        r2 = p_inst.add_run(f"\t{dates}")
                        r2.bold = True if template in ("classic", "harvard") else False
                        r2.font.size = Pt(8.5)
                        _set_run_color(r2, INK_700)
                    else:
                        r1 = p_inst.add_run(inst_text)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)

                deg_parts = []
                if degree:
                    deg_parts.append(degree)
                if gpa:
                    deg_parts.append(gpa if ("cgpa" in gpa.lower() or "percentage" in gpa.lower() or "%" in gpa) else f"CGPA: {gpa}")
                if deg_parts:
                    p_deg = document.add_paragraph()
                    p_deg.paragraph_format.space_before = Pt(0)
                    p_deg.paragraph_format.space_after = Pt(1.5)
                    r_deg = p_deg.add_run(" | ".join(deg_parts))
                    r_deg.font.size = Pt(8.5)
                    _set_run_color(r_deg, INK_900)
            else:
                item_str = str(item).strip()
                if not item_str:
                    continue
                sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
                for sub_idx, sub_clean in enumerate(sub_lines):
                    p_ed = document.add_paragraph()
                    p_ed.paragraph_format.space_before = Pt(3 if sub_idx == 0 and idx > 0 else 0)
                    p_ed.paragraph_format.space_after = Pt(1)
                    cleaned = _clean_title_and_date(sub_clean)
                    if cleaned and cleaned[0] and cleaned[1] and sub_idx == 0:
                        t_str, d_str = cleaned
                        p_ed.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
                        r1 = p_ed.add_run(t_str)
                        r1.bold = True
                        r1.font.size = Pt(8.5)
                        _set_run_color(r1, INK_900)
                        r2 = p_ed.add_run(f"\t{d_str}")
                        r2.bold = True if template in ("classic", "harvard") else False
                        r2.font.size = Pt(8.5)
                        _set_run_color(r2, INK_700)
                    else:
                        r_ed = p_ed.add_run(sub_clean)
                        r_ed.font.size = Pt(8.5)
                        if sub_idx == 0:
                            r_ed.bold = True
                            _set_run_color(r_ed, INK_900)
                        else:
                            _set_run_color(r_ed, INK_900)

    # 6. Certifications
    certs = parsed_data.get("certifications", []) or parsed_data.get("certifications_raw", []) or parsed_data.get("certificates", [])
    if certs:
        add_section_header("Certifications")
        for item in certs:
            item_str = str(item).strip()
            if not item_str:
                continue
            clean_b = _BULLET_PREFIX_RE.sub("", item_str).strip()
            p_b = document.add_paragraph(style="List Bullet")
            p_b.paragraph_format.space_before = Pt(0)
            p_b.paragraph_format.space_after = Pt(1)
            p_b.paragraph_format.left_indent = Inches(0.2)
            r_b = p_b.add_run(clean_b)
            r_b.font.size = Pt(8.5)
            _set_run_color(r_b, INK_900)

    # 7. Achievements
    ach = parsed_data.get("achievements", []) or parsed_data.get("achievements_raw", []) or parsed_data.get("awards", [])
    if ach:
        add_section_header("Achievements")
        for item in ach:
            item_str = str(item).strip()
            if not item_str:
                continue
            clean_b = _BULLET_PREFIX_RE.sub("", item_str).strip()
            p_b = document.add_paragraph(style="List Bullet")
            p_b.paragraph_format.space_before = Pt(0)
            p_b.paragraph_format.space_after = Pt(1)
            p_b.paragraph_format.left_indent = Inches(0.2)
            r_b = p_b.add_run(clean_b)
            r_b.font.size = Pt(8.5)
            _set_run_color(r_b, INK_900)

    # 8. Languages
    langs = parsed_data.get("languages", []) or parsed_data.get("languages_raw", []) or parsed_data.get("languages_known", [])
    if langs:
        add_section_header("Languages")
        p_lang = document.add_paragraph()
        p_lang.paragraph_format.space_before = Pt(0)
        p_lang.paragraph_format.space_after = Pt(2)
        lang_text = ", ".join(str(l) for l in langs if l) if isinstance(langs, list) else str(langs)
        r_lang = p_lang.add_run(lang_text)
        r_lang.font.size = Pt(8.5)
        _set_run_color(r_lang, INK_900)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def generate_docx(content: str | dict, candidate_name: str = "", template: str = "modern", experience_level: str = "fresher") -> bytes:
    """
    Primary DOCX generation entrypoint.
    If content is dict, renders directly.
    If content is string, parses structure deterministically and renders structured document.
    """
    if isinstance(content, dict):
        return render_docx_from_structured(content, candidate_name=candidate_name, template=template)

    from app.modules.resume.parsing.structurer import structure_resume_text
    structured = structure_resume_text(str(content))
    return render_docx_from_structured(structured, candidate_name=candidate_name, template=template)


def measure_pdf_page_count(pdf_bytes: bytes) -> int:
    """Measures the exact page count of a PDF byte stream using PyMuPDF."""
    import pymupdf
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    count = doc.page_count
    doc.close()
    return count
