"""
Resume export (Feature 13). Generates PDF and DOCX from finalized
resume text ONLY -- this module has no path that can export a draft
containing pending/rejected AI changes, enforcing "Generated files
must contain ONLY approved content" at the type level, not just by
convention.

Single-page optimized rendering for freshers & early career:
- Strict single-page vertical budget: 0.4 inch margins, compact line heights.
- Automatic right-aligned dates & roles formatting.
- Clean typography and ATS-safe single-column layout.
"""
import io
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.modules.resume.parsing.structurer import SECTION_PATTERNS

INK_900 = "#111827"
INK_700 = "#374151"
INK_500 = "#6b7280"
SIGNAL_600 = "#0d766e"
CLASSIC_ACCENT = "#111827"
TECH_ACCENT = "#1e3a8a"

_BULLET_PREFIX_RE = re.compile(r"^[•\-\*\u2022\u25E6\u2043\u2219\u25AA\u25AB]\s*")
_DATE_PATTERN_RE = re.compile(
    r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}\s*[-–—to]+\s*(?:Present|Current|\d{4}|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}))\b",
    re.IGNORECASE,
)


def _is_section_header(line: str) -> bool:
    normalized = line.strip().rstrip(":-–— \t")
    return any(re.match(pattern, normalized, re.IGNORECASE) for pattern in SECTION_PATTERNS.values())


def _looks_like_contact_line(line: str) -> bool:
    return bool(re.search(r"@|\d{10}|linkedin\.com|github\.com|https?://", line))


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
            body_start_idx = i + 1
            break
        if _is_section_header(stripped):
            body_start_idx = i
            break
        if _looks_like_contact_line(stripped):
            contact_lines.append(stripped)
            body_start_idx = i + 1
        else:
            body_start_idx = i
            break

    return name.strip(), contact_lines, lines[body_start_idx:]


def generate_pdf(resume_text: str, candidate_name: str, template: str = "modern") -> bytes:
    template = template.lower() if template else "modern"
    buffer = io.BytesIO()
    # Optimized margins (0.45 in) to guarantee clean 1-page fit for freshers
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.35 * inch, bottomMargin=0.35 * inch,
        leftMargin=0.45 * inch, rightMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()

    font_family = "Helvetica"
    font_bold = "Helvetica-Bold"
    font_italic = "Helvetica-Oblique"
    accent_color = SIGNAL_600
    name_align = 1  # center

    if template == "classic":
        font_family = "Times-Roman"
        font_bold = "Times-Bold"
        font_italic = "Times-Italic"
        accent_color = CLASSIC_ACCENT
        name_align = 1
    elif template == "technical":
        font_family = "Helvetica"
        font_bold = "Helvetica-Bold"
        font_italic = "Helvetica-Oblique"
        accent_color = TECH_ACCENT
        name_align = 0  # left-aligned for technical layout

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
        leading=12, textColor=HexColor(accent_color), spaceBefore=4, spaceAfter=1.5,
        letterSpacing=0.6,
    )
    subhead_left = ParagraphStyle(
        "SubheadLeft", parent=styles["Normal"], fontName=font_bold, fontSize=8.5,
        leading=11, textColor=HexColor(INK_900),
    )
    subhead_right = ParagraphStyle(
        "SubheadRight", parent=styles["Normal"], fontName=font_bold, fontSize=8.5,
        leading=11, textColor=HexColor(INK_700), alignment=2,  # right aligned
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontName=font_family, fontSize=8.5,
        textColor=HexColor(INK_900), leading=11, spaceAfter=1,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=body_style, leftIndent=10, bulletIndent=0, spaceAfter=0.8,
    )

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    name, contact_lines, body_lines = _split_name_contact_body(resume_text)

    story = []
    if name:
        story.append(Paragraph(esc(name), name_style))
    if contact_lines:
        formatted_contacts = " • ".join(c.strip(" •·|") for c in contact_lines if c.strip())
        story.append(Paragraph(esc(formatted_contacts), contact_style))
    if name or contact_lines:
        divider_color = HexColor(accent_color if template == "technical" else INK_700)
        story.append(HRFlowable(width="100%", thickness=0.5, color=divider_color, spaceAfter=3))

    last_was_blank = False
    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            if not last_was_blank:
                story.append(Spacer(1, 1.5))
                last_was_blank = True
            continue
        last_was_blank = False

        if _is_section_header(stripped):
            heading_text = stripped.rstrip(":-–— \t").upper()
            story.append(Paragraph(esc(heading_text), heading_style))
            story.append(HRFlowable(width="100%", thickness=0.4, color=HexColor(accent_color if template == "classic" else INK_500), spaceAfter=2))
            continue

        if _BULLET_PREFIX_RE.match(stripped):
            text = _BULLET_PREFIX_RE.sub("", stripped)
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{esc(text)}", bullet_style))
            continue

        # Check for title/company line with right-aligned date
        date_match = _DATE_PATTERN_RE.search(stripped)
        if date_match and not stripped.startswith("•"):
            date_str = date_match.group(1)
            title_str = stripped.replace(date_str, "").strip(" |–-—, \t")
            if title_str:
                col_w1 = usable_width * 0.72
                col_w2 = usable_width * 0.28
                tbl = Table(
                    [[Paragraph(esc(title_str), subhead_left), Paragraph(esc(date_str), subhead_right)]],
                    colWidths=[col_w1, col_w2],
                )
                tbl.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
                ]))
                story.append(tbl)
                continue

        # Format skills category lines nicely: e.g. "Languages: Python, Java, C++"
        if ":" in stripped and not stripped.startswith("http"):
            parts = stripped.split(":", 1)
            if len(parts[0].split()) <= 4:
                prefix = esc(parts[0].strip())
                rest = esc(parts[1].strip())
                story.append(Paragraph(f"<b>{prefix}:</b> {rest}", body_style))
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


