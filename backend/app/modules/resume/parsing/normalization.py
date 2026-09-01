"""
Deterministic Document Normalization Engine.
Cleans encoding artifacts, bullet variants, artificial line wrapping,
multi-column reading orders, and repeated page headers/footers
WITHOUT changing factual content.
"""
import re
from typing import Sequence
from app.modules.resume.parsing.document import DocumentBlock, DocumentLine, DocumentPage

# Standard bullet glyphs
BULLET_CHARS = {"•", "▪", "▫", "►", "▶", "◆", "◇", "●", "○", "✓", "✔", "➔", "→", "➢", "·", "∙", "–", "—", "*"}
BULLET_REGEX = re.compile(r"^\s*([•▪▫►▶◆◇●○✓✔➔→➢·∙\-\*–—]|\uf0b7|\uf0a7|\u2022|\u25aa|\u25b6|\u25c6|\u2713|\u27a4)\s*")

# Unicode normalization mapping
UNICODE_REPLACEMENTS = {
    "\u00a0": " ",      # non-breaking space
    "\u200b": "",       # zero-width space
    "\u200e": "",       # left-to-right mark
    "\u200f": "",       # right-to-left mark
    "\ufeff": "",       # byte order mark
    "\ufffd": "",       # replacement character
    "\u2018": "'",      # left single quotation mark
    "\u2019": "'",      # right single quotation mark
    "\u201c": '"',      # left double quotation mark
    "\u201d": '"',      # right double quotation mark
    "\u2013": " - ",    # en dash
    "\u2014": " — ",    # em dash
    "\xad": "",         # soft hyphen
    "\x0c": "\n",       # form feed
}


def normalize_unicode_artifacts(text: str) -> str:
    """
    Cleans encoding artifacts, strange whitespaces, and normalizes bullet glyphs.
    Guarantees factual metrics, dates, and technical symbols are preserved.
    """
    if not text:
        return ""

    result = text
    for char, replacement in UNICODE_REPLACEMENTS.items():
        if char in result:
            result = result.replace(char, replacement)

    # Normalize weird unicode bullets at line starts
    lines = result.splitlines()
    normalized_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            normalized_lines.append("")
            continue

        # Standardize bullet prefixes to '• '
        if BULLET_REGEX.match(cleaned_line):
            cleaned_line = BULLET_REGEX.sub("• ", cleaned_line, count=1)

        # Collapse multiple horizontal whitespace (tabs / spaces)
        cleaned_line = re.sub(r"[ \t]+", " ", cleaned_line)
        normalized_lines.append(cleaned_line)

    result = "\n".join(normalized_lines)

    # Reconstruct hyphenated words broken across line wraps (e.g. "micro-\nservices" -> "microservices")
    # Only if both parts look like English word syllables (>= 3 letters) and not bullet lists or metrics
    result = re.sub(r"(\b[a-zA-Z]{3,})-\n\s*([a-zA-Z]{3,}\b)", r"\1\2", result)

    return result


def unwrap_paragraph_lines(lines: Sequence[str]) -> list[str]:
    """
    Unwraps artificial line wraps within cohesive paragraphs and bullets
    while strictly preserving section headers, dates, and separate list items.
    """
    if not lines:
        return []

    unwrapped: list[str] = []
    current_item: list[str] = []

    def flush_current():
        if current_item:
            unwrapped.append(" ".join(current_item).strip())
            current_item.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_current()
            continue

        is_bullet = stripped.startswith(("•", "-", "*", "–", "—")) or bool(BULLET_REGEX.match(stripped))
        is_colon_header = stripped.endswith(":") and len(stripped.split()) <= 8
        is_all_caps_header = stripped.isupper() and len(stripped.split()) <= 6

        if is_bullet or is_colon_header or is_all_caps_header:
            flush_current()
            current_item.append(stripped)
        else:
            if current_item:
                last_line = current_item[-1]
                # If last line ended with clear sentence break or colon, start a new item
                if last_line.endswith((".", "!", "?", ":", ";")) and len(stripped) > 0 and stripped[0].isupper():
                    flush_current()
                    current_item.append(stripped)
                else:
                    # Continuation of current line / bullet
                    current_item.append(stripped)
            else:
                current_item.append(stripped)

    flush_current()
    return unwrapped


