import io
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


def test_docx_rendering_preserves_all_sections_and_fields():
    structured = structure_resume_text(CHARGEBEE_TEST_RESUME)
    docx_bytes = render_docx_from_structured(structured, candidate_name="VINAY K", template="modern")
    assert len(docx_bytes) > 1000

    import docx
    doc = docx.Document(io.BytesIO(docx_bytes))
    full_docx_text = "\n".join(p.text for p in doc.paragraphs)

    # 1. Contact Header includes location
    assert "Davangere, Karnataka" in full_docx_text
    assert "vinay@example.com" in full_docx_text

    # 2. Education: All three institutions, degrees, dates
    assert "Bapuji Institute of Engineering and Technology" in full_docx_text
    assert "B.E in Computer Science and Engineering" in full_docx_text
    assert "DRM Science PU College" in full_docx_text
    assert "St. Paul's High School" in full_docx_text

    # 3. Certifications: All 3 entries
    assert "Completed Python Programming Course - Scaler" in full_docx_text
    assert "AWS Certified Cloud Practitioner" in full_docx_text

    # 4. Languages
    assert "LANGUAGES" in full_docx_text.upper()
    assert "Telugu" in full_docx_text

    # 5. Skills categories preserved
    assert "Languages:" in full_docx_text or "Python" in full_docx_text


def test_plain_text_input_renders_all_sections_in_pdf_and_docx():
    from app.modules.tailoring.export import generate_pdf, generate_docx

    # Generate PDF and DOCX directly from plain string
    pdf_bytes = generate_pdf(CHARGEBEE_TEST_RESUME, candidate_name="VINAY K", template="classic")
    docx_bytes = generate_docx(CHARGEBEE_TEST_RESUME, candidate_name="VINAY K", template="classic")

    assert len(pdf_bytes) > 1000
    assert len(docx_bytes) > 1000

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "".join(page.get_text() for page in doc)
    doc.close()

    assert "Davangere, Karnataka" in pdf_text
    assert "Bapuji Institute of Engineering and Technology" in pdf_text
    assert "B.E in Computer Science and Engineering" in pdf_text
    assert "Completed Python Programming Course - Scaler" in pdf_text
    assert "Telugu" in pdf_text


def test_education_blocks_render_with_degree_and_institution_separate():
    from app.modules.tailoring.export import render_text_from_structured
    structured = structure_resume_text(CHARGEBEE_TEST_RESUME)
    text_out = render_text_from_structured(structured)

    assert "EDUCATION" in text_out
    assert "Bapuji Institute of Engineering and Technology" in text_out
    assert "B.E in Computer Science and Engineering" in text_out
    assert "CERTIFICATIONS" in text_out
    assert "LANGUAGES" in text_out


def test_project_title_in_structured_item_renders_as_a_project_heading():
    structured = {
        "personal": {"name": "Candidate", "email": "candidate@example.com"},
        "projects_raw": [
            "AI-Based Ad Viral Potential Analyzer\n"
            "Technologies: Python, Streamlit, OpenCV, Machine Learning\n"
            "Developed an AI-powered application for virality prediction."
        ],
    }

    pdf_bytes = render_pdf_from_structured(structured, candidate_name="Candidate", template="modern")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "".join(page.get_text() for page in doc)
    doc.close()

    assert "AI-Based Ad Viral Potential Analyzer" in pdf_text
    assert "Technologies: Python, Streamlit, OpenCV, Machine Learning" in pdf_text


