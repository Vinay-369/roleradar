"""
Phase 1 Validation Audit — Boundary Case Test Suite
====================================================
Generalized tests for boundary and edge cases NOT covered by the original
Phase 1 test suite. This file is read-only validation; it does NOT fix anything.

Tests added:
  A. A4 page dimensions
  B. Letter page (verify constants scale correctly)
  C. Narrow two-column gutter (30px < 50px threshold → should fallback)
  D. Wide two-column gutter (120px → should detect columns)
  E. Asymmetric column heights — 5:1 ratio at _MAX_HEIGHT_RATIO boundary
  F. Sparse sidebar — exactly _MIN_BLOCKS_PER_COLUMN blocks each
  G. Two-column layout beginning below a full-width header (header at top)
  H. Full-width block in the middle of a two-column layout → KNOWN LIMITATION
  I. Single-column layout with deep (250px) indentation → FAILURE CASE
  J. Multiple indentation levels (3 clusters — leftmost vs rightmost)
  K. Different page widths (letter vs A4 vs legal vs custom)
  L. Multi-page mixed layouts (single page 1, two-col page 2)

For each test, _check_invariants() verifies:
  - No blocks lost
  - No blocks duplicated
  - Block text unchanged
  - Block bbox unchanged
  - Block page preserved
  - reading_order_index is contiguous 0-based
  - column_index is 0 or 1 only
"""
import pytest

from app.modules.resume.parsing.document import DocumentBlock, DocumentPage
from app.modules.resume.parsing.normalization import (
    detect_and_order_columns,
    suppress_repeated_headers_footers,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mb(bid: str, page: int, text: str, x0: float, y0: float, x1: float, y1: float) -> DocumentBlock:
    return DocumentBlock(id=bid, page=page, text=text, bbox=(x0, y0, x1, y1))


def _check_invariants(original: list, ordered: list, label: str) -> None:
    orig_ids = {b.id for b in original}
    ordered_ids = [b.id for b in ordered]
    assert set(ordered_ids) == orig_ids, f"[{label}] Blocks lost or added"
    assert len(ordered_ids) == len(set(ordered_ids)), f"[{label}] Duplicates detected"
    assert len(ordered) == len(original), f"[{label}] Block count changed"
    indices = [b.reading_order_index for b in ordered]
    assert indices == list(range(len(ordered))), f"[{label}] reading_order_index not contiguous"
    assert all(b.column_index in (0, 1) for b in ordered), f"[{label}] Invalid column_index"
    orig_map = {b.id: b for b in original}
    for b in ordered:
        o = orig_map[b.id]
        assert b.text == o.text, f"[{label}] Block {b.id} text mutated"
        assert b.bbox == o.bbox, f"[{label}] Block {b.id} bbox mutated"
        assert b.page == o.page, f"[{label}] Block {b.id} page mutated"


# ── A: A4 page (595 x 842pt) genuine two-column ───────────────────────────────

def test_boundary_a_a4_page_genuine_two_column():
    """
    A4 page (595pt wide). Genuine two-column layout with 68px gutter.
    Gate 2 threshold: 0.38 * 595 = 226px. Right col starts at x0=320.
    All five gates should pass; columns should be detected.
    """
    PAGE_W = 595.0
    left  = [_mb(f"al{i}", 0, f"a4 left {i}", 28, 100 + i * 30, 252, 115 + i * 30) for i in range(6)]
    right = [_mb(f"ar{i}", 0, f"a4 right {i}", 320, 100 + i * 30, 538, 115 + i * 30) for i in range(6)]
    blocks = left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "A-A4")

    # Must detect genuine two-column
    assert any(b.column_index == 1 for b in ordered), "A4 two-column not detected"
    left_positions  = [b.reading_order_index for b in ordered if b.column_index == 0]
    right_positions = [b.reading_order_index for b in ordered if b.column_index == 1]
    assert max(left_positions) < min(right_positions), "A4: left col must precede right col"


# ── B: Letter page (612 x 792pt) genuine two-column ──────────────────────────

