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


def _cluster_x0_values(x0_values: list[float], gap_threshold: float) -> list[list[float]]:
    """
    Groups a sorted list of x0 values into clusters separated by at least gap_threshold pixels.
    Returns a list of clusters, each cluster being a list of x0 values.
    """
    if not x0_values:
        return []
    sorted_vals = sorted(x0_values)
    clusters: list[list[float]] = [[sorted_vals[0]]]
    for val in sorted_vals[1:]:
        if val - clusters[-1][-1] >= gap_threshold:
            clusters.append([])
        clusters[-1].append(val)
    return clusters


def _vertical_overlap_fraction(blocks_a: list[DocumentBlock], blocks_b: list[DocumentBlock]) -> float:
    """
    Computes the fraction of the shorter group's vertical span that overlaps with the other group.
    Returns 0.0 if there is no overlap, 1.0 if fully contained.
    """
    if not blocks_a or not blocks_b:
        return 0.0
    a_y0 = min(b.y0 for b in blocks_a)
    a_y1 = max(b.y1 for b in blocks_a)
    b_y0 = min(b.y0 for b in blocks_b)
    b_y1 = max(b.y1 for b in blocks_b)
    overlap_start = max(a_y0, b_y0)
    overlap_end = min(a_y1, b_y1)
    overlap = max(0.0, overlap_end - overlap_start)
    shorter_height = min(a_y1 - a_y0, b_y1 - b_y0)
    if shorter_height <= 0:
        return 0.0
    return overlap / shorter_height


# ── Geometry constants for genuine-column detection ───────────────────────────
# None of these values are document-specific; they are structural thresholds
# derived from standard typographic conventions and tested across layout classes.

# A block whose width exceeds this fraction of the page is unconditionally full-width.
_FULL_WIDTH_RATIO: float = 0.70

# Minimum pixel gap between the rightmost x1 of the left cluster and the
# leftmost x0 of the right cluster for a genuine inter-column gutter to exist.
_MIN_COLUMN_GAP_PX: float = 50.0

# The right column must start past this fraction of the page width.
# Prevents narrow left-margin labels from being treated as a left column
# alongside a wide-body "right column".
_RIGHT_COL_START_RATIO: float = 0.38

# Each candidate column must have at least this many blocks.
_MIN_BLOCKS_PER_COLUMN: int = 2

# The two column groups must share at least this fraction of the shorter
# group's vertical span. Hanging headers (above their body text) produce ~0.
_MIN_VERTICAL_OVERLAP_RATIO: float = 0.15

# One column cannot be more than this many times taller than the other.
# Prevents a short sidebar from triggering two-column mode on a long page.
_MAX_HEIGHT_RATIO: float = 5.0

# Pixel gap in x0 space that separates two distinct indentation clusters.
_X0_CLUSTER_GAP: float = 50.0

# Vertical band height used when sorting blocks in single-column mode.
# Blocks within the same band are treated as being on the same visual row.
_SORT_BAND_PX: float = 8.0
# ─────────────────────────────────────────────────────────────────────────────