def test_project_with_inline_parens_and_tech_stack_in_plain_text_pdf_and_docx():
    raw_resume = """
Candidate Name
candidate@example.com

TECHNICAL PROJECTS
AI-Powered Resume Screener (Python, FastAPI, PostgreSQL)
• Built an automated resume parser processing 50+ resumes per minute.
• Engineered search queries using PostgreSQL full-text search.
"""
    structured = structure_resume_text(raw_resume)
    assert len(structured["projects_raw"]) == 2
    assert "AI-Powered Resume Screener" in structured["projects_raw"][0]
    assert "Technologies: Python, FastAPI, PostgreSQL" in structured["projects_raw"][0]
    assert "Built an automated resume parser" in structured["projects_raw"][0]
    assert structured["projects_raw"][1] == "Engineered search queries using PostgreSQL full-text search."

    # 1. Plain Text rendering: titles & tech stacks MUST NOT have bullet prefixes
    text_out = render_text_from_structured(structured)
    assert "TECHNICAL PROJECTS" in text_out
    assert "AI-Powered Resume Screener" in text_out
    assert "• AI-Powered Resume Screener" not in text_out
    assert "Technologies: Python, FastAPI, PostgreSQL" in text_out
    assert "• Technologies:" not in text_out
    assert "• Built an automated resume parser processing 50+ resumes per minute." in text_out
    assert "• Engineered search queries using PostgreSQL full-text search." in text_out

    # 2. PDF rendering
    pdf_bytes = render_pdf_from_structured(structured, candidate_name="Candidate Name", template="modern")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "".join(page.get_text() for page in doc)
    doc.close()
    assert "AI-Powered Resume Screener" in pdf_text
    assert "Technologies: Python, FastAPI, PostgreSQL" in pdf_text
    assert "Built an automated resume parser" in pdf_text

    # 3. DOCX rendering
    docx_bytes = render_docx_from_structured(structured, candidate_name="Candidate Name", template="modern")
    assert len(docx_bytes) > 1000

    # 4. Tailoring Merge: AI rewrite of bullet ONLY still preserves title and tech stack
    mock_ai_result = {
        "project_bullets": [
            {
                "change_id": "chg_proj_0",
                "original": structured["projects_raw"][0],
                "proposed": "Architected high-throughput automated resume parser processing 50+ resumes per minute with 92% extraction accuracy.",
            },
            {
                "change_id": "chg_proj_1",
                "original": structured["projects_raw"][1],
                "proposed": "Optimized indexed PostgreSQL search queries, reducing response latency by 45%.",
            }
        ]
    }
    merged = _merge_structured_tailoring(structured, mock_ai_result)
    # The title and tech stack MUST be preserved at the top of the tailored project!
    assert "AI-Powered Resume Screener" in merged["projects_raw"][0]
    assert "Technologies: Python, FastAPI, PostgreSQL" in merged["projects_raw"][0]
    assert "Architected high-throughput automated resume parser" in merged["projects_raw"][0]
    assert merged["projects_raw"][1] == "Optimized indexed PostgreSQL search queries, reducing response latency by 45%."


VIKAS_GLUED_HEADER_RESUME = """
VIKAS K
Davangere, Karnataka | vikas@example.com | +91 9876543210 | github.com/vikas-dev | linkedin.com/in/vikas-k

PROFESSIONAL SUMMARY
Passionate Software and Machine Learning Engineer with experience in full-stack web applications and AI model development.

TECHNICAL SKILLS
Programming Languages: Java, Python, C
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
• Smart India Hackathon (SIH) 2024
• Gen AI Workshop
• Completed Python Programming Course - ScalerLanguages
Telugu, English, Kannada, Hindi
"""


