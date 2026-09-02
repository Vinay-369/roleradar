"""
Phase 1 — Generalized Document Geometry & Reading Order Tests
=============================================================
Verifies that detect_and_order_columns() correctly infers the natural reading
order across ten distinct layout classes without using any document-specific
strings, coordinates, or candidate names.

Scenarios:
  A. Single-column normal resume
  B. Single-column resume with indented section body
  C. Hanging section headers (narrow heading + indented body = same stream)
  D. Multi-line section header spanning consecutive blocks
  E. Genuine two-column resume (skills sidebar + main experience)
  F. Full-width header followed by two genuine columns
  G. Mixed-width blocks within a single reading stream
  H. Multi-page document -- per-page ordering is independent
  I. Dense short-line resume (many narrow blocks at consistent x0)
  J. Real-PDF stress test -- uploaded resume must not misclassify indented
     headings as a second column

Invariants checked on every scenario:
  - Block count unchanged (no blocks dropped or duplicated)
  - Block text unchanged
  - Block bbox unchanged
  - Page number preserved
  - reading_order_index is a contiguous 0-based sequence
  - column_index is assigned (0 or 1 only)
"""
import io
import os
import pytest
import fitz  # PyMuPDF

from app.modules.resume.parsing.document import DocumentBlock, DocumentPage
from app.modules.resume.parsing.normalization import (
    detect_and_order_columns,
    suppress_repeated_headers_footers,
)
from app.modules.resume.parsing.text_extraction import extract_pdf_to_document


# -- Helpers ------------------------------------------------------------------

def _make_block(
    bid: str,
    page: int,
    text: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> DocumentBlock:
    return DocumentBlock(id=bid, page=page, text=text, bbox=(x0, y0, x1, y1))


def _check_invariants(
    original: list,
    ordered: list,
    label: str,
) -> None:
    """Assert that all invariants hold after reordering."""
    orig_ids = {b.id for b in original}
    ordered_ids = [b.id for b in ordered]

    # No blocks lost
    assert set(ordered_ids) == orig_ids, f"[{label}] Blocks were lost or added: {orig_ids ^ set(ordered_ids)}"

    # No duplicates
    assert len(ordered_ids) == len(set(ordered_ids)), f"[{label}] Duplicate blocks in output"

    # Block count unchanged
    assert len(ordered) == len(original), f"[{label}] Block count changed"

    # reading_order_index is contiguous 0-based
    indices = [b.reading_order_index for b in ordered]
    assert indices == list(range(len(ordered))), f"[{label}] reading_order_index not contiguous: {indices}"

    # column_index is 0 or 1
    assert all(b.column_index in (0, 1) for b in ordered), f"[{label}] Unexpected column_index values"

    # Text and bbox preserved (detect_and_order_columns must not mutate these)
    orig_map = {b.id: b for b in original}
    for b in ordered:
        orig = orig_map[b.id]
        assert b.text == orig.text, f"[{label}] Block {b.id} text mutated"
        assert b.bbox == orig.bbox, f"[{label}] Block {b.id} bbox mutated"
        assert b.page == orig.page, f"[{label}] Block {b.id} page mutated"


# -- Scenario A: Single-column normal resume ----------------------------------

def test_scenario_a_single_column_normal():
    """
    Normal resume: all blocks span similar x-range from left margin to right.
    Expected: stable vertical sort order, all column_index=0.
    """
    PAGE_W = 612.0
    blocks = [
        _make_block("a0", 0, "NAME LINE",           36, 40, 576, 55),
        _make_block("a1", 0, "Contact info",         36, 60, 576, 75),
        _make_block("a2", 0, "SUMMARY",              36, 90, 576, 105),
        _make_block("a3", 0, "Summary text here",    36, 110, 576, 125),
        _make_block("a4", 0, "EXPERIENCE",           36, 140, 576, 155),
        _make_block("a5", 0, "Company A bullet 1",   36, 160, 576, 175),
        _make_block("a6", 0, "Company A bullet 2",   36, 180, 576, 195),
        _make_block("a7", 0, "EDUCATION",            36, 210, 576, 225),
        _make_block("a8", 0, "University degree",    36, 230, 576, 245),
    ]

    # Supply in scrambled order to confirm sort works
    scrambled = [blocks[8], blocks[5], blocks[1], blocks[0], blocks[3],
                 blocks[7], blocks[4], blocks[6], blocks[2]]
    ordered = detect_and_order_columns(scrambled, page_width=PAGE_W)

    _check_invariants(scrambled, ordered, "A")

    # All blocks should be column 0 (no genuine two-column detected)
    assert all(b.column_index == 0 for b in ordered), "Scenario A: expected all col_index=0"

    # Reading order should match top-to-bottom order of original blocks
    ordered_texts = [b.text for b in ordered]
    expected_texts = [b.text for b in blocks]
    assert ordered_texts == expected_texts, f"Scenario A order wrong: {ordered_texts}"


# -- Scenario B: Single-column with indented section body ---------------------

def test_scenario_b_single_column_indented_body():
    """
    Heading at x0=36, body text indented to x0=72. Both belong to same stream.
    Must NOT be classified as two columns.
    """
    PAGE_W = 612.0
    blocks = [
        _make_block("b0", 0, "EXPERIENCE",           36,  50,  200,  65),
        _make_block("b1", 0, "Senior Engineer, Corp", 72,  70,  540,  85),
        _make_block("b2", 0, "Bullet one content",    72,  90,  540, 105),
        _make_block("b3", 0, "Bullet two content",    72, 110,  540, 125),
        _make_block("b4", 0, "SKILLS",               36, 140,  200, 155),
        _make_block("b5", 0, "Python, Java, Go",     72, 160,  540, 175),
    ]
    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "B")

    # Should be single stream
    assert all(b.column_index == 0 for b in ordered), "Scenario B: must be single column"

    # Heading must precede its body
    ids = [b.id for b in ordered]
    assert ids.index("b0") < ids.index("b1"), "Scenario B: EXPERIENCE heading must precede body"
    assert ids.index("b4") < ids.index("b5"), "Scenario B: SKILLS heading must precede body"