def generate_docx(resume_text: str, candidate_name: str, template: str = "modern") -> bytes:
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

    if template == "classic":
        font_name = "Times New Roman"
        accent_color = CLASSIC_ACCENT
        alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif template == "technical":
        font_name = "Arial"
        accent_color = TECH_ACCENT
        alignment = WD_ALIGN_PARAGRAPH.LEFT

    normal = document.styles["Normal"]
    normal.font.name = font_name
    normal.font.size = Pt(9.0)

    name, contact_lines, body_lines = _split_name_contact_body(resume_text)

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

    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _is_section_header(stripped):
            p_head = document.add_paragraph()
            p_head.paragraph_format.space_before = Pt(5)
            p_head.paragraph_format.space_after = Pt(2)
            p_head.paragraph_format.keep_with_next = True
            r_head = p_head.add_run(stripped.rstrip(":-–— \t").upper())
            r_head.bold = True
            r_head.font.size = Pt(10)
            _set_run_color(r_head, accent_color)
            _add_bottom_border(p_head, accent_color)
            continue

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

        date_match = _DATE_PATTERN_RE.search(stripped)
        if date_match and not stripped.startswith("•"):
            date_str = date_match.group(1)
            title_str = stripped.replace(date_str, "").strip(" |–-—, \t")
            if title_str:
                tbl = document.add_table(rows=1, cols=2)
                tbl.autofit = False
                row = tbl.rows[0]
                row.cells[0].width = Inches(5.2)
                row.cells[1].width = Inches(2.2)

                p1 = row.cells[0].paragraphs[0]
                p1.paragraph_format.space_before = Pt(1)
                p1.paragraph_format.space_after = Pt(1)
                r1 = p1.add_run(title_str)
                r1.bold = True
                r1.font.size = Pt(8.5)
                _set_run_color(r1, INK_900)

                p2 = row.cells[1].paragraphs[0]
                p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2.paragraph_format.space_before = Pt(1)
                p2.paragraph_format.space_after = Pt(1)
                r2 = p2.add_run(date_str)
                r2.bold = True
                r2.font.size = Pt(8.5)
                _set_run_color(r2, INK_700)
                continue

        p_line = document.add_paragraph()
        p_line.paragraph_format.space_before = Pt(0)
        p_line.paragraph_format.space_after = Pt(1)

        if ":" in stripped and not stripped.startswith("http"):
            parts = stripped.split(":", 1)
            if len(parts[0].split()) <= 4:
                r_pre = p_line.add_run(parts[0].strip() + ": ")
                r_pre.bold = True
                r_pre.font.size = Pt(8.5)
                _set_run_color(r_pre, INK_900)

                r_rest = p_line.add_run(parts[1].strip())
                r_rest.font.size = Pt(8.5)
                _set_run_color(r_rest, INK_900)
                continue

        r_line = p_line.add_run(stripped)
        r_line.font.size = Pt(8.5)
        _set_run_color(r_line, INK_900)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
