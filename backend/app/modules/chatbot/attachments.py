"""
Attachment processing for Career Copilot.
Reuses deterministic text extraction for PDF and DOCX, direct decoding for text/code,
and OCR extraction for image attachments. Detects resume structures to suggest full ATS auditing.
"""
import io
import re

import fitz  # PyMuPDF
from app.modules.resume.parsing.text_extraction import extract_docx, extract_pdf
from app.modules.resume.parsing.structurer import SECTION_PATTERNS

MAX_ATTACHMENT_CHARS = 15000  # Cap attachment text to fit LLM context budget comfortably


def is_likely_resume_text(text: str) -> bool:
    """Detects if extracted text contains standard resume section headers (Skills, Experience, Education)."""
    if len(text.strip()) < 50:
        return False
    matched_sections = 0
    for line in text.splitlines()[:50]:
        line_clean = line.strip().rstrip(":-–— \t")
        if len(line_clean) > 40:
            continue
        if any(re.match(pattern, line_clean, re.IGNORECASE) for pattern in SECTION_PATTERNS.values()):
            matched_sections += 1
            if matched_sections >= 2:
                return True
    return False


def extract_image_text(file_bytes: bytes, filename: str) -> tuple[str, bool]:
    """
    Extracts text from images (screenshots, problem statements, job descriptions) via PyMuPDF OCR.
    If OCR engine is not configured on the host system, returns a clear, transparent message.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    try:
        doc = fitz.open(stream=file_bytes, filetype=ext)
        pdf_bytes = doc.convert_to_pdf()
        pdf_doc = fitz.open("pdf", pdf_bytes)
        
        extracted_pages = []
        for page in pdf_doc:
            try:
                tp = page.get_textpage_ocr(language="eng", dpi=150, full=True)
                text = tp.extractText().strip()
                if text:
                    extracted_pages.append(text)
            except Exception:
                # If OCR fails or Tesseract is not configured
                pass

        doc.close()
        pdf_doc.close()

        if extracted_pages:
            full_text = "\n\n".join(extracted_pages)
            return full_text, True
    except Exception:
        pass

    return (
        f"[Image attached: {filename}. Note: Image text extraction requires standard OCR support. "
        f"Career Copilot is text-based and cannot interpret visual diagrams or photos without readable text.]",
        False,
    )


def process_attachment_file(filename: str, file_bytes: bytes) -> tuple[str, str, bool, str | None]:
    """
    Processes an uploaded document or image attachment.
    Returns: (extracted_text, file_type, is_resume, resume_hint)
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    extracted_text = ""
    file_type = ext.upper()

    if ext == "pdf":
        text, _ = extract_pdf(file_bytes)
        extracted_text = text
    elif ext in ("docx", "doc"):
        docx_res = extract_docx(file_bytes)
        extracted_text = docx_res[0]
    elif ext in ("png", "jpg", "jpeg", "webp"):
        text, _ = extract_image_text(file_bytes, filename)
        extracted_text = text
    else:
        # Plain text, Markdown, JSON, source code (Python, JS, TS, etc.)
        try:
            extracted_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = file_bytes.decode("latin-1", errors="replace")

    # Trim to token budget
    if len(extracted_text) > MAX_ATTACHMENT_CHARS:
        extracted_text = extracted_text[:MAX_ATTACHMENT_CHARS] + f"\n\n[... Attachment truncated at {MAX_ATTACHMENT_CHARS} characters ...]"

    is_resume = is_likely_resume_text(extracted_text)
    resume_hint = (
        "This document contains resume sections (Education, Skills, Experience). "
        "For a full 4-pillar ATS benchmark and keyword optimization, you can upload it directly to Master Resume."
        if is_resume
        else None
    )

    return extracted_text.strip(), file_type, is_resume, resume_hint