def test_boundary_b_letter_page_genuine_two_column():
    """
    Standard Letter page (612pt wide). Genuine two-column with 120px gutter.
    Confirms that the constants work correctly for the baseline page size.
    """
    PAGE_W = 612.0
    left  = [_mb(f"bl{i}", 0, f"letter left {i}", 36, 100 + i * 30, 230, 115 + i * 30) for i in range(6)]
    right = [_mb(f"br{i}", 0, f"letter right {i}", 350, 100 + i * 30, 560, 115 + i * 30) for i in range(6)]
    blocks = left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "B-Letter")

    assert any(b.column_index == 1 for b in ordered), "Letter two-column not detected"
    left_positions  = [b.reading_order_index for b in ordered if b.column_index == 0]
    right_positions = [b.reading_order_index for b in ordered if b.column_index == 1]
    assert max(left_positions) < min(right_positions), "Letter: left col must precede right col"


# ── C: Narrow gutter (30px < 50px threshold) — should NOT detect two-column ──

def test_boundary_c_narrow_gutter_below_threshold():
    """
    Two columns with only 30px gutter (x1_left=250, x0_right=280).
    _MIN_COLUMN_GAP_PX=50, so Gate 1 fails.
    KNOWN LIMITATION: a genuine narrow-gutter two-column layout is misclassified
    as single-column. Document this behaviour explicitly.
    """
    PAGE_W = 612.0
    left  = [_mb(f"nl{i}", 0, f"narrow left {i}", 36, 100 + i * 30, 250, 115 + i * 30) for i in range(6)]
    right = [_mb(f"nr{i}", 0, f"narrow right {i}", 280, 100 + i * 30, 560, 115 + i * 30) for i in range(6)]
    # x1_left=250, x0_right=280, gap=30 < 50px
    blocks = left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "C-NarrowGutter")

    # DOCUMENTED LIMITATION: narrow gutter falls back to single-column mode
    # The test asserts the current behaviour (not a desired outcome).
    two_col = any(b.column_index == 1 for b in ordered)
    assert not two_col, (
        "C: Narrow-gutter two-column falls back to single-column mode. "
        "This is a known limitation of Gate 1 (_MIN_COLUMN_GAP_PX=50)."
    )


# ── D: Wide gutter (120px) — should detect genuine two-column ─────────────────

def test_boundary_d_wide_gutter_detects_two_column():
    """
    Two columns with 120px gutter. All five gates pass.
    Reading order: left col (top-to-bottom) then right col (top-to-bottom).
    """
    PAGE_W = 612.0
    left  = [_mb(f"wl{i}", 0, f"wide left {i}", 36, 100 + i * 30, 230, 115 + i * 30) for i in range(6)]
    right = [_mb(f"wr{i}", 0, f"wide right {i}", 350, 100 + i * 30, 560, 115 + i * 30) for i in range(6)]
    blocks = left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "D-WideGutter")

    assert any(b.column_index == 1 for b in ordered), "D: Wide-gutter two-column must be detected"


# ── E: Asymmetric heights (ratio ~5:8) — within _MAX_HEIGHT_RATIO=5.0 ─────────

def test_boundary_e_asymmetric_heights_within_ratio():
    """
    Left col spans 150px, right col spans 450px → ratio 3.0 < _MAX_HEIGHT_RATIO=5.0.
    Gate 4 should pass; two-column should be detected.
    This represents a real-world case: short skills sidebar + longer experience body.
    Note: a skills sidebar with only 5 blocks (vs 15 in experience) produces ratio 5.8,
    which fails Gate 4. That specific case is documented as a limitation.
    """
    PAGE_W = 612.0
    left  = [_mb(f"el{i}", 0, f"asym left {i}", 36, 100 + i * 50, 240, 115 + i * 50) for i in range(4)]
    right = [_mb(f"er{i}", 0, f"asym right {i}", 330, 100 + i * 30, 560, 115 + i * 30) for i in range(15)]
    # left spans: y0=100 to y1=115+(3*50)=265 → height 165
    # right spans: y0=100 to y1=115+(14*30)=535 → height 435
    # ratio = 435/165 = 2.6 — should pass gate4
    blocks = left + right
    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "E-AsymmetricHeights")

    left_h  = max(b.y1 for b in left)  - min(b.y0 for b in left)
    right_h = max(b.y1 for b in right) - min(b.y0 for b in right)
    ratio   = right_h / left_h if left_h > 0 else 999
    # Only assert the two-column result if the ratio actually passes Gate 4
    if ratio <= 5.0:
        assert any(b.column_index == 1 for b in ordered), (
            f"E: Asymmetric heights (ratio={ratio:.1f} <= 5.0) should detect two-column"
        )


# ── F: Sparse sidebar (exactly _MIN_BLOCKS_PER_COLUMN=2 blocks) ───────────────