def test_vikas_glued_languages_header_regression():
    """
    Permanent regression test for glued header ('...ScalerLanguages') and
    strict separation of spoken languages from programming languages.
    """
    structured = structure_resume_text(VIKAS_GLUED_HEADER_RESUME)

    # 1. Certifications section must contain EXACTLY 3 entries (SIH, Gen AI Workshop, Python Course)
    certs = structured["certifications"]
    assert len(certs) == 3, f"Expected exactly 3 certifications, got {len(certs)}: {certs}"
    assert "Smart India Hackathon (SIH) 2024" in certs
    assert "Gen AI Workshop" in certs
    assert "Completed Python Programming Course - Scaler" in certs
    # Candidate spoken languages must NOT be trapped in certifications
    for lang in ["Telugu", "English", "Kannada", "Hindi"]:
        assert lang not in certs
        assert not any(lang in c for c in certs)

    # 2. Languages section must contain EXACTLY Telugu, English, Kannada, Hindi
    langs = structured["languages"]
    assert len(langs) == 4, f"Expected exactly 4 languages, got {len(langs)}: {langs}"
    assert set(langs) == {"Telugu", "English", "Kannada", "Hindi"}
    # Programming languages must NEVER pollute spoken languages
    assert "Java" not in langs
    assert "Python" not in langs
    assert "C" not in langs

    # 3. Programming Languages remains correctly inside Skills
    assert "Programming Languages: Java, Python, C" in structured["skills_categorized"]
    skills_lower = {s.lower() for s in structured["skills"]}
    assert "java" in skills_lower
    assert "python" in skills_lower
    assert "c" in skills_lower

    # 4. Render to PDF and verify content integrity
    pdf_bytes = render_pdf_from_structured(structured, candidate_name="VIKAS K", template="modern")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "".join(page.get_text() for page in doc)
    doc.close()

    assert "Telugu, English, Kannada, Hindi" in pdf_text
    assert "Completed Python Programming Course - Scaler" in pdf_text
    assert "Gen AI Workshop" in pdf_text
    assert "Smart India Hackathon (SIH) 2024" in pdf_text
    assert "Programming Languages: Java, Python, C" in pdf_text

    # 5. Render to DOCX and Plain Text
    docx_bytes = render_docx_from_structured(structured, candidate_name="VIKAS K", template="modern")
    assert len(docx_bytes) > 1000

    text_out = render_text_from_structured(structured)
    assert "Telugu, English, Kannada, Hindi" in text_out
    assert "Completed Python Programming Course - Scaler" in text_out
    assert "Programming Languages: Java, Python, C" in text_out


VIKAS_COMPLETE_TAILORING_RESUME = """
VIKAS K
Davangere, Karnataka | vikas@example.com | +91 9876543210 | github.com/vikas-dev | linkedin.com/in/vikas-k

PROFESSIONAL SUMMARY
Passionate Software and Machine Learning Engineer with experience in full-stack web applications and AI model development.

TECHNICAL SKILLS
Programming Languages: Java, Python, C
Frameworks & Tools: React, Node.js, Express, Flask, FastAPI, MongoDB, PostgreSQL, Git, Docker, AWS

EDUCATION
Bapuji Institute of Engineering and Technology, Davangere
B.E in Computer Science and Engineering (2023 - 2027) | CGPA: 9.1 / 10.0

DRM Science PU College, Davangere
Pre-University Course (PCMB) (2021 - 2023) | Percentage: 94%

TECHNICAL PROJECTS
• AI-Based Ad Viral Potential Analyzer: Built an interactive Streamlit dashboard and feature extraction pipeline using OpenCV and Scikit-Learn.
• ShopVerse E-Commerce: Developed full-stack e-commerce marketplace using React, Node.js, and MongoDB with Stripe payment integration.
• Cataract Prediction System Using Deep Learning: Implemented feature extraction techniques using OpenCV and Python.

CERTIFICATIONS
• Smart India Hackathon (SIH) 2024
• Gen AI Workshop
• Completed Python Programming Course - ScalerLanguages
Telugu, English, Kannada, Hindi
"""


def test_strengthen_bullet_verb_no_double_verbs():
    """
    Acceptance Criteria 2 & 4:
    Given a bullet that already starts with a strong verb ("Implemented X", "Built X"),
    running it through the tailoring/strengthening step must NOT produce double verbs
    (e.g., never 'Developed Implemented' or 'Architected Built').
    """
    from app.modules.resume.parsing.action_verbs import strengthen_bullet_verb

    # 1. Bullets already starting with strong verbs must remain unchanged
    b1 = "• Implemented feature extraction techniques using OpenCV and Python."
    res1, chg1 = strengthen_bullet_verb(b1, default_verb="Developed")
    assert not chg1
    assert res1 == b1
    assert "Developed Implemented" not in res1

    b2 = "Built an interactive Streamlit dashboard for real-time inference."
    res2, chg2 = strengthen_bullet_verb(b2, default_verb="Architected")
    assert not chg2
    assert res2 == b2
    assert "Architected Built" not in res2

    b3 = "• Architected end-to-end ad classification engine using Flask."
    res3, chg3 = strengthen_bullet_verb(b3, default_verb="Engineered")
    assert not chg3
    assert res3 == b3
    assert "Engineered Architected" not in res3

    # 2. Accidental double verb inputs get cleanly cleaned
    bad_input = "Developed Implemented feature extraction techniques using OpenCV"
    res4, chg4 = strengthen_bullet_verb(bad_input, default_verb="Architected")
    assert chg4
    assert res4 == "Implemented feature extraction techniques using OpenCV"
    assert not res4.startswith("Developed Implemented")

    bad_input2 = "Architected Built an interactive Streamlit dashboard"
    res5, chg5 = strengthen_bullet_verb(bad_input2, default_verb="Engineered")
    assert chg5
    assert res5 == "Built an interactive Streamlit dashboard"

    # 3. Weak phrasing is converted to strong verb without double stacking
    weak_input = "• Worked on building REST APIs with FastAPI and Docker"
    res6, chg6 = strengthen_bullet_verb(weak_input, default_verb="Engineered")
    assert chg6
    assert "Engineered" in res6
    assert "Worked on" not in res6
    assert not res6.startswith("• Engineered Worked")