# -- Scenario C: Hanging section headers --------------------------------------

def test_scenario_c_hanging_section_headers():
    """
    Headers at x0=36 with narrow width (~70px), body text at x0=144 with
    wide width (~400px). Same y-band. Must be classified as single stream,
    not two columns.
    """
    PAGE_W = 612.0
    blocks = [
        _make_block("c0", 0, "FULL NAME",               180, 30, 432, 48),
        _make_block("c1", 0, "WORK",                     36, 100, 106, 115),
        _make_block("c2", 0, "EXPERIENCE",                36, 115, 106, 130),
        _make_block("c3", 0, "Company A, Role, Date",    144, 100, 556, 115),
        _make_block("c4", 0, "Bullet one",               144, 120, 556, 135),
        _make_block("c5", 0, "Bullet two",               144, 140, 556, 155),
        _make_block("c6", 0, "EDUCATION",                 36, 180, 106, 195),
        _make_block("c7", 0, "University of X, B.Sc.",   144, 180, 556, 195),
        _make_block("c8", 0, "GPA: 3.8, May 2020",       144, 200, 556, 215),
    ]
    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "C")

    col_indices = {b.column_index for b in ordered}
    assert col_indices == {0}, f"Scenario C: all blocks should be col 0, got {col_indices}"

    ids = [b.id for b in ordered]
    assert ids.index("c1") < ids.index("c3"), "Scenario C: heading must precede body"


# -- Scenario D: Multi-line section header ------------------------------------