def test_boundary_f_sparse_sidebar_exactly_min_blocks():
    """
    Each column has exactly _MIN_BLOCKS_PER_COLUMN=2 blocks.
    Gate 3 uses >=, so exactly 2 should pass.
    Both columns must be detected and correctly ordered.
    """
    PAGE_W = 612.0
    left  = [_mb(f"fl{i}", 0, f"sparse left {i}", 36, 100 + i * 200, 240, 120 + i * 200) for i in range(2)]
    right = [_mb(f"fr{i}", 0, f"sparse right {i}", 330, 100 + i * 200, 560, 120 + i * 200) for i in range(2)]
    blocks = left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "F-SparseSidebar")

    # With exactly 2 blocks per column and full vertical overlap, all gates should pass
    assert any(b.column_index == 1 for b in ordered), (
        "F: Sparse sidebar with exactly _MIN_BLOCKS_PER_COLUMN=2 must be detected as two-column"
    )


# ── G: Two-column below a full-width header ───────────────────────────────────

def test_boundary_g_fullwidth_header_then_two_columns():
    """
    Page begins with a full-width header block, then two genuine columns start.
    Full-width header must appear first in the ordered output.
    Two-column portion must be detected and ordered correctly.
    """
    PAGE_W = 612.0
    header = _mb("HEADER", 0, "Full-width page header block", 36, 30, 576, 55)
    left   = [_mb(f"gl{i}", 0, f"g left {i}",  40, 90 + i * 30, 255, 105 + i * 30) for i in range(6)]
    right  = [_mb(f"gr{i}", 0, f"g right {i}", 320, 90 + i * 30, 570, 105 + i * 30) for i in range(6)]
    blocks = [header] + left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "G-FullWidthThenTwoCols")

    ids = [b.id for b in ordered]
    assert ids[0] == "HEADER", f"G: Full-width header must be first, got {ids[0]}"
    assert any(b.column_index == 1 for b in ordered), "G: Two-column portion must be detected"


# ── H: Full-width block in the MIDDLE of two-column layout ───────────────────

def test_boundary_h_fullwidth_block_in_middle_of_two_columns():
    """
    A full-width block appears mid-page (y0=220 > full_width_bottom_thresh=200)
    inside a two-column layout.

    KNOWN LIMITATION: The full_width_bottom_thresh=200 constant means any full-width
    block below y0=200 is treated as a 'bottom' block and appended AFTER both columns,
    regardless of its actual y position within the column stream.

    This test documents the current behaviour — the full-width block appears at
    the END of the ordered output even though it is visually between blocks.
    """
    PAGE_W = 612.0
    left   = [_mb(f"hl{i}", 0, f"h left {i}",  36, 100 + i * 30, 240, 115 + i * 30) for i in range(4)]
    mid_fw = _mb("MID_FW", 0, "Full-width mid-page block", 36, 220, 576, 250)  # y0=220 > 200
    right  = [_mb(f"hr{i}", 0, f"h right {i}", 330, 100 + i * 30, 560, 115 + i * 30) for i in range(4)]
    blocks = left + [mid_fw] + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "H-FullWidthInMiddle")

    ids = [b.id for b in ordered]
    # Document the limitation: MID_FW appears at the END, not at its visual position
    mfw_pos = ids.index("MID_FW")
    # It should be after both column groups — this is the documented limitation
    assert mfw_pos == len(ids) - 1, (
        f"H: KNOWN LIMITATION — Full-width block mid-page (y0=220 > 200) "
        f"appears at pos {mfw_pos}, expected at end. "
        f"The full_width_bottom_thresh=200 does not account for mid-page full-width blocks."
    )


# ── I: Deep indentation — DOCUMENTED FAILURE CASE ─────────────────────────────

