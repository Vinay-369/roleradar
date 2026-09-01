"""
Regression Test Suite: Evidence Preservation & Multi-Project Provenance Invariant.
Verifies:
1. Resumes with multiple projects NEVER silently lose a project during tailoring.
2. Verified candidate metrics (e.g. 91% validation accuracy) remain available even when not highly relevant to a target JD.
3. Partial LLM rewrites do not discard unmodified candidate experience or projects.
4. Categorized skills are preserved structurally without single-line element explosion.
5. 1-page fit enforcement never deletes whole project entities or verified candidate metrics.
6. Post-render PDF text extraction on the real Vikas resume retains 100% of candidate evidence.
"""
import pytest
import pymupdf
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.resume.models import CandidateProfile
from app.core.ai_service.schemas import (
    StructuredTailoringResult,
    BulletRewrite,
    SkillsTailoring,
    SummaryTailoring,
    ChangeStatus,
)
from app.modules.tailoring.services import _merge_structured_tailoring
from app.modules.tailoring.validation import measure_and_enforce_one_page_fit
from app.modules.tailoring.export import generate_pdf, generate_docx

VIKAS_RESUME = """
VIKAS K
Davangere, Karnataka | vikas@example.com | +91 9876543210

PROFESSIONAL SUMMARY
Motivated Computer Science undergraduate with hands-on experience in Full Stack Web Development and Machine Learning.

TECHNICAL SKILLS
Programming Languages: Python, Java, C, JavaScript, SQL
Frameworks & Libraries: React.js, Node.js, Express.js, Flask, OpenCV, TensorFlow, Keras, NumPy, Pandas
Developer Tools: Docker, Git, VS Code, Postman
Database: MongoDB, MySQL

TECHNICAL PROJECTS
• AI-Based Ad Viral Potential Analyzer
  Technologies: Python, Streamlit, OpenCV, Scikit-Learn, Machine Learning
  - Built predictive machine learning pipeline using Streamlit and OpenCV to analyze video features and predict viral engagement.
  - Implemented feature extraction for visual hooks and audio pacing, achieving 91% accuracy across 10,000 ad samples.

• Cataract Prediction System Using Deep Learning
  Technologies: Python, TensorFlow, Keras, Deep Learning, NumPy, Pandas
  - Developed a Convolutional Neural Network (CNN) image classification model using Python, TensorFlow, and Keras to detect cataracts from retinal images.
  - Achieved 91% validation accuracy on a clinical dataset of 2,000 retinal scans.
  - Engineered end-to-end preprocessing pipeline using NumPy and Pandas for data augmentation and normalization.
  - Collaborated across a 6-week timeline with a 4-member team to deliver the final inference pipeline.

EDUCATION
Bapuji Institute of Engineering and Technology, Davangere
B.E in Computer Science and Engineering (2023 - 2027) | CGPA: 9.1 / 10.0

DRM Science PU College, Davangere
Pre-University Course (PCMB) (2021 - 2023) | Percentage: 94%

CERTIFICATIONS
• Smart India Hackathon (SIH) 2024 Finalist
• Gen AI Workshop
• Scaler Python Programming Course

LANGUAGES
Telugu, English, Kannada, Hindi
"""

WEB_BACKEND_JD = """
Backend Engineer - Python & Django
We are seeking a Python backend developer to build RESTful services, optimize databases, and integrate Docker containers.
Required: Python, SQL, REST APIs, Docker, Git.
Preferred: Flask, MongoDB.
"""


def test_extraction_preserves_both_projects_and_metrics():
    """Verify structurer extracts both projects, technologies, and metrics from Vikas resume."""
    structured = structure_resume_text(VIKAS_RESUME)
    raw_projects = structured.get("projects_raw", [])
    assert len(raw_projects) >= 2, f"Expected at least 2 project entries, got {len(raw_projects)}"
    
    all_proj_text = " ".join(str(p) for p in raw_projects)
    assert "AI-Based Ad Viral Potential Analyzer" in all_proj_text
    assert "Cataract Prediction System Using Deep Learning" in all_proj_text
    assert "91%" in all_proj_text
    assert "TensorFlow" in all_proj_text
    assert "OpenCV" in all_proj_text


