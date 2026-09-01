"""
Dedicated Test Suite for Phase 10: PDF/DOCX Post-Render Extraction & Structural Integrity Audit.
Validates:
- Real Vikas resume regression test
- Senior Principal Architect resume (executive metrics, leadership, enterprise projects)
- Fresher / Student resume (academic projects, coursework, hackathons)
- Specialized ML Engineer / Researcher resume (models, datasets, publications)
- Catches: missing content, duplicated content, replacement characters, project contamination, education contamination, broken bullets, truncation.
"""
import pytest
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.export import (
    generate_docx,
    generate_pdf,
    verify_export_against_structured_resume,
)

VIKAS_RESUME = """
VIKAS K
Davangere, Karnataka | vikas@example.com | +91 9876543210

PROFESSIONAL SUMMARY
Motivated Computer Science undergraduate with hands-on experience in Full Stack Web Development and Machine Learning.

TECHNICAL SKILLS
Languages: Python, Java, C, JavaScript, SQL
Frameworks & Tools: React.js, Node.js, Express.js, Flask, OpenCV, Docker, Git

PROJECTS
• AI Viral Analyzer (Flask, OpenCV, Python): Engineered image recognition pipeline achieving 91% classification accuracy across 5,000 images.
• ShopVerse (React.js, Node.js, MongoDB): Developed e-commerce platform supporting real-time cart checkout with Stripe.

EDUCATION
Bapuji Institute of Engineering and Technology
B.E. in Computer Science and Engineering (2023 - 2027) | CGPA: 9.1 / 10.0

CERTIFICATIONS
Smart India Hackathon Finalist 2024
"""

SENIOR_ARCHITECT_RESUME = """
ELENA ROSTOVA
Seattle, WA | elena@example.com | +1 206 555 0188 | linkedin.com/in/erostova

PROFESSIONAL SUMMARY
Principal Distributed Systems Architect with 12+ years designing planet-scale streaming data infrastructure.

TECHNICAL SKILLS
Distributed Systems: Apache Kafka, Apache Flink, gRPC, Raft, Kubernetes, AWS, Go, Rust, C++

WORK EXPERIENCE
Principal Engineer at CloudCore Technologies (2020 - Present) - Seattle, WA
• Architected multi-region streaming platform processing 4.2 million events/sec at sub-5ms p99 latency.
• Mentored 18 staff and senior engineers across 3 distributed engineering organizations.
• Reduced annual AWS compute and network egress overhead by $2.4M through zero-copy serialization.

Staff Systems Engineer at DataGrid Inc (2015 - 2020) - San Francisco, CA
• Designed distributed transactional key-value storage engine in Rust with Raft consensus.
• Led cloud migration of 1,200 database nodes without downtime.

EDUCATION
University of Washington
M.S. in Computer Science (2013 - 2015)
B.S. in Computer Engineering (2009 - 2013)

CERTIFICATIONS
AWS Certified Solutions Architect Professional
"""

FRESHER_STUDENT_RESUME = """
ROHAN MEHTA
Mumbai, India | rohan@example.com | +91 9123456780

PROFESSIONAL SUMMARY
Computer Engineering senior passionate about Mobile and Web applications.

TECHNICAL SKILLS
Languages: TypeScript, Kotlin, Dart, Python
Frameworks: Flutter, Next.js, FastAPI, PostgreSQL, Supabase

PROJECTS
• CampusBuddy (Flutter, Firebase): Mobile application adopted by 3,500 active university students for course scheduling.
• Algorithmic Visualizer (Next.js, TypeScript): Interactive graph algorithms visualizer rendered with Canvas API.

EDUCATION
Veermata Jijabai Technological Institute (VJTI)
B.Tech in Computer Engineering (2021 - 2025) | CGPA: 8.8 / 10.0

ACHIEVEMENTS
Winner, Mumbai Hackathon 2023
"""

ML_RESEARCHER_RESUME = """
DR. ARIS THORNE
Boston, MA | aris@example.com | 617-555-0144

PROFESSIONAL SUMMARY
Machine Learning Researcher specializing in Large Multimodal Foundation Models and Efficient Attention mechanisms.

TECHNICAL SKILLS
ML Frameworks: PyTorch, JAX, HuggingFace, vLLM, DeepSpeed, Triton
Specializations: Transformer Architecture, FlashAttention, Quantization, CUDA C++

WORK EXPERIENCE
Senior Research Scientist at NeuralScale Labs (2022 - Present) - Boston, MA
• Invented sparse attention pruning algorithm reducing LLM inference memory footprint by 45%.
• Deployed 70B parameter multimodal model across 256 H100 GPUs with DeepSpeed ZeRO-3.

EDUCATION
Massachusetts Institute of Technology (MIT)
Ph.D. in Computer Science & AI (2018 - 2022)
B.S. in Mathematics and Computer Science (2014 - 2018)

PUBLICATIONS
• Efficient Multimodal Attention via Token Pruning (NeurIPS 2023)
"""


def test_vikas_resume_pdf_and_docx_export_integrity():
    """
    Regression test: Real Vikas resume must export to PDF and DOCX without dropped facts,
    replacement characters, or broken structure.
    """
    profile = extract_candidate_profile(VIKAS_RESUME)
    
    # 1. Test PDF Export
    pdf_bytes = generate_pdf(profile, candidate_name="VIKAS K", template="modern")
    assert len(pdf_bytes) > 1000
    is_pdf_valid, pdf_report = verify_export_against_structured_resume(pdf_bytes, profile, file_type="pdf")
    assert is_pdf_valid is True, f"PDF integrity failure: {pdf_report}"
    assert len(pdf_report["replacement_characters"]) == 0
    assert len(pdf_report["missing_facts"]) == 0

    # 2. Test DOCX Export
    docx_bytes = generate_docx(profile, candidate_name="VIKAS K", template="modern")
    assert len(docx_bytes) > 1000
    is_docx_valid, docx_report = verify_export_against_structured_resume(docx_bytes, profile, file_type="docx")
    assert is_docx_valid is True, f"DOCX integrity failure: {docx_report}"


def test_senior_architect_resume_export_integrity():
    """
    Validates Senior Principal Architect resume export across multiple companies,
    multi-year dates, and quantified millions-dollar metrics.
    """
    profile = extract_candidate_profile(SENIOR_ARCHITECT_RESUME)
    
    pdf_bytes = generate_pdf(profile, candidate_name="ELENA ROSTOVA", template="executive")
    assert len(pdf_bytes) > 1000
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, profile, file_type="pdf")
    assert is_valid is True, f"Senior resume PDF integrity failure: {report}"


def test_fresher_student_resume_export_integrity():
    """
    Validates Fresher/Student resume export prioritizing projects and education.
    """
    profile = extract_candidate_profile(FRESHER_STUDENT_RESUME)
    
    pdf_bytes = generate_pdf(profile, candidate_name="ROHAN MEHTA", template="modern")
    assert len(pdf_bytes) > 1000
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, profile, file_type="pdf")
    assert is_valid is True, f"Fresher resume PDF integrity failure: {report}"


def test_ml_researcher_resume_export_integrity():
    """
    Validates specialized ML Researcher resume export with academic credentials.
    """
    profile = extract_candidate_profile(ML_RESEARCHER_RESUME)
    
    pdf_bytes = generate_pdf(profile, candidate_name="DR. ARIS THORNE", template="technical")
    assert len(pdf_bytes) > 1000
    is_valid, report = verify_export_against_structured_resume(pdf_bytes, profile, file_type="pdf")
    assert is_valid is True, f"ML researcher resume PDF integrity failure: {report}"
