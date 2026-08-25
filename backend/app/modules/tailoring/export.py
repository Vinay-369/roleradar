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

    personal = parsed_data.get("personal", {}) or {}
    name = personal.get("name") or "Candidate"
    contacts = []
    if personal.get("location"):
        contacts.append(personal["location"])
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
    summary = parsed_data.get("summary")
    if summary and summary.strip():
        lines.append("PROFESSIONAL SUMMARY")
        lines.append(summary.strip())
        lines.append("")

    # Skills
    skills = parsed_data.get("skills", [])
    if skills:
        lines.append("TECHNICAL SKILLS")
        if isinstance(skills, list):
            lines.append(", ".join(str(s) for s in skills if s))
        else:
            lines.append(str(skills))
        lines.append("")

    # Experience
    exp = parsed_data.get("experience_raw", [])
    if exp:
        lines.append("PROFESSIONAL EXPERIENCE")
        for b in exp:
            b_str = str(b).strip()
            if b_str:
                prefix = "" if b_str.startswith(("•", "-", "*")) else "• "
                lines.append(f"{prefix}{b_str}")
        lines.append("")

    # Projects
    proj = parsed_data.get("projects_raw", [])
    if proj:
        lines.append("TECHNICAL PROJECTS")
        for b in proj:
            b_str = str(b).strip()
            if b_str:
                prefix = "" if b_str.startswith(("•", "-", "*")) else "• "
                lines.append(f"{prefix}{b_str}")
        lines.append("")

    # Education
    edu = parsed_data.get("education_raw", [])
    if edu:
        lines.append("EDUCATION")
        for e in edu:
            e_str = str(e).strip()
            if e_str:
                lines.append(e_str)
        lines.append("")

    # Certifications
    certs = parsed_data.get("certifications", [])
    if certs:
        lines.append("CERTIFICATIONS")
        for c in certs:
            c_str = str(c).strip()
            if c_str:
                prefix = "" if c_str.startswith(("•", "-", "*")) else "• "
                lines.append(f"{prefix}{c_str}")
        lines.append("")

    # Achievements
    ach = parsed_data.get("achievements", [])
    if ach:
        lines.append("ACHIEVEMENTS")
        for a in ach:
            a_str = str(a).strip()
            if a_str:
                prefix = "" if a_str.startswith(("•", "-", "*")) else "• "
                lines.append(f"{prefix}{a_str}")
        lines.append("")

    # Languages
    langs = parsed_data.get("languages", [])
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
    r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}(?:\s*[-–—to]+\s*(?:Present|Current|\d{4}|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}))?)\b\)?\s*$",
    re.IGNORECASE,
)