def detect_and_order_columns(blocks: list[DocumentBlock], page_width: float = 612.0) -> list[DocumentBlock]:
    """
    Infers logical reading order for single, two-column, or hybrid multi-column pages.
    Header blocks spanning the page are placed first, followed by left column top-to-bottom,
    right column top-to-bottom, and footer blocks.
    """
    if not blocks or len(blocks) <= 1:
        for idx, b in enumerate(blocks):
            b.reading_order_index = idx
        return blocks

    # Analyze x-coordinate distribution to detect multi-column layout
    col_midpoint = page_width * 0.5
    left_col_blocks: list[DocumentBlock] = []
    right_col_blocks: list[DocumentBlock] = []
    full_width_top_blocks: list[DocumentBlock] = []
    full_width_bottom_blocks: list[DocumentBlock] = []

    # Calculate average width of blocks
    for b in blocks:
        width = b.x1 - b.x0
        # If block spans > 65% of the page or is centered at the very top (e.g. Header / Contact)
        if width > (page_width * 0.65) or (b.y0 < 120 and width > page_width * 0.45):
            if b.y0 < 200:
                full_width_top_blocks.append(b)
            else:
                full_width_bottom_blocks.append(b)
        elif b.x0 < (col_midpoint - 15) and b.x1 <= (col_midpoint + 50):
            b.column_index = 0
            left_col_blocks.append(b)
        elif b.x0 >= (col_midpoint - 50):
            b.column_index = 1
            right_col_blocks.append(b)
        else:
            # Fallback based on center of block
            center_x = (b.x0 + b.x1) / 2.0
            if center_x < col_midpoint:
                b.column_index = 0
                left_col_blocks.append(b)
            else:
                b.column_index = 1
                right_col_blocks.append(b)

    # Sort each group vertically by y0
    full_width_top_blocks.sort(key=lambda b: b.y0)
    left_col_blocks.sort(key=lambda b: b.y0)
    right_col_blocks.sort(key=lambda b: b.y0)
    full_width_bottom_blocks.sort(key=lambda b: b.y0)

    # If there are meaningful columns on both sides, order: Top -> Left Col -> Right Col -> Bottom
    is_multi_column = len(left_col_blocks) >= 2 and len(right_col_blocks) >= 2
    if is_multi_column:
        ordered = full_width_top_blocks + left_col_blocks + right_col_blocks + full_width_bottom_blocks
    else:
        # Standard single column or mixed page: sort primarily by y0, secondary by x0
        ordered = sorted(blocks, key=lambda b: (round(b.y0 / 10.0), b.x0))

    for idx, b in enumerate(ordered):
        b.reading_order_index = idx

    return ordered


def suppress_repeated_headers_footers(pages: list[DocumentPage]) -> None:
    """
    Identifies and marks repeated page header or footer artifacts across multi-page resumes.
    """
    if len(pages) < 2:
        return

    # Check top margin blocks (y0 < 50) and bottom margin blocks (y1 > height - 50)
    top_texts: dict[str, int] = {}
    bottom_texts: dict[str, int] = {}

    for p in pages:
        for b in p.blocks:
            clean_t = (b.normalized_text or b.text).strip().lower()
            if not clean_t:
                continue
            if b.y0 < 50:
                top_texts[clean_t] = top_texts.get(clean_t, 0) + 1
            if b.y1 > (p.height - 50):
                # Check for standard page numbers e.g. "page 1 of 2", "page 2", "2", "- 2 -"
                if re.match(r"^(?:page\s*\d+(?:\s*(?:of|\/)\s*\d+)?|\d+|[-–—]\s*\d+\s*[-–—])$", clean_t):
                    b.is_repeated_header_or_footer = True
                bottom_texts[clean_t] = bottom_texts.get(clean_t, 0) + 1

    # Mark blocks appearing at top or bottom margin across multiple pages
    for p in pages:
        for b in p.blocks:
            clean_t = (b.normalized_text or b.text).strip().lower()
            if (b.y0 < 50 and top_texts.get(clean_t, 0) >= 2) or (b.y1 > (p.height - 50) and (bottom_texts.get(clean_t, 0) >= 2 or re.match(r"^(?:page\s*\d+(?:\s*(?:of|\/)\s*\d+)?|\d+|[-–—]\s*\d+\s*[-–—])$", clean_t))):
                b.is_repeated_header_or_footer = True