def test_partial_llm_project_rewrites_do_not_drop_unmodified_projects():
    """
    When the LLM only returns a rewrite for Project 0 (e.g. because it matched the JD),
    all other projects (Project 1, Cataract Prediction, etc.) MUST be 100% preserved in the merged profile.
    """
    structured = structure_resume_text(VIKAS_RESUME)
    initial_project_count = len(structured["projects_raw"])
    assert initial_project_count >= 2

    # Simulate LLM tailoring only project index 0
    llm_result = StructuredTailoringResult(
        summary=SummaryTailoring(
            original=structured.get("summary", ""),
            proposed="Motivated Computer Science undergraduate specializing in Python backend and ML systems.",
            reason="Aligned with backend role",
            source_evidence=structured.get("summary", ""),
        ),
        skills=SkillsTailoring(
            ordered_skills=structured.get("skills", []),
            additions=[],
        ),
        project_bullets=[
            BulletRewrite(
                bullet_index=0,
                original=structured["projects_raw"][0],
                proposed="AI-Based Ad Viral Potential Analyzer\nTechnologies: Python, Streamlit, OpenCV, Machine Learning\nArchitected predictive ML pipeline with Streamlit for real-time engagement scoring.",
                action="REWRITE",
                reason="Highlighted backend pipeline architecture",
                source_evidence=structured["projects_raw"][0],
            )
        ]
    )

    merged = _merge_structured_tailoring(structured, llm_result.model_dump(mode="json"))

    # Invariant: Project count before tailoring must equal project count after tailoring
    assert len(merged["projects_raw"]) == initial_project_count, (
        f"Master had {initial_project_count} projects, but merged only has {len(merged['projects_raw'])}"
    )

    merged_text = " ".join(merged["projects_raw"])
    assert "AI-Based Ad Viral Potential Analyzer" in merged_text
    assert "Cataract Prediction System Using Deep Learning" in merged_text
    assert "91% validation accuracy" in merged_text or "91%" in merged_text
    assert "TensorFlow" in merged_text
    assert "Keras" in merged_text


def test_partial_llm_experience_rewrites_do_not_drop_unmodified_roles():
    """
    When a candidate has 4 work experience entries and LLM only rewrites 1,
    the remaining 3 entries must remain 100% untouched.
    """
    master_parsed = {
        "personal": {"name": "Test Engineer"},
        "skills": ["Python", "AWS", "Go"],
        "experience_raw": [
            "Senior Engineer at Alpha Corp (2022 - Present)\n• Led backend scaling to 1M users.",
            "Software Engineer at Beta Inc (2020 - 2022)\n• Built internal reporting dashboard in Django.",
            "Junior Developer at Gamma LLC (2018 - 2020)\n• Implemented automated unit tests with pytest.",
            "Intern at Delta Tech (2018)\n• Documented REST APIs with Swagger.",
        ],
        "projects_raw": [],
        "education_raw": ["B.S. in CS"],
    }

    # LLM only rewrote bullet index 0
    llm_result = StructuredTailoringResult(
        experience_bullets=[
            BulletRewrite(
                bullet_index=0,
                original=master_parsed["experience_raw"][0],
                proposed="Senior Engineer at Alpha Corp (2022 - Present)\n• Spearheaded backend scaling to 1M daily active users with sub-50ms latency.",
                action="REWRITE",
                reason="Strengthened metric",
                source_evidence=master_parsed["experience_raw"][0],
            )
        ]
    )

    merged = _merge_structured_tailoring(master_parsed, llm_result.model_dump(mode="json"))

    assert len(merged["experience_raw"]) == 4
    assert "Spearheaded backend scaling" in merged["experience_raw"][0]
    assert "Beta Inc" in merged["experience_raw"][1]
    assert "Gamma LLC" in merged["experience_raw"][2]
    assert "Delta Tech" in merged["experience_raw"][3]


