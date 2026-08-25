"""
Raw text (+ layout) extraction from uploaded resume files.
Deterministic, no AI — this is pure file parsing, per Feature 28
(don't call the LLM for work plain code can do).
"""
import io

import fitz  # PyMuPDF
from docx import Document


class UnsupportedFileTypeError(Exception):
    pass


class CorruptedFileError(Exception):
    pass


def extract_pdf(file_bytes: bytes) -> tuple[str, list[dict]]:
    """
    Returns (full_text, blocks) where blocks is a list of
    {page, x0, y0, x1, y1, text} — the layout info the Parseability
    Engine uses to detect multi-column layouts.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise CorruptedFileError(f"Could not open PDF: {exc}") from exc

    full_text_parts: list[str] = []
    blocks: list[dict] = []

    for page_num, page in enumerate(doc):
        page_text = page.get_text("text")
        full_text_parts.append(page_text)
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            if text.strip():
                blocks.append({"page": page_num, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": text.strip()})

    doc.close()
    return "\n".join(full_text_parts), blocks


def extract_docx(file_bytes: bytes) -> tuple[str, list[dict], bool]:
    try:
        document = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise CorruptedFileError(f"Could not open DOCX: {exc}") from exc

    lines = [p.text for p in document.paragraphs if p.text.strip()]
    # DOCX doesn't give us pixel coordinates, so we can't run the same
    # multi-column heuristic — the Parseability Engine treats DOCX as
    # "layout unknown" for that specific check and relies on the other
    # structural checks instead.
    has_tables = len(document.tables) > 0
    blocks = [{"page": 0, "x0": 0, "y0": i, "x1": 100, "y1": i, "text": line} for i, line in enumerate(lines)]
    full_text = "\n".join(lines)
    return full_text, blocks, has_tables


def extract_text_and_layout(file_bytes: bytes, filename: str) -> dict:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        if not file_bytes.startswith(b"%PDF"):
            raise CorruptedFileError("File does not have a valid PDF signature.")
        text, blocks = extract_pdf(file_bytes)
        return {"text": text, "blocks": blocks, "has_tables": None, "file_type": "pdf"}

    if lower.endswith(".docx"):
        if not file_bytes.startswith(b"PK"):
            raise CorruptedFileError("File does not have a valid DOCX (zip) signature.")
        text, blocks, has_tables = extract_docx(file_bytes)
        return {"text": text, "blocks": blocks, "has_tables": has_tables, "file_type": "docx"}

    raise UnsupportedFileTypeError(f"Unsupported file type for '{filename}'. Only PDF and DOCX are supported.")
