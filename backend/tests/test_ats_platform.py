import pytest
from app.modules.intelligence.ats_platform import (
    ATSPlatform,
    detect_platform_from_url,
    evaluate_platform_compliance,
)
from app.modules.intelligence.ats_score import compute_ats_score
from app.modules.tailoring.export import generate_pdf, generate_docx


def test_detect_platform_from_url():
    assert detect_platform_from_url("https://adobe.myworkdayjobs.com/en-US/careers/job/123") == ATSPlatform.WORKDAY
    assert detect_platform_from_url("https://tcs.taleo.net/careersection/jobdetail.ftl?job=456") == ATSPlatform.TALEO
    assert detect_platform_from_url("https://boards.greenhouse.io/stripe/jobs/789") == ATSPlatform.GREENHOUSE
    assert detect_platform_from_url("https://jobs.lever.co/figma/abc") == ATSPlatform.LEVER
    assert detect_platform_from_url("https://careers-microsoft.icims.com/jobs/999") == ATSPlatform.ICIMS
    assert detect_platform_from_url("https://example.com/apply") == ATSPlatform.GENERIC


def test_platform_compliance_workday():
    resume_text = "Python FastAPI Docker PostgreSQL React"
    parseability = {
        "score": 90,
        "likely_multi_column": True,
        "missing_standard_sections": ["EDUCATION"],
        "contact_info_found": {"email": True, "phone": True, "links": True},
        "word_count": 400,
    }
    res = evaluate_platform_compliance(resume_text, parseability, ATSPlatform.WORKDAY, keyword_density=3.5)
    assert res["platform"] == "workday"
    assert res["platform_name"] == "Workday"
    # Should have warnings for multi-column, density ceiling, and missing sections
    warning_titles = [w["title"] for w in res["warnings"]]
    assert any("Multi-Column" in t for t in warning_titles)
    assert any("Density" in t for t in warning_titles)


def test_platform_compliance_taleo():
    parseability = {
        "score": 85,
        "likely_multi_column": True,
        "missing_standard_sections": ["EXPERIENCE"],
        "contact_info_found": {"email": True, "phone": True, "links": False},
        "word_count": 350,
    }
    res = evaluate_platform_compliance("text", parseability, ATSPlatform.TALEO)
    assert res["platform"] == "taleo"
    assert len(res["warnings"]) >= 2


def test_keyword_density_and_ideal_match_guidance():
    resume_text = (
        "Experienced Backend Developer with Python, FastAPI, Docker, and PostgreSQL. "
        "Built distributed microservices, REST APIs, and database schemas with Python and FastAPI."
    )
    jd_text = (
        "Looking for a Backend Developer skilled in Python, FastAPI, Docker, and PostgreSQL. "
        "Experience building scalable APIs and database architectures."
    )

    score = compute_ats_score(
        resume_text=resume_text,
        jd_text=jd_text,
        parseability_score=95,
        recruiter_impact_score=90,
        skill_match_score=85,
        role_match_score=80,
    )

    assert score.keyword_coverage > 0
    assert score.keyword_density > 0
    assert score.match_guidance is not None
    assert score.match_guidance.target_range == "75% - 85%"


def test_multi_template_exports():
    sample_resume = (
        "Jane Doe\njane@example.com · 9876543210 · linkedin.com/in/janedoe\n\n"
        "EXPERIENCE\n"
        "Senior Software Engineer at Acme Corp\n"
        "• Architected distributed systems handling 50k requests/sec\n"
        "• Led team of 5 backend engineers\n\n"
        "SKILLS\n"
        "Python, FastAPI, Docker, Kubernetes, AWS\n\n"
        "EDUCATION\n"
        "B.Tech in Computer Science, 2021\n"
    )

    for tmpl in ["modern", "classic", "technical"]:
        pdf_data = generate_pdf(sample_resume, "Jane Doe", template=tmpl)
        assert len(pdf_data) > 500
        assert pdf_data.startswith(b"%PDF")

        docx_data = generate_docx(sample_resume, "Jane Doe", template=tmpl)
        assert len(docx_data) > 500
        assert docx_data.startswith(b"PK")  # ZIP header for DOCX