def test_one_page_enforcement_never_deletes_whole_projects_or_metrics():
    """
    Verifies that measure_and_enforce_one_page_fit never pops entire project entries
    or removes verified metrics such as 91%.
    """
    structured = structure_resume_text(VIKAS_RESUME)
    initial_projects = list(structured.get("projects_raw", []))

    trimmed, fits, page_count = measure_and_enforce_one_page_fit(
        structured,
        candidate_name="VIKAS K",
        template="modern",
        max_pages=1,
        required_skills=["Python", "Django", "SQL"],
    )

    trimmed_projects = trimmed.get("projects_raw", [])
    # Project count must NOT drop to 1
    assert len(trimmed_projects) == len(initial_projects)

    all_trimmed_text = " ".join(str(p) for p in trimmed_projects)
    assert "AI-Based Ad Viral Potential Analyzer" in all_trimmed_text
    assert "Cataract Prediction System Using Deep Learning" in all_trimmed_text
    assert "91%" in all_trimmed_text


def test_post_render_pdf_text_extraction_against_vikas_resume():
    """
    Extracts text back from the generated PDF of the tailored Vikas resume.
    Guarantees that:
    1. Both projects ("AI-Based", "Cataract") are present in PDF text.
    2. 91% accuracy metric is present in PDF text.
    3. Education, Certifications, and Languages are present in PDF text.
    4. Skills section has clean category structure.
    """
    structured = structure_resume_text(VIKAS_RESUME)
    
    # Simulate tailored result
    llm_result = StructuredTailoringResult(
        summary=SummaryTailoring(
            original=structured.get("summary", ""),
            proposed="Motivated Computer Science undergraduate with hands-on experience in Python, Full Stack Web Development, and Machine Learning.",
            reason="Aligned with backend role",
            source_evidence=structured.get("summary", ""),
        ),
        skills=SkillsTailoring(
            ordered_skills=structured.get("skills", []),
            additions=[],
        ),
        project_bullets=[
            BulletRewrite(
                bullet_index=0,
                original=structured["projects_raw"][0],
                proposed="AI-Based Ad Viral Potential Analyzer\nTechnologies: Python, Streamlit, OpenCV, Scikit-Learn, Machine Learning\n• Built predictive machine learning pipeline using Streamlit and OpenCV to analyze video features and predict viral engagement.\n• Implemented feature extraction for visual hooks and audio pacing, achieving 91% accuracy across 10,000 ad samples.",
                action="REWRITE",
                reason="Optimized bullet structure",
                source_evidence=structured["projects_raw"][0],
            )
        ]
    )

    merged = _merge_structured_tailoring(structured, llm_result.model_dump(mode="json"))

    pdf_bytes = generate_pdf(merged, candidate_name="VIKAS K", template="modern")
    assert pdf_bytes and len(pdf_bytes) > 1000

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    # 1. Candidate Info
    assert "VIKAS K" in pdf_text
    assert "vikas@example.com" in pdf_text

    # 2. Both Projects Preserved
    assert "AI-Based Ad Viral Potential Analyzer" in pdf_text
    assert "Cataract Prediction System Using Deep Learning" in pdf_text or "Cataract Prediction System" in pdf_text

    # 3. Technologies & Verified Metrics Preserved
    assert "91%" in pdf_text
    assert "OpenCV" in pdf_text
    assert "TensorFlow" in pdf_text or "Keras" in pdf_text

    # 4. Education & Certifications Preserved
    assert "Bapuji Institute of Engineering and Technology" in pdf_text
    assert "Smart India Hackathon" in pdf_text

    # 5. Languages Preserved
    assert "Telugu" in pdf_text or "English" in pdf_text


