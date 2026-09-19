import sys
import os
import fitz
from docx import Document

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.tailoring.export import generate_pdf, generate_docx

test_resume = {
    "personal": {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0199",
        "location": "San Francisco, CA",
        "linkedin": "linkedin.com/in/janedoe",
        "github": "github.com/janedoe",
    },
    "summary": "Full Stack Software Engineer with expertise in Python, React, and PostgreSQL.",
    "skills": ["Python", "React", "TypeScript", "PostgreSQL", "FastAPI", "Docker", "Redis"],
    "experience_raw": [
        "TechCorp — San Francisco, CA\nSoftware Engineer (2022 - Present)\n• Developed REST APIs using FastAPI and PostgreSQL, serving 100k daily requests.\n• Optimized React frontend state management, reducing bundle size by 25%.\n• Containerized microservices using Docker and automated CI/CD deployment pipelines."
    ],
    "projects_raw": [
        "Distributed Task Queue\nTechnologies: Python, Redis, Docker\n• Engineered an asynchronous task queue handling 5,000 tasks/second with Redis.\n• Implemented exponential backoff and dead-letter queue for resilient job execution."
    ],
    "education_raw": [
        "University of California, Berkeley\nB.S. in Computer Science (2018 - 2022)\nGPA: 3.8 / 4.0"
    ],
    "certifications": [
        "AWS Certified Solutions Architect - Associate"
    ],
    "achievements": [
        "1st Place, UC Berkeley Hackathon 2021"
    ]
}

templates = ["modern", "classic", "executive", "harvard"]
results = {}

for t in templates:
    pdf_bytes = generate_pdf(test_resume, candidate_name="Jane Doe", template=t)
    docx_bytes = generate_docx(test_resume, candidate_name="Jane Doe", template=t)
    
    # Check PDF
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_pages = pdf_doc.page_count
    pdf_text = "".join(p.get_text() for p in pdf_doc)
    pdf_doc.close()
    
    # Check DOCX
    import io
    docx_doc = Document(io.BytesIO(docx_bytes))
    docx_paragraphs = len(docx_doc.paragraphs)
    docx_font = docx_doc.styles["Normal"].font.name
    
    results[t] = {
        "pdf_bytes_len": len(pdf_bytes),
        "pdf_pages": pdf_pages,
        "docx_bytes_len": len(docx_bytes),
        "docx_paragraphs": docx_paragraphs,
        "docx_font": docx_font,
    }

print("TEMPLATE TEST RESULTS:")
for t, r in results.items():
    print(f"Template '{t}': PDF bytes={r['pdf_bytes_len']}, pages={r['pdf_pages']} | DOCX font={r['docx_font']}, bytes={r['docx_bytes_len']}")

# Compare executive vs harvard vs classic
print("\nPDF Equality check:")
pdf_classic = generate_pdf(test_resume, template="classic")
pdf_exec = generate_pdf(test_resume, template="executive")
pdf_harvard = generate_pdf(test_resume, template="harvard")
print(f"classic == executive PDF? {pdf_classic == pdf_exec}")
print(f"classic == harvard PDF? {pdf_classic == pdf_harvard}")
print(f"executive == harvard PDF? {pdf_exec == pdf_harvard}")

docx_classic = generate_docx(test_resume, template="classic")
docx_exec = generate_docx(test_resume, template="executive")
docx_harvard = generate_docx(test_resume, template="harvard")
print(f"classic == executive DOCX length? {len(docx_classic) == len(docx_exec)}")
print(f"classic == harvard DOCX length? {len(docx_classic) == len(docx_harvard)}")