def _is_section_header(line: str) -> bool:
    normalized = line.strip().rstrip(":-–— \t")
    if len(normalized) > 40:
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
    contact_lines: list[str] = []
    body_start_idx = name_idx + 1

    for i in range(name_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if _is_section_header(stripped):
            body_start_idx = i
            break
        if _looks_like_contact_line(stripped) or len(contact_lines) < 2 and ("|" in stripped or "•" in stripped):
            contact_lines.append(stripped)
            body_start_idx = i + 1
        else:
            body_start_idx = i
            break

    return name.strip(), contact_lines, lines[body_start_idx:]


def _clean_title_and_date(line: str) -> tuple[str, str] | None:
    """Extracts clean (title_or_institution, right_aligned_date) if line contains a date span."""
    date_match = _DATE_PATTERN_RE.search(line)
    if not date_match or line.startswith("•") or line.startswith("-"):
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


def _merge_standalone_dates(body_lines: list[str]) -> list[str]:
    """Combines standalone date lines with the preceding title line."""
    processed = []
    i = 0
    lines = list(body_lines)
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped:
            processed.append(line)
            i += 1
            continue

        cleaned = _clean_title_and_date(stripped)
        # If line is ONLY a date (e.g. "April 2026", "Aug 2021") with no title
        if cleaned and not cleaned[0]:
            prev_valid = processed and processed[-1].strip() and not _is_section_header(processed[-1].strip()) and not _BULLET_PREFIX_RE.match(processed[-1].strip())
            if prev_valid:
                processed[-1] = processed[-1].rstrip() + " " + stripped
            else:
                processed.append(line)
        else:
            processed.append(line)
            
        i += 1
    return processed


def _is_skill_category(line: str) -> bool:
    return ":" in line and not line.startswith("http") and len(line.split(":")[0].split()) <= 5


def _is_title_and_date(line: str) -> bool:
    cleaned = _clean_title_and_date(line)
    return bool(cleaned and cleaned[0])


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


def _merge_hard_wrapped_lines(body_lines: list[str]) -> list[str]:
    """Merges ONLY broken bullet continuations, preserving distinct headings, titles, and institutions."""
    processed: list[str] = []
    
    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            processed.append(line)
            continue
            
        current_is_header = _is_section_header(stripped)
        current_is_title_date = _is_title_and_date(stripped)
        current_is_bullet = bool(_BULLET_PREFIX_RE.match(stripped))
        current_is_skill = _is_skill_category(stripped)
        current_is_tech = _is_tech_stack_line(stripped)
        
        # If current line is a special structural element, keep separate
        if current_is_header or current_is_title_date or current_is_bullet or current_is_skill or current_is_tech:
            processed.append(line)
            continue
            
        if not processed:
            processed.append(line)
            continue
            
        prev_line = processed[-1]
        prev_stripped = prev_line.strip()
        
        if not prev_stripped:
            processed.append(line)
            continue
            
        prev_is_header = _is_section_header(prev_stripped)
        prev_is_title_date = _is_title_and_date(prev_stripped)
        prev_is_bullet = bool(_BULLET_PREFIX_RE.match(prev_stripped))
        prev_is_skill = _is_skill_category(prev_stripped)
        prev_is_tech = _is_tech_stack_line(prev_stripped)
        
        # DO NOT merge if previous is header, title+date, skill, or tech stack
        if prev_is_header or prev_is_title_date or prev_is_skill or prev_is_tech:
            processed.append(line)
        elif prev_is_bullet:
            # Only merge into previous bullet if previous bullet didn't end with period/semicolon
            if prev_stripped.endswith((".", ";", "!")):
                processed.append(line)
            else:
                processed[-1] = prev_line.rstrip() + " " + stripped
        else:
            # Plain text line following another plain text line (e.g. institution or summary)
            if prev_stripped.endswith((".", ";", "!")):
                processed.append(line)
            else:
                # If current line looks like an institution or degree or standalone title, keep separate!
                if len(stripped.split()) <= 10 and ("," in stripped or "-" in stripped):
                    processed.append(line)
                else:
                    processed[-1] = prev_line.rstrip() + " " + stripped
            
    return processed


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
        leading=12, textColor=HexColor(accent_color), spaceBefore=9, spaceAfter=2,
        letterSpacing=0.6,
    )
    subhead_left = ParagraphStyle(
        "SubheadLeft", parent=styles["Normal"], fontName=font_bold, fontSize=8.5,
        leading=11, textColor=HexColor(INK_900),
    )
    subhead_right = ParagraphStyle(
        "SubheadRight", parent=styles["Normal"], fontName=font_bold if template in ("classic", "harvard") else font_family,
        fontSize=8.0, leading=11, textColor=HexColor(INK_700), alignment=2, rightIndent=8,
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

    personal = parsed_data.get("personal", {}) or {}
    name = personal.get("name") or candidate_name or "Candidate"
    contacts = []
    if personal.get("location"):
        contacts.append(personal["location"])
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
        story.append(Paragraph(esc(" • ".join(contacts)), contact_style))
    if name or contacts:
        divider_color = HexColor(accent_color if template in ("technical", "harvard") else INK_700)
        story.append(HRFlowable(width="100%", thickness=0.6, color=divider_color, spaceAfter=3))

    def add_section_header(title: str):
        story.append(Paragraph(esc(title.upper()), heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor(accent_color if template == "classic" else INK_500), spaceAfter=2))

    # 1. Summary
    summary = parsed_data.get("summary")
    if summary and summary.strip():
        add_section_header("Professional Summary")
        story.append(Paragraph(esc(summary.strip()), body_style))

    # 2. Skills
    skills = parsed_data.get("skills", [])
    if skills:
        add_section_header("Technical Skills")
        if isinstance(skills, list):
            story.append(Paragraph(esc(", ".join(str(s) for s in skills if s)), body_style))
        else:
            story.append(Paragraph(esc(str(skills)), body_style))

    # 3. Experience
    exp = parsed_data.get("experience_raw", [])
    if exp:
        add_section_header("Work Experience")
        for item in exp:
            item_str = str(item).strip()
            if not item_str:
                continue
            cleaned_bullet = _BULLET_PREFIX_RE.sub("", item_str).strip()
            bullet_text = f"&bull; {esc(cleaned_bullet)}"
            story.append(Paragraph(bullet_text, bullet_style))

    # 4. Projects
    proj = parsed_data.get("projects_raw", [])
    if proj:
        add_section_header("Projects")
        for item in proj:
            item_str = str(item).strip()
            if not item_str:
                continue
            cleaned_bullet = _BULLET_PREFIX_RE.sub("", item_str).strip()
            bullet_text = f"&bull; {esc(cleaned_bullet)}"
            story.append(Paragraph(bullet_text, bullet_style))

    # 5. Education
    edu = parsed_data.get("education_raw", [])
    if edu:
        add_section_header("Education")
        for item in edu:
            item_str = str(item).strip()
            if not item_str:
                continue
            sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
            for sub_idx, sub_clean in enumerate(sub_lines):
                cleaned = _clean_title_and_date(sub_clean)
                if cleaned:
                    title_str, date_str = cleaned
                    col_w1 = usable_width * 0.72
                    col_w2 = usable_width * 0.28
                    tbl = Table(
                        [[Paragraph(esc(title_str), subhead_left), Paragraph(esc(date_str), subhead_right)]],
                        colWidths=[col_w1, col_w2],
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
                    style_to_use = subhead_left if sub_idx == 0 and len(sub_lines) > 1 else body_style
                    story.append(Paragraph(esc(sub_clean), style_to_use))

    # 6. Certifications
    certs = parsed_data.get("certifications", [])
    if certs:
        add_section_header("Certifications")
        for item in certs:
            item_str = str(item).strip()
            if not item_str:
                continue
            cleaned_bullet = _BULLET_PREFIX_RE.sub("", item_str).strip()
            bullet_text = f"&bull; {esc(cleaned_bullet)}"
            story.append(Paragraph(bullet_text, bullet_style))

    # 7. Achievements
    ach = parsed_data.get("achievements", [])
    if ach:
        add_section_header("Achievements")
        for item in ach:
            item_str = str(item).strip()
            if not item_str:
                continue
            cleaned_bullet = _BULLET_PREFIX_RE.sub("", item_str).strip()
            bullet_text = f"&bull; {esc(cleaned_bullet)}"
            story.append(Paragraph(bullet_text, bullet_style))

    # 8. Languages
    langs = parsed_data.get("languages", [])
    if langs:
        add_section_header("Languages")
        if isinstance(langs, list):
            story.append(Paragraph(esc(", ".join(str(l) for l in langs if l)), body_style))
        else:
            story.append(Paragraph(esc(str(langs)), body_style))

    doc.build(story)
    return buffer.getvalue()


def generate_pdf(content: str | dict, candidate_name: str = "", template: str = "modern", experience_level: str = "fresher") -> bytes:
    if isinstance(content, dict):
        return render_pdf_from_structured(content, candidate_name=candidate_name, template=template, experience_level=experience_level)

    resume_text = _sanitize_text(str(content))
    template = template.lower() if template else "modern"
    buffer = io.BytesIO()

    # 0.45 inch margins for standard Harvard / Stanford ATS compliance
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
        name_align = 0  # left-aligned for technical / stanford layout
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
        leading=12, textColor=HexColor(accent_color), spaceBefore=9, spaceAfter=2,
        letterSpacing=0.6,
    )
    subhead_left = ParagraphStyle(
        "SubheadLeft", parent=styles["Normal"], fontName=font_bold, fontSize=8.5,
        leading=11, textColor=HexColor(INK_900),
    )
    subhead_right = ParagraphStyle(
        "SubheadRight", parent=styles["Normal"], fontName=font_bold if template in ("classic", "harvard") else font_family,
        fontSize=8.0, leading=11, textColor=HexColor(INK_700), alignment=2,  # right aligned
        rightIndent=8,  # Insets date slightly from right border
    )
    tech_stack_style = ParagraphStyle(
        "TechStack", parent=styles["Normal"], fontName=font_italic, fontSize=8.0,
        leading=10.5, textColor=HexColor(INK_700), spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontName=font_family, fontSize=8.5,
        textColor=HexColor(INK_900), leading=11, spaceAfter=1.5,
    )
    institution_style = ParagraphStyle(
        "Institution", parent=styles["Normal"], fontName=font_family, fontSize=8.5,
        textColor=HexColor(INK_700), leading=11, spaceAfter=2.5,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=styles["Normal"], fontName=font_family, fontSize=8.5,
        textColor=HexColor(INK_900), leading=11, leftIndent=12, firstLineIndent=-8, spaceAfter=1.5,
    )

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    name, contact_lines, body_lines = _split_name_contact_body(resume_text)
    if not name and candidate_name:
        name = candidate_name
        
    body_lines = _merge_standalone_dates(body_lines)
    body_lines = _merge_hard_wrapped_lines(body_lines)

    story = []
    if name:
        story.append(Paragraph(esc(name), name_style))
    if contact_lines:
        formatted_contacts = " • ".join(c.strip(" •·|") for c in contact_lines if c.strip())
        story.append(Paragraph(esc(formatted_contacts), contact_style))
    if name or contact_lines:
        divider_color = HexColor(accent_color if template in ("technical", "harvard") else INK_700)
        story.append(HRFlowable(width="100%", thickness=0.6, color=divider_color, spaceAfter=3))

    current_section = ""
    last_was_blank = False
    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            if not last_was_blank:
                story.append(Spacer(1, 2))
                last_was_blank = True
            continue
        last_was_blank = False

        if _is_section_header(stripped):
            current_section = stripped.rstrip(":-–— \t").lower()
            heading_text = stripped.rstrip(":-–— \t").upper()
            story.append(Paragraph(esc(heading_text), heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor(accent_color if template == "classic" else INK_500), spaceAfter=2))
            continue

        # Check for title/institution/company line with right-aligned date
        cleaned = _clean_title_and_date(stripped)
        if cleaned:
            title_str, date_str = cleaned
            col_w1 = usable_width * 0.72
            col_w2 = usable_width * 0.28
            tbl = Table(
                [[Paragraph(esc(title_str), subhead_left), Paragraph(esc(date_str), subhead_right)]],
                colWidths=[col_w1, col_w2],
                hAlign='LEFT',
            )
            tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (1, 0), (1, -1), 6),  # Inset date cleanly inside border
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))
            story.append(tbl)
            continue

        # Check for tech stack line in projects/experience
        if _is_tech_stack_line(stripped):
            story.append(Paragraph(esc(stripped), tech_stack_style))
            continue

        # Check for skills category lines: e.g. "Languages: Python, Java, C++"
        if _is_skill_category(stripped):
            parts = stripped.split(":", 1)
            prefix = esc(parts[0].strip())
            rest = esc(parts[1].strip())
            story.append(Paragraph(f"<b>{prefix}:</b> {rest}", body_style))
            continue

        # Check for explicit bullet point prefix
        if _BULLET_PREFIX_RE.match(stripped):
            text = _BULLET_PREFIX_RE.sub("", stripped)
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{esc(text)}", bullet_style))
            continue

        # Check for institution in education section
        if "education" in current_section:
            story.append(Paragraph(esc(stripped), institution_style))
            continue

        # Pointwise bullet rendering for project and experience descriptions
        is_bullet_section = any(k in current_section for k in ("project", "experience", "internship", "achievement", "leadership", "activity"))
        if is_bullet_section and not _is_title_and_date(stripped):
            bullets = _split_into_bullet_points(stripped)
            for b in bullets:
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;{esc(b)}", bullet_style))
            continue

        story.append(Paragraph(esc(stripped), body_style))

    doc.build(story)
    return buffer.getvalue()


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

    personal = parsed_data.get("personal", {}) or {}
    name = personal.get("name") or candidate_name or "Candidate"
    contacts = []
    if personal.get("location"):
        contacts.append(personal["location"])
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
        r_contact = p_contact.add_run(" • ".join(contacts))
        r_contact.font.size = Pt(8.5)
        _set_run_color(r_contact, INK_700)

    def add_section_header(title: str):
        p_head = document.add_paragraph()
        p_head.paragraph_format.space_before = Pt(9)
        p_head.paragraph_format.space_after = Pt(2)
        p_head.paragraph_format.keep_with_next = True
        r_head = p_head.add_run(title.upper())
        r_head.bold = True
        r_head.font.size = Pt(10)
        _set_run_color(r_head, accent_color)
        _add_bottom_border(p_head, accent_color)

    # 1. Summary
    summary = parsed_data.get("summary")
    if summary and summary.strip():
        add_section_header("Professional Summary")
        p_sum = document.add_paragraph()
        p_sum.paragraph_format.space_before = Pt(0)
        p_sum.paragraph_format.space_after = Pt(2)
        r_sum = p_sum.add_run(summary.strip())
        r_sum.font.size = Pt(8.5)

    # 2. Skills
    skills = parsed_data.get("skills", [])
    if skills:
        add_section_header("Technical Skills")
        p_sk = document.add_paragraph()
        p_sk.paragraph_format.space_before = Pt(0)
        p_sk.paragraph_format.space_after = Pt(2)
        sk_text = ", ".join(str(s) for s in skills if s) if isinstance(skills, list) else str(skills)
        r_sk = p_sk.add_run(sk_text)
        r_sk.font.size = Pt(8.5)

    # 3. Experience
    exp = parsed_data.get("experience_raw", [])
    if exp:
        add_section_header("Work Experience")
        for item in exp:
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

    # 4. Projects
    proj = parsed_data.get("projects_raw", [])
    if proj:
        add_section_header("Projects")
        for item in proj:
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

    # 5. Education
    edu = parsed_data.get("education_raw", [])
    if edu:
        add_section_header("Education")
        for item in edu:
            item_str = str(item).strip()
            if not item_str:
                continue
            sub_lines = [l.strip() for l in item_str.split("\n") if l.strip()]
            for sub_idx, sub_clean in enumerate(sub_lines):
                p_ed = document.add_paragraph()
                p_ed.paragraph_format.space_before = Pt(0)
                p_ed.paragraph_format.space_after = Pt(1)
                r_ed = p_ed.add_run(sub_clean)
                r_ed.font.size = Pt(8.5)
                if sub_idx == 0 and len(sub_lines) > 1:
                    r_ed.bold = True

    # 6. Certifications
    certs = parsed_data.get("certifications", [])
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

    # 7. Achievements
    ach = parsed_data.get("achievements", [])
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

    # 8. Languages
    langs = parsed_data.get("languages", [])
    if langs:
        add_section_header("Languages")
        p_lang = document.add_paragraph()
        p_lang.paragraph_format.space_before = Pt(0)
        p_lang.paragraph_format.space_after = Pt(2)
        lang_text = ", ".join(str(l) for l in langs if l) if isinstance(langs, list) else str(langs)
        r_lang = p_lang.add_run(lang_text)
        r_lang.font.size = Pt(8.5)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def generate_docx(content: str | dict, candidate_name: str = "", template: str = "modern", experience_level: str = "fresher") -> bytes:
    if isinstance(content, dict):
        return render_docx_from_structured(content, candidate_name=candidate_name, template=template)

    resume_text = _sanitize_text(str(content))
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

    name, contact_lines, body_lines = _split_name_contact_body(resume_text)
    if not name and candidate_name:
        name = candidate_name
        
    body_lines = _merge_standalone_dates(body_lines)
    body_lines = _merge_hard_wrapped_lines(body_lines)

    if name:
        p_name = document.add_paragraph()
        p_name.alignment = alignment
        p_name.paragraph_format.space_before = Pt(0)
        p_name.paragraph_format.space_after = Pt(1)
        r_name = p_name.add_run(name)
        r_name.bold = True
        r_name.font.size = Pt(15)
        _set_run_color(r_name, INK_900)

    if contact_lines:
        p_contact = document.add_paragraph()
        p_contact.alignment = alignment
        p_contact.paragraph_format.space_before = Pt(0)
        p_contact.paragraph_format.space_after = Pt(3)
        formatted_contacts = " • ".join(c.strip(" •·|") for c in contact_lines if c.strip())
        r_contact = p_contact.add_run(formatted_contacts)
        r_contact.font.size = Pt(8.5)
        _set_run_color(r_contact, INK_700)

    current_section = ""
    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _is_section_header(stripped):
            current_section = stripped.rstrip(":-–— \t").lower()
            p_head = document.add_paragraph()
            p_head.paragraph_format.space_before = Pt(9)
            p_head.paragraph_format.space_after = Pt(2)
            p_head.paragraph_format.keep_with_next = True
            r_head = p_head.add_run(stripped.rstrip(":-–— \t").upper())
            r_head.bold = True
            r_head.font.size = Pt(10)
            _set_run_color(r_head, accent_color)
            _add_bottom_border(p_head, accent_color)
            continue

        cleaned = _clean_title_and_date(stripped)
        if cleaned:
            title_str, date_str = cleaned
            p_sub = document.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(1.5)
            p_sub.paragraph_format.space_after = Pt(1)
            # Add right-aligned tab stop at 7.3 inches (matching right margin)
            p_sub.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
            r1 = p_sub.add_run(title_str)
            r1.bold = True
            r1.font.size = Pt(8.5)
            _set_run_color(r1, INK_900)

            r2 = p_sub.add_run(f"\t{date_str}")
            r2.bold = True if template in ("classic", "harvard") else False
            r2.font.size = Pt(8.5)
            _set_run_color(r2, INK_700)
            continue


        if _is_tech_stack_line(stripped):
            p_tech = document.add_paragraph()
            p_tech.paragraph_format.space_before = Pt(0)
            p_tech.paragraph_format.space_after = Pt(2)
            r_tech = p_tech.add_run(stripped)
            r_tech.italic = True
            r_tech.font.size = Pt(8.0)
            _set_run_color(r_tech, INK_700)
            continue

        if _is_skill_category(stripped):
            parts = stripped.split(":", 1)
            p_line = document.add_paragraph()
            p_line.paragraph_format.space_before = Pt(0)
            p_line.paragraph_format.space_after = Pt(1)
            r_pre = p_line.add_run(parts[0].strip() + ": ")
            r_pre.bold = True
            r_pre.font.size = Pt(8.5)
            _set_run_color(r_pre, INK_900)

            r_rest = p_line.add_run(parts[1].strip())
            r_rest.font.size = Pt(8.5)
            _set_run_color(r_rest, INK_900)
            continue

        # Check for explicit bullet prefix
        if _BULLET_PREFIX_RE.match(stripped):
            text = _BULLET_PREFIX_RE.sub("", stripped)
            p_b = document.add_paragraph(style="List Bullet")
            p_b.paragraph_format.space_before = Pt(0)
            p_b.paragraph_format.space_after = Pt(1)
            p_b.paragraph_format.left_indent = Inches(0.2)
            r_b = p_b.add_run(text)
            r_b.font.size = Pt(8.5)
            _set_run_color(r_b, INK_900)
            continue

        if "education" in current_section:
            p_inst = document.add_paragraph()
            p_inst.paragraph_format.space_before = Pt(0)
            p_inst.paragraph_format.space_after = Pt(2)
            r_inst = p_inst.add_run(stripped)
            r_inst.font.size = Pt(8.5)
            _set_run_color(r_inst, INK_700)
            continue

        is_bullet_section = any(k in current_section for k in ("project", "experience", "internship", "achievement", "leadership", "activity"))
        if is_bullet_section and not _is_title_and_date(stripped):
            bullets = _split_into_bullet_points(stripped)
            for b in bullets:
                p_b = document.add_paragraph(style="List Bullet")
                p_b.paragraph_format.space_before = Pt(0)
                p_b.paragraph_format.space_after = Pt(1)
                p_b.paragraph_format.left_indent = Inches(0.2)
                r_b = p_b.add_run(b)
                r_b.font.size = Pt(8.5)
                _set_run_color(r_b, INK_900)
            continue

        p_line = document.add_paragraph()
        p_line.paragraph_format.space_before = Pt(0)
        p_line.paragraph_format.space_after = Pt(1)
        r_line = p_line.add_run(stripped)
        r_line.font.size = Pt(8.5)
        _set_run_color(r_line, INK_900)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def measure_pdf_page_count(pdf_bytes: bytes) -> int:
    """Measures the exact page count of a PDF byte stream using PyMuPDF."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = doc.page_count
    doc.close()
    return count