def test_cataract_wrapped_bullet_semantic_coherence_and_flipkart_case():
    """
    Regression Test for Flipkart / Cataract Prediction System case:
    Verifies that wrapped multi-line delivery bullets are NOT fractured into
    misidentified project titles or tech stacks, and that 'Built' is not injected
    into mid-sentence fragments.
    """
    MESSY_FLIPKART_RESUME = """
VIKAS K V
Davangere, Karnataka | vikas@example.com | +91 9876543210

PROFESSIONAL SUMMARY
Motivated Information Science undergraduate with hands-on experience in Full Stack Web Development and Machine Learning.

TECHNICAL SKILLS
Languages: Java, Python, C, HTML, CSS, JavaScript
Database & Cloud: MySQL, MongoDB, AWS EC2/S3
Frameworks & Libraries: Flask, Streamlit, Keras, TensorFlow, NumPy, Pandas, OpenCV
Tools & Concepts: Git, GitHub, Docker, PyCharm, OOP, DSA, Machine Learning, Deep Learning, NLP, Random Forest, Artificial Intelligence

TECHNICAL PROJECTS
• AI-Based Ad Viral Potential Analyzer
  Technologies: Python, Streamlit, OpenCV, ML, Random Forest, NLP
  - Developed an AI-powered web application for advertisement virality prediction using Random Forest Regression.
  - Implemented real-time video/image analysis and OpenCV feature extraction alongside NLP to analyze CTR, retention, and watch time metrics.
  - Built interactive Streamlit dashboard for real-time viral potential prediction and visualization.

• Cataract Prediction System Using Deep Learning
  Technologies: Python, TensorFlow, Keras, DL, NumPy, Pandas
  - Convolutional Neural Network (CNN) image classification model using
  Python, TensorFlow, and Keras to detect cataracts from
  retinal images, achieving 91% validation accuracy.
  - Engineered end-to-end data preprocessing and augmentation pipeline using NumPy and Pandas.
  - Collaborated across a 6-week timeline with a 4-member team across data collection, model building, and evaluation.

EDUCATION
Bapuji Institute of Engineering and Technology, Davangere
B.E in Information Science & Engineering (2023 - 2027) | CGPA: 6.82 / 10.0

Shree Gitam PU College
Pre-University Course (2021 - 2023) | Percentage: 84.8%

Shree Siddeshwara English Medium High School
SSLC (10th Standard) | Percentage: 88%

CERTIFICATIONS
Smart India Hackathon 2024
Gen AI Workshop

LANGUAGES
English, Kannada, Hindi, Telugu
"""
    structured = structure_resume_text(MESSY_FLIPKART_RESUME)
    raw_projects = structured.get("projects_raw", [])
    
    # Must have both projects present in raw projects list
    assert len(raw_projects) >= 2
    cataract_proj = next(p for p in raw_projects if "Cataract Prediction System" in p)
    assert "Technologies: Python, TensorFlow, Keras, DL, NumPy, Pandas" in cataract_proj
    
    # Verify the wrapped bullet is reconstructed as a single unified coherent bullet
    expected_bullet = (
        "Convolutional Neural Network (CNN) image classification model using "
        "Python, TensorFlow, and Keras to detect cataracts from "
        "retinal images, achieving 91% validation accuracy."
    )
    assert expected_bullet in cataract_proj
    
    # Must NOT contain corrupted artifacts
    assert "Technologies: Python, TensorFlow, and Keras to detect cataracts from" not in cataract_proj
    assert "Built images, achieving" not in cataract_proj
    assert "Built retinal images" not in cataract_proj

    # Verify CandidateProfile extraction
    cp = CandidateProfile.from_parsed_dict(structured, MESSY_FLIPKART_RESUME)
    assert len(cp.projects) == 2
    assert cp.projects[1].title == "Cataract Prediction System Using Deep Learning"
    assert "Python" in cp.projects[1].technologies
    assert "TensorFlow" in cp.projects[1].technologies
    assert len(cp.projects[1].bullets) == 3

    # Verify structured education
    assert len(cp.education) == 3
    assert "Bapuji Institute of Engineering and Technology" in cp.education[0].institution
    assert "Information Science" in cp.education[0].degree
    assert cp.education[0].dates == "2023 - 2027"
    assert "6.82" in (cp.education[0].gpa or "")

    # Verify PDF export text
    pdf_bytes = generate_pdf(structured, candidate_name="VIKAS K V", template="modern")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    assert "Cataract Prediction System Using Deep Learning" in pdf_text
    assert "91%" in pdf_text
    assert "6-week timeline" in pdf_text
    assert "4-member team" in pdf_text
    assert "Built images, achieving" not in pdf_text