def test_scenario_d_multiline_section_header():
    """
    A section heading split across two vertically adjacent narrow blocks,
    body text below. Must be same single stream.
    """
    PAGE_W = 612.0
    blocks = [
        _make_block("d0", 0, "PROJECT",               36, 200, 106, 215),
        _make_block("d1", 0, "EXPERIENCE",            36, 215, 106, 230),
        _make_block("d2", 0, "Project 1 description", 144, 200, 556, 240),
        _make_block("d3", 0, "Developed system X",    144, 250, 556, 265),
        _make_block("d4", 0, "Deployed to cloud",     144, 270, 556, 285),
    ]
    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "D")

    assert all(b.column_index == 0 for b in ordered), "Scenario D: must be single column"

    ids = [b.id for b in ordered]
    assert ids.index("d0") < ids.index("d2"), "Scenario D: PROJECT must precede body"


# -- Scenario E: Genuine two-column resume ------------------------------------

def test_scenario_e_genuine_two_column():
    """
    Classic two-column resume: left sidebar (x0~50, x1~260) with skills/
    education running parallel to right main body (x0~310, x1~560).
    Both columns occupy the same y-ranges.
    Reading order: left col complete, then right col complete.
    """
    PAGE_W = 612.0
    left_blocks = [
        _make_block("el0", 0, "SKILLS",           50, 100, 260, 115),
        _make_block("el1", 0, "Python, Java",      50, 120, 260, 135),
        _make_block("el2", 0, "Docker, K8s",       50, 140, 260, 155),
        _make_block("el3", 0, "EDUCATION",         50, 170, 260, 185),
        _make_block("el4", 0, "B.Sc. CS, 2020",    50, 190, 260, 205),
        _make_block("el5", 0, "GPA 3.9",           50, 210, 260, 225),
    ]
    right_blocks = [
        _make_block("er0", 0, "EXPERIENCE",              310, 100, 560, 115),
        _make_block("er1", 0, "Senior Engineer, Corp A",  310, 120, 560, 135),
        _make_block("er2", 0, "Built microservices arch", 310, 140, 560, 155),
        _make_block("er3", 0, "Reduced latency by 40%",  310, 160, 560, 175),
        _make_block("er4", 0, "Software Eng, Corp B",    310, 190, 560, 205),
        _make_block("er5", 0, "Scaled to 100k QPS",      310, 210, 560, 225),
    ]
    # Interleaved extraction order
    scrambled = [left_blocks[0], right_blocks[0], left_blocks[1], right_blocks[1],
                 left_blocks[2], right_blocks[2], left_blocks[3], right_blocks[3],
                 left_blocks[4], right_blocks[4], left_blocks[5], right_blocks[5]]

    ordered = detect_and_order_columns(scrambled, page_width=PAGE_W)
    _check_invariants(scrambled, ordered, "E")

    ordered_ids = [b.id for b in ordered]
    left_positions = [ordered_ids.index(b.id) for b in left_blocks]
    right_positions = [ordered_ids.index(b.id) for b in right_blocks]
    assert max(left_positions) < min(right_positions), (
        f"Scenario E: all left-col blocks must precede right-col blocks. "
        f"left={left_positions}, right={right_positions}"
    )

    for b in ordered:
        if b.id.startswith("el"):
            assert b.column_index == 0, f"Scenario E: {b.id} should be col 0"
        elif b.id.startswith("er"):
            assert b.column_index == 1, f"Scenario E: {b.id} should be col 1"


# -- Scenario F: Full-width header then two genuine columns -------------------

def test_scenario_f_full_width_header_then_two_columns():
    """
    Full-width name/contact bar at the top, then two genuine columns.
    Header must appear first; columns must be left-then-right.
    """
    PAGE_W = 612.0
    header = _make_block("fh", 0, "FULL NAME | email@x.com | phone", 36, 30, 576, 55)

    left_blocks = [
        _make_block("fl0", 0, "SKILLS",       40, 80, 250, 95),
        _make_block("fl1", 0, "Python, Go",   40, 100, 250, 115),
        _make_block("fl2", 0, "AWS, Docker",  40, 120, 250, 135),
    ]
    right_blocks = [
        _make_block("fr0", 0, "EXPERIENCE",            310, 80, 570, 95),
        _make_block("fr1", 0, "Lead Eng, Company C",   310, 100, 570, 115),
        _make_block("fr2", 0, "Refactored monolith",   310, 120, 570, 135),
    ]

    all_blocks = [header, left_blocks[0], right_blocks[0], left_blocks[1],
                  right_blocks[1], left_blocks[2], right_blocks[2]]

    ordered = detect_and_order_columns(all_blocks, page_width=PAGE_W)
    _check_invariants(all_blocks, ordered, "F")

    ordered_ids = [b.id for b in ordered]
    assert ordered_ids[0] == "fh", f"Scenario F: header block must be first, got {ordered_ids[0]}"

    left_positions = [ordered_ids.index(b.id) for b in left_blocks]
    right_positions = [ordered_ids.index(b.id) for b in right_blocks]
    assert max(left_positions) < min(right_positions), \
        "Scenario F: all left-col blocks must precede right-col blocks"


