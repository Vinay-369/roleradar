import pytest
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.resume.parsing.parseability import analyze_parseability
from app.modules.resume.parsing.recruiter_impact import analyze_recruiter_impact


MESSY_RESUME_1_NO_HEADERS = """
Vinay Kumar
vinay.kumar@example.com
+91 9876543210
github.com/vinayk

Passionate software engineer with hands-on experience building scalable applications.
I have built backend services using Python, FastAPI, and PostgreSQL with Redis caching.
Led development of a distributed notification service with Docker, RabbitMQ, and Celery.
Graduated with Bachelor of Technology in Computer Science from National Institute of Technology.
Awarded 1st place in National Smart India Hackathon 2024 for automated disaster response app.
"""

MESSY_RESUME_2_EXOTIC_BULLETS_AND_CATEGORIES = """
PRIYA PATEL
Email: priya.patel@work.io | Tel: +91-91234-56789
linkedin.com/in/priyapatel-dev

== CAREER SUMMARY ==
Full-stack developer with 2+ years of freelance experience delivering React and Node.js solutions.

== TECHNICAL PROFICIENCIES ==
Languages: TypeScript, JavaScript, Python, SQL
Frontend: React.js, Next.js, Redux Toolkit, TailwindCSS, HTML5/CSS3
Backend & DB: Node.js, Express, MongoDB, PostgreSQL, GraphQL
DevOps & Tools: Git, Docker, AWS S3, Jest, Postman

== WORK HISTORY ==
➢ Architected responsive customer portal using React and TypeScript, boosting mobile conversion by 28%.
➔ Implemented JWT authentication and role-based access control protecting 15,000 active user accounts.
✔ Optimized MongoDB aggregation queries reducing dashboard render latency from 1.8s to 240ms.

== ACADEMIC PROJECTS ==
1. E-Commerce Microservices Engine: Built distributed cart and checkout service using Node.js and Redis.
2. Real-time Collaborative Editor: Created WebSocket-based document editing app with operational transformation.

== EDUCATION & QUALIFICATIONS ==
B.E. in Information Technology, Mumbai University (2020 - 2024) - CGPA: 8.9/10
"""

MESSY_RESUME_3_PIPES_AND_TABLES = """
Candidate: Rohan Deshmukh
Contact: rohan.d@gmail.com | Phone: 9876501234 | Portfolio: https://rohand.dev

AREAS OF EXPERTISE:
Python | C++ | Java | Golang | Kubernetes | Terraform | AWS | Prometheus | Grafana | Linux | CI/CD

PROFESSIONAL EXPERIENCE:
| DevOps Engineer | CloudScale Systems | 2023 - Present |
- Automated AWS multi-account infrastructure deployment using Terraform and Terragrunt across 4 regions.
- Deployed Kubernetes (EKS) clusters with Helm charts, managing 80+ microservice deployments.
- Implemented centralized logging and telemetry with Prometheus, Grafana, and Loki, reducing MTTR by 45%.

PORTFOLIO PROJECTS:
- Multi-cloud Disaster Recovery Orchestrator: Automated failover pipeline between AWS and GCP with 99.99% uptime.
- GitOps Continuous Delivery Bot: Built GitHub Actions and ArgoCD automation for automated PR preview environments.

AWARDS & ACHIEVEMENTS:
- AWS Certified Solutions Architect - Associate (2024)
- Published technical paper on container security in IEEE Student Conference.
"""

MESSY_RESUME_4_NON_STANDARD_HEADERS = """
CURRICULUM VITAE

Amina Sheikh
amina.sheikh@outlook.com
+1 (555) 349-9201
https://github.com/aminas

PERSONAL PROFILE:
Junior Data Scientist and Machine Learning enthusiast with strong mathematical foundations.

KEY SKILLS:
PyTorch, TensorFlow, Scikit-Learn, Pandas, NumPy, NLP, Transformers, OpenCV, SQL, PowerBI

RELEVANT EXPERIENCE:
* Developed an NLP sentiment analysis pipeline using HuggingFace Transformers, achieving 91% F1-score on customer reviews.
* Engineered feature pipelines on 4.2M row retail transactions dataset using Pandas and DuckDB, accelerating model training time by 3.5x.
* Built computer vision defect classification model with PyTorch and ResNet50, reducing inspection false alarms by 22%.

EDUCATIONAL BACKGROUND:
Master of Science in Data Science, Stanford University (2023 - 2025)
Bachelor of Science in Mathematics & Computing (2019 - 2023)

CO-CURRICULAR & HONORS:
* Kaggle Competitions Expert (Top 2% in Global Tabular Competition)
* Dean's Honor List for Academic Excellence (2022, 2023)
"""