def test_boundary_i_deep_indentation_misclassified_as_two_column():
    """
    Single-column layout with deep (250px) indentation where the body text
    starts at x0=250 (41% of 612px page width, above the 38% Gate 2 threshold).

    DOCUMENTED FAILURE: When all five gates happen to pass for a deeply-indented
    single-column document:
      - Gate 1 passes: gap between heading x1(150) and body x0(250) = 100px >= 50px
      - Gate 2 passes: right_x0_mean=250 >= 0.38*612=232px
      - Gate 3 passes: 6 blocks per group
      - Gate 4 passes: equal heights (symmetric layout)
      - Gate 5 passes: high overlap (headings and bodies at same y-levels)

    The algorithm incorrectly treats this as a two-column document.
    This is the primary remaining generalization weakness of Phase 1.
    """
    PAGE_W = 612.0
    # Headings at x0=36, bodies at x0=250, same y-levels (both present at each row)
    headings = [_mb(f"ih{i}", 0, f"heading text {i}", 36, 50 + i * 80, 150, 65 + i * 80) for i in range(6)]
    bodies   = [_mb(f"ib{i}", 0, f"body content {i}", 250, 65 + i * 80, 560, 80 + i * 80) for i in range(6)]
    blocks   = headings + bodies

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "I-DeepIndent")

    # Document the actual (incorrect) behaviour
    two_col = any(b.column_index == 1 for b in ordered)
    # This assertion DOCUMENTS THE FAILURE — it is expected to be True (wrong classification)
    # The test passes, but records that a real single-column deep-indentation layout
    # is incorrectly classified as two-column.
    # When Phase 1 is fixed, this test should be updated to assert `not two_col`.
    assert two_col, (
        "I: DOCUMENTED FAILURE — Deep indentation (250px body x0 > 38% page width) "
        "with same y-level headings passes all 5 gates and is misclassified as two-column. "
        "This is a known limitation to be addressed in a future fix."
    )


# ── J: Multiple indentation levels (3 x0 clusters) ───────────────────────────

def test_boundary_j_multiple_indentation_levels():
    """
    Three distinct x0 levels: level1=36, level2=72, level3=350.
    The algorithm uses leftmost (36) and rightmost (350) clusters.
    Level2 blocks (x0=72) should be assigned to the left cluster.
    All invariants must hold; no blocks lost.
    """
    PAGE_W = 612.0
    level1 = [_mb(f"jl1_{i}", 0, f"level1 {i}",  36, 50 + i * 30, 180, 65 + i * 30) for i in range(4)]
    level2 = [_mb(f"jl2_{i}", 0, f"level2 {i}",  72, 65 + i * 30, 280, 80 + i * 30) for i in range(4)]
    level3 = [_mb(f"jl3_{i}", 0, f"level3 {i}", 350, 50 + i * 30, 560, 65 + i * 30) for i in range(4)]
    blocks = level1 + level2 + level3

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "J-MultiIndent")

    # Level2 blocks (x0=72) are closer to left cluster (dist=36) than right (dist=278)
    # → should be assigned column_index=0
    for b in ordered:
        if b.id.startswith("jl2"):
            assert b.column_index == 0, (
                f"J: level2 block {b.id} (x0=72) should be assigned to left cluster"
            )

    # Level3 blocks should be column 1
    for b in ordered:
        if b.id.startswith("jl3"):
            assert b.column_index == 1, f"J: level3 block {b.id} should be right column"


# ── K: Different page widths — legal page (612 x 1008pt) ─────────────────────

def test_boundary_k_legal_page_two_column():
    """
    Legal page (612 x 1008pt, same width as Letter).
    Constants are expressed as fractions of page_width so legal page
    behaves identically to letter for column detection.
    """
    PAGE_W = 612.0  # Legal is same width as Letter, just taller
    left  = [_mb(f"kl{i}", 0, f"legal left {i}", 36, 100 + i * 30, 230, 115 + i * 30) for i in range(6)]
    right = [_mb(f"kr{i}", 0, f"legal right {i}", 350, 100 + i * 30, 560, 115 + i * 30) for i in range(6)]
    blocks = left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "K-LegalPage")

    assert any(b.column_index == 1 for b in ordered), "K: Legal page two-column must be detected"


def test_boundary_k_wide_page_two_column():
    """
    Wide custom page (900pt wide, e.g. landscape A4).
    Gate thresholds scale with page_width; two-column layout should still be detected.
    """
    PAGE_W = 900.0
    left  = [_mb(f"kwl{i}", 0, f"wide left {i}",  50, 100 + i * 30, 350, 115 + i * 30) for i in range(6)]
    right = [_mb(f"kwr{i}", 0, f"wide right {i}", 500, 100 + i * 30, 850, 115 + i * 30) for i in range(6)]
    # On 900pt page: 38% = 342pt. right_x0=500 > 342 → Gate 2 passes.
    # Gap: 500 - 350 = 150 >= 50 → Gate 1 passes.
    blocks = left + right

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "K-WidePage")

    assert any(b.column_index == 1 for b in ordered), "K: Wide page two-column must be detected"


# ── L: Multi-page mixed layouts ───────────────────────────────────────────────