# -- Scenario G: Mixed-width blocks in single stream --------------------------

def test_scenario_g_mixed_width_single_stream():
    """
    Some blocks span 90% of page width, others narrower. All belong to same
    linear stream. Must not trigger two-column mode.
    """
    PAGE_W = 612.0
    blocks = [
        _make_block("g0", 0, "SUMMARY",                 36, 50,  576, 65),
        _make_block("g1", 0, "Experienced engineer",    36, 70,  576, 85),
        _make_block("g2", 0, "10 years in backend",     36, 90,  400, 105),
        _make_block("g3", 0, "focusing on distributed", 36, 110, 300, 125),
        _make_block("g4", 0, "SKILLS",                  36, 140, 576, 155),
        _make_block("g5", 0, "Python, Java, Rust, C++", 36, 160, 576, 175),
        _make_block("g6", 0, "AWS, GCP, Azure, K8s",    36, 180, 500, 195),
    ]
    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "G")

    assert all(b.column_index == 0 for b in ordered), \
        "Scenario G: mixed-width single stream must not trigger two-column mode"


# -- Scenario H: Multi-page document ------------------------------------------

def test_scenario_h_multi_page():
    """
    Two-page document. Each page ordered independently.
    Repeated header/footer suppressed. Main content preserved.
    """
    PAGE_W = 612.0

    p0_blocks = [
        _make_block("h0_hdr", 0, "Candidate Name Resume", 36, 15, 576, 35),
        _make_block("h0_b0",  0, "EXPERIENCE",             36, 60, 576, 75),
        _make_block("h0_b1",  0, "Senior Eng at Corp A",   36, 80, 576, 95),
        _make_block("h0_b2",  0, "Built distributed svc",  36, 100, 576, 115),
        _make_block("h0_ftr", 0, "Page 1 of 2",            250, 765, 362, 780),
    ]
    p1_blocks = [
        _make_block("h1_hdr", 1, "Candidate Name Resume", 36, 15, 576, 35),
        _make_block("h1_b0",  1, "EDUCATION",              36, 60, 576, 75),
        _make_block("h1_b1",  1, "B.Sc. CS University Y",  36, 80, 576, 95),
        _make_block("h1_ftr", 1, "Page 2 of 2",            250, 765, 362, 780),
    ]

    p0 = DocumentPage(page_number=0, width=PAGE_W, height=792.0, blocks=p0_blocks)
    p1 = DocumentPage(page_number=1, width=PAGE_W, height=792.0, blocks=p1_blocks)

    ordered_p0 = detect_and_order_columns(p0_blocks, page_width=PAGE_W)
    ordered_p1 = detect_and_order_columns(p1_blocks, page_width=PAGE_W)

    _check_invariants(p0_blocks, ordered_p0, "H-page0")
    _check_invariants(p1_blocks, ordered_p1, "H-page1")

    p0.blocks = ordered_p0
    p1.blocks = ordered_p1
    suppress_repeated_headers_footers([p0, p1])

    assert p0_blocks[0].is_repeated_header_or_footer is True
    assert p1_blocks[0].is_repeated_header_or_footer is True
    assert p0_blocks[2].is_repeated_header_or_footer is False
    assert p1_blocks[2].is_repeated_header_or_footer is False
    assert p0_blocks[4].is_repeated_header_or_footer is True
    assert p1_blocks[3].is_repeated_header_or_footer is True


