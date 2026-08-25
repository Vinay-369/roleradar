import pytest
import fitz  # PyMuPDF
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.tailoring.export import render_pdf_from_structured, render_docx_from_structured, render_text_from_structured
from app.modules.tailoring.services import _merge_structured_tailoring
from app.modules.tailoring.validation import measure_and_enforce_one_page_fit

CHARGEBEE_TEST_RESUME = """
VINAY K
Davangere, Karnataka | vinay@example.com | +91 9876543210 | github.com/vinay-dev | linkedin.com/in/vinay-k

PROFESSIONAL SUMMARY
Motivated Full Stack and Machine Learning Engineer with hands-on experience building scalable web applications and predictive ML pipelines.

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, SQL, HTML, CSS
Frameworks & Tools: React, Node.js, Express, Flask, FastAPI, MongoDB, PostgreSQL, Git, Docker, AWS

EDUCATION
Bapuji Institute of Engineering and Technology, Davangere
B.E in Computer Science and Engineering (2023 - 2027) | CGPA: 9.1 / 10.0

DRM Science PU College, Davangere
Pre-University Course (PCMB) (2021 - 2023) | Percentage: 94%

St. Paul's High School, Davangere
SSLC (10th Standard) (2021) | Percentage: 92%

TECHNICAL PROJECTS
• AI-Based Ad Analyzer: Architected end-to-end ad classification engine using Flask and Random Forest, achieving 91% accuracy across 10,000 samples.
• ShopVerse E-Commerce: Developed full-stack e-commerce marketplace using React, Node.js, and MongoDB with Stripe payment integration.
• TaskFlow Collaboration Tool: Built real-time project management dashboard using TypeScript, WebSocket, and Redis.

CERTIFICATIONS
• Completed Python Programming Course - Scaler
• AWS Certified Cloud Practitioner
• Problem Solving (Basic) - HackerRank

ACHIEVEMENTS
• 1st Place at National Level Hackathon (Smart India Hackathon 2024)
• Solved 350+ algorithmic data structures problems on LeetCode

LANGUAGES
Telugu, English, Kannada, Hindi
"""

def test_structurer_preserves_education_dates_location_certifications_languages():
    structured = structure_resume_text(CHARGEBEE_TEST_RESUME)
    
    # 1. Contact & Location
    assert structured["personal"]["location"] == "Davangere, Karnataka"
    assert structured["personal"]["name"] == "VINAY K"
    assert structured["personal"]["email"] == "vinay@example.com"
    assert structured["personal"]["phone"] == "+91 9876543210"

    # 2. Education Preservation & Non-Corruption
    edu = structured["education_raw"]
    assert len(edu) == 3, f"Expected 3 distinct education entries, got {len(edu)}: {edu}"
    
    # Check all institution names are present
    edu_text = " ".join(edu)
    assert "Bapuji Institute of Engineering and Technology" in edu_text
    assert "DRM Science PU College" in edu_text
    assert "St. Paul's High School" in edu_text
    
    # Check all 3 date ranges are preserved
    assert "2023 - 2027" in edu_text
    assert "2021 - 2023" in edu_text
    assert "2021" in edu_text
    
    # Check degree name B.E is preserved (NOT corrupted to 'E')
    assert "B.E in Computer Science and Engineering" in edu_text
    assert not edu_text.startswith("E in Computer Science")

    # 3. Certifications Preservation
    certs = structured["certifications"]
    assert len(certs) == 3
    assert "Completed Python Programming Course - Scaler" in certs
    assert "AWS Certified Cloud Practitioner" in certs
    assert "Problem Solving (Basic) - HackerRank" in certs

    # 4. Languages Preservation
    langs = structured["languages"]
    assert len(langs) == 4
    assert set(langs) == {"Telugu", "English", "Kannada", "Hindi"}