def detect_and_order_columns(blocks: list[DocumentBlock], page_width: float = 612.0) -> list[DocumentBlock]:
    """
    Infers the natural reading order of blocks on a single PDF page using
    a document-geometry-only algorithm that supports:

      - Genuine single-column resumes
      - Genuine two-column resumes (skills sidebar + experience main body)
      - Indented section headings (narrow heading, wide body, same stream)
      - Hanging headers (heading starts at a different x than body text)
      - Multi-line headings split across consecutive blocks
      - Blocks with varying x-positions that belong to the same stream
      - Mixed-width blocks within the same semantic section
      - Full-width contact / header blocks at the top of the page

    The algorithm evaluates five independent geometry gates to decide whether
    genuine side-by-side columns exist.  ALL five gates must pass for
    two-column reading order to be applied.  If any gate fails the page is
    treated as a single reading stream and blocks are sorted by vertical band
    then by x0 within each band.

    No NLP, no semantic parsing, and no document-specific strings are used.
    All thresholds are structural typographic constants.

    Args:
        blocks:     All DocumentBlock objects for this page in extraction order.
        page_width: Physical page width in points (default 612 = US Letter).

    Returns:
        The same list of blocks with reading_order_index assigned and sorted
        into the inferred reading order.  Block geometry (bbox) is never modified.
    """
    if not blocks or len(blocks) <= 1:
        for idx, b in enumerate(blocks):
            b.reading_order_index = idx
        return blocks

    # ── Step 1: Separate unconditional full-width blocks ─────────────────────
    # A block is full-width if its width exceeds _FULL_WIDTH_RATIO of the page.
    # These are always emitted in the shared vertical stream regardless of column
    # detection outcome (name, contact bar, horizontal rules, wide summary).
    full_width_top: list[DocumentBlock] = []
    full_width_bottom_thresh = 200.0   # y0 below which a block is "bottom"
    full_width_bottom: list[DocumentBlock] = []
    candidate_blocks: list[DocumentBlock] = []

    for b in blocks:
        width = b.x1 - b.x0
        if width >= _FULL_WIDTH_RATIO * page_width:
            if b.y0 < full_width_bottom_thresh:
                full_width_top.append(b)
            else:
                full_width_bottom.append(b)
        else:
            candidate_blocks.append(b)

    # If no candidates remain (all blocks are full-width), sort by y0 and return.
    if not candidate_blocks:
        all_sorted = sorted(blocks, key=lambda b: (round(b.y0 / _SORT_BAND_PX), b.x0))
        for idx, b in enumerate(all_sorted):
            b.reading_order_index = idx
        return all_sorted

    # ── Step 2: Find x0 indentation clusters among candidate blocks ──────────
    # Gap-based 1D clustering on x0 values discovers the actual indentation
    # levels used in this document without any prior knowledge of its margins.
    candidate_x0s = [b.x0 for b in candidate_blocks]
    x0_clusters = _cluster_x0_values(candidate_x0s, gap_threshold=_X0_CLUSTER_GAP)

    # ── Step 3: Determine whether two genuine side-by-side columns exist ─────
    # Assign each candidate block to the indentation cluster whose centroid is
    # closest to its x0.  Then evaluate five geometry gates.

    is_genuine_two_column = False
    left_col: list[DocumentBlock] = []
    right_col: list[DocumentBlock] = []

    # We only attempt two-column detection when exactly two dominant x0 clusters exist.
    # "Dominant" = each cluster has at least _MIN_BLOCKS_PER_COLUMN blocks.
    if len(x0_clusters) >= 2:
        # Sort clusters by their mean x0 to get left / right candidates.
        cluster_means = [sum(c) / len(c) for c in x0_clusters]
        sorted_cluster_indices = sorted(range(len(x0_clusters)), key=lambda i: cluster_means[i])

        # Identify the two candidate column clusters.
        # For pages with more than two clusters (multiple indentation levels)
        # we compare the leftmost and rightmost clusters as the column candidates.
        left_ci = sorted_cluster_indices[0]
        right_ci = sorted_cluster_indices[-1]

        left_x0_mean = cluster_means[left_ci]
        right_x0_mean = cluster_means[right_ci]

        # Assign blocks to left/right candidate columns based on nearest cluster mean.
        for b in candidate_blocks:
            dist_left = abs(b.x0 - left_x0_mean)
            dist_right = abs(b.x0 - right_x0_mean)
            if dist_left <= dist_right:
                left_col.append(b)
            else:
                right_col.append(b)

        # Gate 1 — x0 cluster separation: the two clusters must be far enough apart.
        # This passes for genuine two-column docs (large gutter) and fails for
        # documents with only minor indentation differences.
        left_x1_max = max((b.x1 for b in left_col), default=0.0)
        right_x0_min = min((b.x0 for b in right_col), default=page_width)
        gate_gap = (right_x0_min - left_x1_max) >= _MIN_COLUMN_GAP_PX

        # Gate 2 — right column must start well into the page.
        # In indented-heading layouts the "right column" (body text) starts at
        # a moderate x0 (e.g. 144 px on a 612 px page = 23% of width).
        # Genuine right columns start much further right (> 38% of page width).
        gate_right_position = right_x0_mean >= (_RIGHT_COL_START_RATIO * page_width)

        # Gate 3 — minimum block population per column.
        gate_population = (
            len(left_col) >= _MIN_BLOCKS_PER_COLUMN
            and len(right_col) >= _MIN_BLOCKS_PER_COLUMN
        )

        # Gate 4 — vertical height balance between columns.
        # A genuine two-column layout has broadly comparable column heights.
        # A sidebar of two labels vs. a main body of 20 blocks is not two-column.
        if left_col and right_col:
            left_height = max(b.y1 for b in left_col) - min(b.y0 for b in left_col)
            right_height = max(b.y1 for b in right_col) - min(b.y0 for b in right_col)
            taller = max(left_height, right_height)
            shorter = min(left_height, right_height)
            gate_balance = shorter > 0 and (taller / shorter) <= _MAX_HEIGHT_RATIO
        else:
            gate_balance = False

        # Gate 5 — vertical overlap between the two groups.
        # In a genuine two-column layout the left and right blocks occupy the
        # SAME vertical region (they are side-by-side).  In an indented-heading
        # layout the narrow heading blocks appear ABOVE their body text — their
        # y-ranges do not meaningfully overlap.
        overlap = _vertical_overlap_fraction(left_col, right_col)
        gate_overlap = overlap >= _MIN_VERTICAL_OVERLAP_RATIO

        is_genuine_two_column = (
            gate_gap
            and gate_right_position
            and gate_population
            and gate_balance
            and gate_overlap
        )

    # ── Step 4: Assign column_index on blocks ─────────────────────────────────
    if is_genuine_two_column:
        for b in left_col:
            b.column_index = 0
        for b in right_col:
            b.column_index = 1
    else:
        # Single-column / indented layout: all blocks belong to column 0.
        for b in candidate_blocks:
            b.column_index = 0

    # ── Step 5: Build final reading order ─────────────────────────────────────
    full_width_top.sort(key=lambda b: b.y0)
    full_width_bottom.sort(key=lambda b: b.y0)

    if is_genuine_two_column:
        left_col.sort(key=lambda b: b.y0)
        right_col.sort(key=lambda b: b.y0)
        ordered = full_width_top + left_col + right_col + full_width_bottom
    else:
        # Sort all blocks (full-width and candidates together) by vertical band
        # then by x0 within each band so blocks at the same visual row are adjacent.
        all_blocks = full_width_top + candidate_blocks + full_width_bottom
        ordered = sorted(all_blocks, key=lambda b: (round(b.y0 / _SORT_BAND_PX), b.x0))

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