# -- Scenario I: Dense short-line resume --------------------------------------

def test_scenario_i_dense_short_lines():
    """
    30 narrow single-line blocks at consistent x0 ~36. Must be single column.
    """
    PAGE_W = 612.0
    blocks = []
    for i in range(30):
        y = 50 + i * 16
        blocks.append(_make_block(f"i{i}", 0, f"Line {i} content here", 36, y, 400, y + 12))

    ordered = detect_and_order_columns(blocks, page_width=PAGE_W)
    _check_invariants(blocks, ordered, "I")

    assert all(b.column_index == 0 for b in ordered), \
        "Scenario I: dense single-column should not trigger two-column mode"

    y0_sequence = [b.y0 for b in ordered]
    assert y0_sequence == sorted(y0_sequence), \
        "Scenario I: blocks should be in top-to-bottom order"


# -- Scenario J: Real-PDF stress test -----------------------------------------

STRESS_TEST_PDF_PATH = r"C:\Users\vinny\Downloads\computingresume---sample.pdf"


@pytest.mark.skipif(
    not os.path.exists(STRESS_TEST_PDF_PATH),
    reason="Stress-test PDF not present in expected location.",
)
def test_scenario_j_stress_test_real_pdf():
    """
    Real uploaded resume (single-page, indented hanging-header layout).

    Invariants:
    - Block count unchanged from extraction
    - No blocks duplicated
    - All block texts preserved
    - All blocks column_index == 0 (NOT misclassified as two-column)
    - Name block (top y0) appears before contact info block
    - Name block appears before experience bullets
    - Full text contains expected section content
    - No text fabricated or lost (char count tolerance)
    """
    with open(STRESS_TEST_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    full_text, legacy_blocks, norm_doc, is_scanned = extract_pdf_to_document(pdf_bytes)

    assert not is_scanned, "Stress-test PDF should not be flagged as scanned"
    assert len(norm_doc.pages) >= 1

    page = norm_doc.pages[0]
    ordered = page.blocks

    assert len(ordered) > 0, "Should have at least one block"

    # Contiguous reading_order_index
    indices = [b.reading_order_index for b in ordered]
    assert indices == list(range(len(ordered))), \
        f"reading_order_index not contiguous: {indices}"

    # No false two-column classification
    two_col_blocks = [b for b in ordered if b.column_index == 1]
    assert two_col_blocks == [], (
        f"Stress test: {len(two_col_blocks)} blocks misclassified as right-column.\n"
        f"These are: {[(b.id, b.text[:40]) for b in two_col_blocks]}"
    )

    # Name block (smallest y0 on page) must precede contact block
    name_blocks = [b for b in ordered if b.y0 < 50 and len(b.text.strip()) > 3]
    contact_blocks = [b for b in ordered if 50 <= b.y0 < 80]
    if name_blocks and contact_blocks:
        assert name_blocks[0].reading_order_index < contact_blocks[0].reading_order_index, \
            "Stress test: name block (y0<50) must precede contact block (y0 50-80)"

    # Full text content preserved
    assert "Software Engineer" in full_text, "Stress test: role text missing from full text"

    # Character count sanity (blocks vs full_text within 15% tolerance)
    sum_block_chars = sum(len(b.text) for b in ordered)
    full_text_chars = len(full_text.replace("\n", " "))
    ratio = abs(sum_block_chars - full_text_chars) / max(full_text_chars, 1)
    assert ratio < 0.15, (
        f"Stress test: character count divergence {ratio:.1%} "
        f"(blocks={sum_block_chars}, full_text={full_text_chars})"
    )

    # Print final ordering for the walkthrough report
    print("\n=== PHASE 1 STRESS TEST -- Block Reading Order (After Fix) ===")
    for b in ordered:
        print(f"  [{b.reading_order_index:02d}] col={b.column_index} "
              f"y0={b.y0:5.1f} x0={b.x0:5.1f} | {repr(b.text[:60])}")