def test_pdf_rendering_preserves_all_sections_and_fields():
    structured = structure_resume_text(CHARGEBEE_TEST_RESUME)
    
    # Render modern template PDF
    pdf_bytes = render_pdf_from_structured(structured, candidate_name="VINAY K", template="modern")
    assert len(pdf_bytes) > 1000

    # Extract text from rendered PDF with PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count == 1, f"Expected 1 page, got {doc.page_count}"
    
    extracted_text = ""
    for page in doc:
        extracted_text += page.get_text()
    doc.close()

    # 1. Contact Header includes location
    assert "Davangere, Karnataka" in extracted_text

    # 2. Education: All three institutions, degrees, dates
    assert "Bapuji Institute of Engineering and Technology" in extracted_text
    assert "B.E in Computer Science and Engineering" in extracted_text
    assert "2023 - 2027" in extracted_text
    assert "DRM Science PU College" in extracted_text
    assert "2021 - 2023" in extracted_text
    assert "St. Paul's High School" in extracted_text
    assert "2021" in extracted_text

    # 3. Certifications: All 3 entries
    assert "Completed Python Programming Course - Scaler" in extracted_text
    assert "AWS Certified Cloud Practitioner" in extracted_text
    assert "Problem Solving (Basic) - HackerRank" in extracted_text

    # 4. Languages section
    assert "LANGUAGES" in extracted_text.upper()
    assert "Telugu" in extracted_text
    assert "English" in extracted_text
    assert "Kannada" in extracted_text
    assert "Hindi" in extracted_text

    # 5. Metric preservation (91% accuracy preserved)
    assert "91%" in extracted_text


def test_structured_tailoring_merge_preserves_languages_and_protected_sections():
    master_structured = structure_resume_text(CHARGEBEE_TEST_RESUME)
    
    mock_ai_result = {
        "summary": {
            "change_id": "chg_summary",
            "original": master_structured["summary"],
            "proposed": "Results-driven Software Engineer with proven expertise in developing high-availability billing APIs and ML systems.",
        },
        "skills": {
            "ordered_skills": ["Python", "FastAPI", "React", "Node.js", "Docker", "AWS", "SQL"],
            "additions": [],
        },
        "project_bullets": [
            {
                "change_id": "chg_proj_0",
                "original": master_structured["projects_raw"][0],
                "proposed": "Engineered enterprise-grade ad classification engine using Flask and Random Forest, maintaining 91% accuracy across 10,000+ transaction samples.",
            }
        ],
        "experience_bullets": [],
    }

    merged = _merge_structured_tailoring(master_structured, mock_ai_result)

    # Verify protected sections are 100% untouched
    assert merged["personal"]["location"] == "Davangere, Karnataka"
    assert len(merged["education_raw"]) == 3
    assert "Bapuji Institute of Engineering and Technology" in merged["education_raw"][0]
    assert "B.E in Computer Science" in merged["education_raw"][0]
    assert len(merged["certifications"]) == 3
    assert "Completed Python Programming Course - Scaler" in merged["certifications"]
    assert len(merged["languages"]) == 4
    assert "Telugu" in merged["languages"]


def test_one_page_trimming_never_drops_structural_sections_or_education():
    structured = structure_resume_text(CHARGEBEE_TEST_RESUME)
    
    # Add a lot of dummy project bullets to force genuine multi-page overflow
    long_projects = list(structured["projects_raw"])
    for i in range(35):
        long_projects.append(f"Architected auxiliary microservice subsystem module {i} with end-to-end automated testing and distributed database caching.")
    structured["projects_raw"] = long_projects

    # Enforce one page fit
    fitted, is_fitted, pages = measure_and_enforce_one_page_fit(structured, candidate_name="VINAY K", template="modern", max_pages=1)
    
    # Verify that trimming trimmed project bullets, NOT education, NOT certs, NOT languages, NOT personal
    assert fitted["personal"]["location"] == "Davangere, Karnataka"
    assert len(fitted["education_raw"]) == 3
    assert "Bapuji Institute of Engineering and Technology" in fitted["education_raw"][0]
    assert len(fitted["certifications"]) == 3
    assert len(fitted["languages"]) == 4
    # Project bullets should have been trimmed to fit
    assert len(fitted["projects_raw"]) < len(long_projects)
    assert is_fitted is True
    assert pages == 1