MESSY_RESUME_5_FRESHER_DENSE = """
ANANYA GUPTA
ananya.g@college.edu
+91 9988776655
github.com/ananyaguptaa
linkedin.com/in/ananya-gupta-cs

TECHNICAL SKILLS:
Programming: C, C++, Python, Java
Web: HTML, CSS, JavaScript, React, Node.js, Express, MongoDB
Core: Data Structures, Algorithms, DBMS, Operating Systems, Computer Networks, OOP

SELECTED PROJECTS:
• Algorithmic Trading Backtester: Built backtesting simulation platform in Python using NumPy and Pandas with 15+ quantitative indicators.
• Smart Campus Attendance System: Developed facial recognition mobile app with Flutter and OpenCV, handling 500+ daily check-ins.
• Distributed File Storage System: Implemented fault-tolerant file chunking server in Java with RAFT consensus protocol.
• AI Resume Keyword Matcher: Created TF-IDF and spaCy semantic analyzer comparing resumes to job descriptions.

EDUCATION:
B.Tech in Computer Science and Engineering
Vellore Institute of Technology (VIT)
CGPA: 9.12 / 10 (2021 - 2025)

EXTRA-CURRICULAR:
• Solved 400+ problems on LeetCode (Knight badge, 1950 rating)
• Lead Organizer of Campus Hackathon with 1200+ participants
"""


def test_messy_resume_1_no_headers_recovers_skills_and_personal():
    structured = structure_resume_text(MESSY_RESUME_1_NO_HEADERS)
    assert structured["personal"]["name"] == "Vinay Kumar"
    assert structured["personal"]["email"] == "vinay.kumar@example.com"
    assert structured["personal"]["github"] == "github.com/vinayk"
    
    # NLP fallback should extract Python, FastAPI, PostgreSQL, Docker, Redis, Celery, RabbitMQ from text
    skills_lower = {s.lower() for s in structured["skills"]}
    assert "python" in skills_lower
    assert "fastapi" in skills_lower
    assert "docker" in skills_lower
    assert len(structured["experience_raw"]) == 2
    assert any("backend services" in bullet for bullet in structured["experience_raw"])
    assert any("notification service" in bullet for bullet in structured["experience_raw"])


def test_unstructured_experience_paragraph_is_split_into_evidence_bullets():
    text = """
Candidate Name
candidate@example.com
EXPERIENCE
Built a FastAPI service for order processing. Optimized PostgreSQL queries, reducing dashboard latency by 42%. Deployed the service with Docker and GitHub Actions.
"""
    structured = structure_resume_text(text)

    assert structured["experience_raw"] == [
        "Built a FastAPI service for order processing.",
        "Optimized PostgreSQL queries, reducing dashboard latency by 42%.",
        "Deployed the service with Docker and GitHub Actions.",
    ]


def test_split_technical_skills_heading_does_not_pollute_education():
    text = """
Candidate Name
candidate@example.com
EDUCATION
Example High School
SSLC - 88% Technical
Skills
Python, Flask
"""
    structured = structure_resume_text(text)

    assert "Technical" not in " ".join(structured["education_raw"])
    assert "Python" in structured["skills"]


def test_project_title_and_stack_are_preserved_with_first_project_bullet():
    text = """
Candidate Name
candidate@example.com
PROJECTS
AI-Based Ad Viral Potential Analyzer
Python, Streamlit, OpenCV, Machine Learning
• Developed an AI-powered application for virality prediction.
• Implemented OpenCV feature extraction for video analysis.
"""
    structured = structure_resume_text(text)

    assert structured["projects_raw"][0] == (
        "AI-Based Ad Viral Potential Analyzer\n"
        "Technologies: Python, Streamlit, OpenCV, Machine Learning\n"
        "Developed an AI-powered application for virality prediction."
    )
    assert structured["projects_raw"][1] == "Implemented OpenCV feature extraction for video analysis."