def test_boundary_l_multipage_single_then_two_column():
    """
    Page 0: single-column. Page 1: genuine two-column with page header + footer.
    Each page is processed independently (as text_extraction.py does).

    DOCUMENTED FAILURE — PAGE FOOTER CONTAMINATION:
    The page footer block on page 1 (p1_f: x0=270, width=72) is not classified
    as full-width (72 < 70% of 612=428), so it enters the candidate pool.
    Its x0=270 falls between left_col mean (36) and right_col mean (330), but is
    closer to right → assigned to right_col.

    This causes:
      - Gate 1 to fail: right_col's x0_min becomes 270 (footer x0), so
        gap = 270 - left_x1(240) = 30px < 50px threshold
      - Gate 4 to fail: right_col's height becomes 770-60=710 (footer y1),
        vs left_col height 150, ratio = 4.7× — actually passes in this case,
        but the gap failure alone is sufficient to fall back to single-column

    Result: Page 1 is classified as single-column even though it has a genuine
    two-column layout. This is a known bug to be fixed in a future revision.

    The fix requires a pre-filter step that removes likely footer/isolated blocks
    from the column candidate pool before gate evaluation.
    """
    PAGE_W = 612.0

    # Page 0 — single column
    p0_blocks = [
        _mb("p0_h",  0, "Repeated Header",              36,  15, 576, 35),
        _mb("p0_b0", 0, "Single column content line 1", 36,  60, 576, 75),
        _mb("p0_b1", 0, "Single column content line 2", 36,  80, 576, 95),
        _mb("p0_b2", 0, "Single column content line 3", 36, 100, 576, 115),
        _mb("p0_f",  0, "Page 1",                       270, 770, 342, 785),
    ]

    # Page 1 — genuine two columns with header and footer
    p1_left   = [_mb(f"p1l{i}", 1, f"p1 left {i}",  36, 60 + i * 30, 240, 75 + i * 30) for i in range(5)]
    p1_right  = [_mb(f"p1r{i}", 1, f"p1 right {i}", 330, 60 + i * 30, 560, 75 + i * 30) for i in range(5)]
    p1_header = _mb("p1_h", 1, "Repeated Header", 36, 15, 576, 35)
    p1_footer = _mb("p1_f", 1, "Page 2", 270, 770, 342, 785)  # narrow, not full-width
    p1_blocks = [p1_header] + p1_left + p1_right + [p1_footer]

    ordered_p0 = detect_and_order_columns(p0_blocks, page_width=PAGE_W)
    ordered_p1 = detect_and_order_columns(p1_blocks, page_width=PAGE_W)

    _check_invariants(p0_blocks, ordered_p0, "L-page0")
    _check_invariants(p1_blocks, ordered_p1, "L-page1")

    # Page 0: all single column (correct)
    assert all(b.column_index == 0 for b in ordered_p0), \
        "L: Page 0 (single-col) must have all column_index=0"

    # Page 1: DOCUMENTED FAILURE — footer contamination causes single-column fallback
    # The footer block (x0=270, narrow) joins right_col, reducing gap to 30px (< 50px).
    # When this bug is fixed (by pre-filtering footer-like isolated blocks),
    # this assertion should be changed to: assert any(b.column_index == 1 for b in ordered_p1)
    two_col_p1 = any(b.column_index == 1 for b in ordered_p1)
    assert not two_col_p1, (
        "L: DOCUMENTED FAILURE — Page footer (x0=270, width=72) contaminates the right "
        "column group. Gate 1 gap drops to 30px (< 50px threshold), causing genuine "
        "two-column layout to be misclassified as single-column. "
        "Fix: pre-filter isolated non-column-width blocks from candidate pool before gates."
    )

    # Multi-page header suppression (works regardless of column detection)
    p0 = DocumentPage(page_number=0, width=PAGE_W, height=792.0, blocks=ordered_p0)
    p1 = DocumentPage(page_number=1, width=PAGE_W, height=792.0, blocks=ordered_p1)
    suppress_repeated_headers_footers([p0, p1])

    h0 = next(b for b in ordered_p0 if b.id == "p0_h")
    h1 = next(b for b in ordered_p1 if b.id == "p1_h")
    assert h0.is_repeated_header_or_footer, "L: Page 0 header must be suppressed"
    assert h1.is_repeated_header_or_footer, "L: Page 1 header must be suppressed"

    # Main content must not be suppressed
    content = next(b for b in ordered_p0 if b.id == "p0_b0")
    assert not content.is_repeated_header_or_footer, "L: Page 0 content must not be suppressed"

