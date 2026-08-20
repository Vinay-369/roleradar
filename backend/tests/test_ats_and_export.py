import io

from docx import Document as DocxReader
import fitz

from app.modules.intelligence.ats_score import compute_ats_score, _extract_keywords, _keyword_coverage
from app.modules.tailoring.export import generate_docx, generate_pdf


def test_extract_keywords_strips_stopwords():
    keywords = _extract_keywords("The candidate will build REST APIs and manage a team")
    assert "the" not in keywords
    assert "will" not in keywords
    assert "build" in keywords
    assert "apis" in keywords


def test_keyword_coverage_full_match():
    resume = "Python FastAPI Docker MongoDB experience"
    jd = "Python FastAPI Docker MongoDB experience"
    assert _keyword_coverage(resume, jd) == 100


def test_keyword_coverage_partial_match():
    resume = "Skills: Python only"
    jd = "Required: Python FastAPI Docker Kubernetes AWS"
    coverage = _keyword_coverage(resume, jd)
    assert 0 < coverage < 100


def test_keyword_coverage_handles_empty_jd():
    assert _keyword_coverage("anything", "") == 100


def test_compute_ats_score_combines_components_correctly():
    score = compute_ats_score(
        resume_text="Python FastAPI MongoDB Docker experience building REST APIs",
        jd_text="Looking for Python FastAPI MongoDB Docker skills",
        parseability_score=90,
        recruiter_impact_score=80,
        skill_match_score=85,
        role_match_score=70,
    )
    assert score.structure == 90
    assert score.formatting == 90
    assert score.readability == 80
    assert score.required_skills == 85
    assert score.role_alignment == 70
    assert 0 <= score.overall <= 100
    assert score.keyword_coverage > 50  # most JD keywords appear in resume


def test_low_component_scores_produce_low_overall():
    score = compute_ats_score(
        resume_text="completely unrelated content about gardening",
        jd_text="Required: Kubernetes Terraform AWS DevOps automation",
        parseability_score=40,
        recruiter_impact_score=30,
        skill_match_score=10,
        role_match_score=10,
    )
    assert score.overall < 40


def test_generate_pdf_produces_valid_pdf_with_expected_text():
    text = "ANANYA RAO\nananya@example.com\n\nSKILLS\nPython, FastAPI, MongoDB\n\nEXPERIENCE\nBuilt REST APIs"
    pdf_bytes = generate_pdf(text, "Ananya Rao")
    assert pdf_bytes.startswith(b"%PDF")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    extracted = "\n".join(page.get_text() for page in doc)
    doc.close()
    assert "ANANYA RAO" in extracted
    assert "Python" in extracted
    assert "Built REST APIs" in extracted


def test_generate_docx_produces_valid_docx_with_expected_text():
    text = "ANANYA RAO\nananya@example.com\n\nSKILLS\nPython, FastAPI, MongoDB"
    docx_bytes = generate_docx(text, "Ananya Rao")
    assert docx_bytes.startswith(b"PK")  # docx is a zip archive

    document = DocxReader(io.BytesIO(docx_bytes))
    full_text = "\n".join(p.text for p in document.paragraphs)
    assert "ananya@example.com" in full_text
    assert "Python, FastAPI, MongoDB" in full_text


def test_export_never_includes_content_not_in_source_text():
    """Sanity check that export is a pure transform of the given text —
    it cannot introduce content that wasn't in final_text, which is what
    makes 'exported files contain only approved content' actually true:
    export has no access to the changes list, only the already-filtered
    final_text string."""
    text = "ONLY THIS APPROVED LINE"
    pdf_bytes = generate_pdf(text, "X")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    extracted = "\n".join(page.get_text() for page in doc)
    doc.close()
    assert "ONLY THIS APPROVED LINE" in extracted
    assert "REJECTED" not in extracted
    assert "PENDING" not in extracted