def test_project_parser_handles_pdf_extracted_standalone_bullets_and_wrapped_lines():
    text = """
Candidate Name
candidate@example.com
PROJECTS
Cataract Prediction System Using Deep Learning                                  Python, TensorFlow, Keras
–
Convolutional Neural Network model using Python and TensorFlow to detect cataracts from
retinal images, achieving 91% validation accuracy.
"""
    structured = structure_resume_text(text)

    assert structured["projects_raw"] == [
        "Cataract Prediction System Using Deep Learning\n"
        "Technologies: Python, TensorFlow, Keras\n"
        "Convolutional Neural Network model using Python and TensorFlow to detect cataracts from retinal images, achieving 91% validation accuracy."
    ]


def test_messy_resume_2_exotic_bullets_and_categories():
    structured = structure_resume_text(MESSY_RESUME_2_EXOTIC_BULLETS_AND_CATEGORIES)
    assert structured["personal"]["name"] == "PRIYA PATEL"
    assert structured["personal"]["email"] == "priya.patel@work.io"
    assert structured["personal"]["linkedin"] == "linkedin.com/in/priyapatel-dev"

    # Verify bullet prefixes were stripped cleanly
    assert len(structured["experience_raw"]) >= 3
    for bullet in structured["experience_raw"]:
        assert not bullet.startswith("➢")
        assert not bullet.startswith("➔")
        assert not bullet.startswith("✔")

    # Verify categories like "Languages:" didn't pollute skill names
    skills_lower = {s.lower() for s in structured["skills"]}
    assert "typescript" in skills_lower
    assert "react" in skills_lower or "react.js" in skills_lower
    assert "languages: typescript" not in skills_lower


def test_messy_resume_3_pipes_and_tables():
    structured = structure_resume_text(MESSY_RESUME_3_PIPES_AND_TABLES)
    assert structured["personal"]["name"] == "Rohan Deshmukh"
    assert structured["personal"]["email"] == "rohan.d@gmail.com"

    skills_lower = {s.lower() for s in structured["skills"]}
    assert "kubernetes" in skills_lower
    assert "terraform" in skills_lower
    assert "aws" in skills_lower
    assert len(structured["projects_raw"]) >= 2


def test_messy_resume_4_non_standard_headers():
    structured = structure_resume_text(MESSY_RESUME_4_NON_STANDARD_HEADERS)
    assert structured["personal"]["name"] == "Amina Sheikh"
    assert structured["personal"]["email"] == "amina.sheikh@outlook.com"

    # Non-standard headers (PERSONAL PROFILE, KEY SKILLS, RELEVANT EXPERIENCE, CO-CURRICULAR & HONORS)
    assert structured["summary"] is not None
    assert len(structured["experience_raw"]) >= 3
    assert len(structured["achievements"]) >= 2

    impact = analyze_recruiter_impact(structured["experience_raw"])
    assert impact.bullets_analyzed >= 3
    assert impact.quantified_bullets >= 2
    assert impact.score >= 60


def test_messy_resume_5_fresher_dense_extraction():
    structured = structure_resume_text(MESSY_RESUME_5_FRESHER_DENSE)
    assert structured["personal"]["name"] == "ANANYA GUPTA"
    assert structured["personal"]["email"] == "ananya.g@college.edu"

    skills_lower = {s.lower() for s in structured["skills"]}
    assert "c++" in skills_lower
    assert "python" in skills_lower
    assert "react" in skills_lower

    assert len(structured["projects_raw"]) >= 4
    for proj in structured["projects_raw"]:
        assert not proj.startswith("•")

    parseability = analyze_parseability(
        text=MESSY_RESUME_5_FRESHER_DENSE,
        blocks=[],
        file_type="pdf",
        has_tables=False
    )
    assert parseability.score >= 70
    assert parseability.contact_info_found["email"] is True