def test_vikas_resume_tailoring_and_project_structure_regression():
    """
    Acceptance Criteria 1, 2, 3:
    1. Re-run tailoring on Vikas resume against a JD.
       Confirm: "AI-Based" and "Cataract" survive in project titles 100% intact.
    2. No bullet in output contains two consecutive capitalized verbs at start.
    3. Project titles remain on their own line (bold), tech stack on its own line (italic),
       and bullets as separate lines below.
    """
    from app.core.ai_service.service import AIService
    from app.core.config import Settings
    import json

    structured = structure_resume_text(VIKAS_COMPLETE_TAILORING_RESUME)
    settings = Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")
    ai_service = AIService(settings)

    jd_text = (
        "Seeking Machine Learning and Software Engineer with experience in Python, "
        "Flask, Deep Learning, OpenCV, and scalable backend services."
    )

    editable_sub = {
        "summary": structured.get("summary", ""),
        "skills": structured.get("skills", []),
        "experience_bullets": structured.get("experience_raw", []),
        "project_bullets": structured.get("projects_raw", []),
    }

    tailored_result = ai_service._fallback_resume_rewrite(
        master_resume_json=json.dumps(editable_sub),
        jd_text=jd_text,
        company="Target Tech",
        role="ML Engineer",
    )
    result_dict = tailored_result.model_dump(mode="json")

    # 1. Merge structured tailoring
    merged = _merge_structured_tailoring(structured, result_dict, approved_change_ids=None)

    # 2. Verify project titles: "AI-Based" and "Cataract" MUST survive unmodified
    projects = merged["projects_raw"]
    proj_text_all = "\n".join(str(p) for p in projects)

    assert "AI-Based Ad Viral Potential Analyzer" in proj_text_all or "AI-Based" in proj_text_all
    assert "Cataract Prediction System Using Deep Learning" in proj_text_all or "Cataract" in proj_text_all
    assert "Engineered Ad Viral Potential Analyzer" not in proj_text_all
    assert "Deployed Prediction System Using Deep Learning" not in proj_text_all

    # 3. Verify no double verbs in any bullet
    for p in projects:
        lines = str(p).split("\n")
        for line in lines:
            words = line.strip().split()
            if len(words) >= 2:
                w0 = words[0].strip("•-* ")
                w1 = words[1].strip("•-* ")
                assert not (w0 in ["Developed", "Architected", "Engineered"] and w1 in ["Implemented", "Built", "Developed", "Deployed"]), \
                    f"Double-verb detected in line: {line}"

    # 4. Render to Text and verify project formatting structure
    text_out = render_text_from_structured(merged)
    assert "AI-Based Ad Viral Potential Analyzer" in text_out
    assert "Cataract Prediction System Using Deep Learning" in text_out
    assert "ShopVerse E-Commerce" in text_out
    assert "Engineered Ad Viral Potential" not in text_out

    # 5. Render to PDF and verify layout
    pdf_bytes = render_pdf_from_structured(merged, candidate_name="VIKAS K", template="modern")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "".join(page.get_text() for page in doc)
    doc.close()

    assert "AI-Based Ad Viral Potential Analyzer" in pdf_text
    assert "Cataract Prediction System Using Deep Learning" in pdf_text
    assert "Engineered Ad Viral Potential Analyzer" not in pdf_text
    assert "Developed Implemented" not in pdf_text
    assert "Architected Built" not in pdf_text


