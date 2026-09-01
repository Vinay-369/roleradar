"""
Canonical Normalized Document Representation.
Provides format-independent intermediate document representation
preserving layout, reading order, typography, and blocks for both PDF and DOCX.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentSpan:
    """Atomic text span with font and coordinate metadata."""
    text: str
    font: str | None = None
    size: float | None = None
    is_bold: bool = False
    is_italic: bool = False
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class DocumentLine:
    """Individual line within a block with bullet and formatting metadata."""
    text: str
    normalized_text: str = ""
    spans: list[DocumentSpan] = field(default_factory=list)
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    has_bullet: bool = False
    bullet_char: str | None = None
    is_heading: bool = False


@dataclass
class DocumentBlock:
    """Cohesive block of text (paragraph, heading, list item, or table cell)."""
    id: str
    page: int
    text: str
    normalized_text: str = ""
    lines: list[DocumentLine] = field(default_factory=list)
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    reading_order_index: int = 0
    is_table_cell: bool = False
    column_index: int = 0
    is_repeated_header_or_footer: bool = False

    @property
    def x0(self) -> float:
        return self.bbox[0]

    @property
    def y0(self) -> float:
        return self.bbox[1]

    @property
    def x1(self) -> float:
        return self.bbox[2]

    @property
    def y1(self) -> float:
        return self.bbox[3]


@dataclass
class DocumentPage:
    """Single page containing geometry and ordered blocks."""
    page_number: int
    width: float
    height: float
    blocks: list[DocumentBlock] = field(default_factory=list)
    is_multi_column: bool = False
    column_count: int = 1


@dataclass
class NormalizedDocument:
    """
    Format-agnostic canonical document representation produced by PDF and DOCX extractors.
    All downstream semantic parsing can consume this representation directly.
    """
    pages: list[DocumentPage] = field(default_factory=list)
    full_text: str = ""
    normalized_text: str = ""
    is_scanned: bool = False
    has_tables: bool = False
    file_type: str = "pdf"
    blocks: list[DocumentBlock] = field(default_factory=list)

    def to_legacy_blocks(self) -> list[dict[str, Any]]:
        """
        Converts blocks into the legacy dictionary list expected by parseability checks.
        """
        legacy = []
        for b in self.blocks:
            if b.is_repeated_header_or_footer:
                continue
            t = b.normalized_text or b.text
            if t.strip():
                legacy.append({
                    "page": b.page,
                    "x0": b.x0,
                    "y0": b.y0,
                    "x1": b.x1,
                    "y1": b.y1,
                    "text": t.strip(),
                })
        return legacy
