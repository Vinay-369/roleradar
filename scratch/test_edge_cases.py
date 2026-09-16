import sys
import os
import fitz
from docx import Document
import io

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.tailoring.export import generate_pdf, generate_docx
from app.modules.tailoring.validation import (
    detect_fabricated_claims,
    detect_unsupported_metrics,
    detect_unsupported_action_verbs_and_scope,
    validate_final_tailored_resume,
)

edge_resumes = [
    {
        "name": "Empty experience (pure fresher)",
        "data": {
            "personal": {"name": "Pure Fresher", "email": "fresher@edu.in"},
            "summary": "Recent graduate eager to learn.",
            "skills": ["Python", "Java", "SQL"],
            "experience_raw": [],
            "projects_raw": ["Capstone Project\n• Built automated attendance system."],
            "education_raw": ["State College\nB.Tech Computer Science (2020-2024)"],
        }
    },
    {
        "name": "Extremely long skill list & special unicode",
        "data": {
            "personal": {"name": "Unicode Candidate — 李雷 & Mária ⚡", "email": "candidate@domain.com"},
            "summary": "Specialist in «distributed systems» & high-throughput pipelines. 100% resilient.",
            "skills": [f"Skill-{i}" for i in range(50)],
            "experience_raw": [
                "TechCorp — Senior Engineer\n• Deployed systems with €500M scale & 99.99% uptime.\n• Implemented UTF-8 pipelines handling emojis 🚀 and accents é, ñ, ü."
            ],
            "projects_raw": [
                "Extremely Long Project Name That Goes On And On Across Multiple Lines To Test Structural Integrity And Wrapping\nTechnologies: Python, Redis\n• Handled large-scale jobs with 10k tasks/sec."
            ],
            "education_raw": [
                "International University of Science & Technology — School of Advanced Computational Mathematics & Theoretical Computer Science\nDoctor of Philosophy in Artificial Intelligence & Computational Linguistics (2018 - 2023)\nDissertation: Deep Hierarchical Attention Networks"
            ],
            "certifications": ["Certified Kubernetes Administrator (CKA)"],
        }
    },
    {
        "name": "Missing summary, URLs and empty optional fields",
        "data": {
            "personal": {
                "name": "Anonymous Dev",
                "github": "https://github.com/anon-dev/repo-test-1234",
                "portfolio": "https://portfolio.dev/projects?id=99",
            },
            "summary": "",
            "skills": ["Go", "Docker"],
            "experience_raw": [
                "Cloud Solutions Inc.\n• Maintained servers at https://cloud.internal.net."
            ],
            "projects_raw": [],
            "education_raw": [],
        }
    }
]

print("--- RUNNING EDGE CASE TESTS ---")
for tc in edge_resumes:
    print(f"\nTesting: {tc['name']}")
    for template in ["modern", "classic", "executive", "harvard"]:
        # Test PDF
        pdf_bytes = generate_pdf(tc["data"], candidate_name=tc["data"].get("personal", {}).get("name", "Candidate"), template=template)
        assert len(pdf_bytes) > 500, f"PDF export too short for {template}"
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert pdf_doc.page_count >= 1
        pdf_doc.close()

        # Test DOCX
        docx_bytes = generate_docx(tc["data"], candidate_name=tc["data"].get("personal", {}).get("name", "Candidate"), template=template)
        assert len(docx_bytes) > 1000, f"DOCX export too short for {template}"
        doc = Document(io.BytesIO(docx_bytes))
        assert len(doc.paragraphs) >= 1

    print(f"  Passed for all 4 templates in PDF & DOCX")

print("\nALL EDGE CASES PASSED WITH 100% ROBUSTNESS!")
