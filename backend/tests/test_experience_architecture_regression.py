import pytest
from app.modules.resume.parsing.structurer import (
    _clean_raw_text_artifacts,
    _split_into_sections,
    structure_resume_text,
    extract_candidate_profile,
    _bulletize,
)
from app.modules.resume.parsing.action_verbs import strengthen_bullet_verb


AKHIL_RANA_RESUME = """AKHIL RANA
akhil.rana@example.com | +91 9876543210 | Bengaluru, India | linkedin.com/in/akhil-rana

PROFESSIONAL SUMMARY
Experienced Senior Software Engineer with 4+ years of expertise in system software, macOS/iOS client engineering, cloud infrastructure, and full-stack development.

TECHNICAL SKILLS
Languages: Python, Swift, Objective-C, Go, JavaScript, TypeScript, C++, Shell
Frameworks & Tools: FastAPI, React, Node.js, Docker, Kubernetes, AWS, CoreWLAN, Git, CI/CD, Terraform
Databases: PostgreSQL, Redis, MongoDB, MySQL

WORK EXPERIENCE
Juniper Networks
Software Engineer - 3 (April 2024 - Present)
Software Engineer - 2 (April 2022 - March 2024)
Software Engineer Intern (January 2022 - March 2022)
Bengaluru, India

Marvis Client - MacOS/iOS Development:
• Maintained and enhanced the Marvis Client daemon application for macOS and iOS, delivering enterprise telemetry collection using CoreWLAN and system APIs.
• Architected automated network onboarding workflows supporting 40k monthly active users across Fortune 500 enterprise deployments.
• Built Marvis-CLI diagnostic utility in Swift, reducing network troubleshooting time for IT administrators by 70%.

Application Infrastructure & Packaging:
• Architected modular application packaging pipelines, achieving a 99.8% installer success rate across diverse macOS environments.
• Optimized binary build sizes with a 65% package-size reduction through dynamic framework linkage and asset pruning.
• Automated CI/CD and release pipelines via GitHub Actions and Jenkins, reducing release cycle duration from 3 hours to 10 minutes (90% manual effort reduction).

Indoor Location SDK & Platform:
• Engineered real-time indoor location tracking SDK components handling high-frequency telemetry packets.
• Integrated Bluetooth Low Energy (BLE) and Wi-Fi signal processing algorithms, improving location accuracy by 35%.

Full-Stack Development & Microservices (Freelance / Advisory):
• Led development of a full-stack scheduling and payment platform using FastAPI, React, and PostgreSQL, processing $200k+ transactions.
• Optimized database indexing and query execution plans, delivering a 45% page-load improvement.
• Consolidated third-party API dependencies, achieving an 80% SaaS spend reduction for the client.

EDUCATION
Bachelor of Technology in Computer Science and Engineering (2018 - 2022)
National Institute of Technology — CGPA: 8.8 / 10.0
"""


def test_experience_trace():
    cleaned = _clean_raw_text_artifacts(AKHIL_RANA_RESUME)
    lines = cleaned.split("\n")
    sections = _split_into_sections(lines)
    exp_lines = sections.get("experience", [])
    
    # 1. Verify structured experience lines
    struct = structure_resume_text(cleaned)
    exp_raw = struct.get("experience_raw", [])
    assert "Juniper Networks" in exp_raw
    assert any("Software Engineer - 3" in x for x in exp_raw)
    assert any("Software Engineer - 2" in x for x in exp_raw)
    assert any("Software Engineer Intern" in x for x in exp_raw)
    assert any("Marvis Client - MacOS/iOS Development:" in x for x in exp_raw)
    assert any("Application Infrastructure & Packaging:" in x for x in exp_raw)
    assert any("99.8%" in x for x in exp_raw)
    assert any("65%" in x for x in exp_raw)
    assert any("40k" in x for x in exp_raw)
    assert any("$200k+" in x for x in exp_raw)

    # 2. Verify canonical CandidateProfile
    profile = extract_candidate_profile(cleaned)
    assert len(profile.experience) >= 1
    exp = profile.experience[0]
    assert exp.company == "Juniper Networks"
    assert exp.role == "Software Engineer - 3"
    assert exp.dates == "April 2024 - Present"
    assert exp.location == "Bengaluru, India"
    
    # Verify progression
    assert len(exp.progression) == 3
    assert exp.progression[0].title == "Software Engineer - 3"
    assert exp.progression[0].dates == "April 2024 - Present"
    assert exp.progression[1].title == "Software Engineer - 2"
    assert exp.progression[1].dates == "April 2022 - March 2024"
    assert exp.progression[2].title == "Software Engineer Intern"
    assert exp.progression[2].dates == "January 2022 - March 2022"

    # Verify responsibility groups
    assert len(exp.responsibility_groups) == 4
    headings = [g.heading for g in exp.responsibility_groups]
    assert "Marvis Client - MacOS/iOS Development:" in headings
    assert "Application Infrastructure & Packaging:" in headings
    assert "Indoor Location SDK & Platform:" in headings
    assert "Full-Stack Development & Microservices (Freelance / Advisory):" in headings

    # Verify all 11 bullets preserved
    assert len(exp.bullets) == 11
    all_text = " ".join(exp.bullets)
    assert "99.8%" in all_text
    assert "65%" in all_text
    assert "3 hours to 10 minutes" in all_text or "3 hours" in all_text
    assert "90%" in all_text
    assert "40k" in all_text
    assert "35%" in all_text
    assert "$200k+" in all_text
    assert "45%" in all_text
    assert "80%" in all_text
    assert "70%" in all_text

    # 3. Verify downstream fallback rewrite
    from app.core.ai_service.service import AIService
    from app.core.config import get_settings
    ai_service = AIService(settings=get_settings())
    jd_text = "We are seeking a Senior Systems Engineer with macOS/iOS experience, Swift, Python, and CI/CD."
    rewrite_res = ai_service._fallback_resume_rewrite(struct, jd_text, role="Senior Systems Engineer", company="TechCorp")
    assert rewrite_res.experience_bullets
    
    for r in rewrite_res.experience_bullets:
        # Guarantee no mangling of category headings or progression
        if r.original.endswith(":"):
            assert r.proposed == r.original, f"Heading was modified: {r.proposed}"
            assert r.action == "KEEP"
        if "Software Engineer" in r.original and ("2024" in r.original or "2022" in r.original):
            assert r.proposed == r.original, f"Role progression was modified: {r.proposed}"
            assert r.action == "KEEP"
        # Guarantee no 'Developed a software Engineer' or 'Engineered a marvis Client'
        assert not r.proposed.lower().startswith("developed a software engineer")
        assert not r.proposed.lower().startswith("engineered a marvis client")
        assert not r.proposed.lower().startswith("implemented a application infrastructure")
        assert not r.proposed.lower().startswith("built a full-stack development")


VIKAS_RESUME = """VIKAS
vikas@example.com | +91 9123456780 | Bengaluru, India

SKILLS
Languages: Python, C++, SQL
Frameworks & Libraries: TensorFlow, Keras, OpenCV, Streamlit, NumPy, Pandas, Scikit-learn

PROJECTS
AI-Based Ad Viral Potential Analyzer
Python, Streamlit, OpenCV, ML
• Developed an AI tool to predict ad virality using computer vision and engagement signals.
• Built an interactive Streamlit dashboard for real-time video upload and scoring.

Cataract Prediction System Using Deep Learning
Python, TensorFlow, Keras, DL
• Convolutional Neural Network (CNN) image classification model using Python, TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy.
• Engineered image preprocessing pipeline with NumPy and Pandas.
• Delivered project within 6-week timeline in 4-member team.

EDUCATION
Bachelor of Technology in Computer Science
Visvesvaraya Technological University — 2024
"""


def test_vikas_fresher_projects_no_regression():
    cleaned = _clean_raw_text_artifacts(VIKAS_RESUME)
    struct = structure_resume_text(cleaned)
    profile = extract_candidate_profile(cleaned)

    assert len(profile.projects) == 2
    cataract = next(p for p in profile.projects if "Cataract" in p.title)
    assert cataract.title == "Cataract Prediction System Using Deep Learning"
    assert any("91%" in b for b in cataract.bullets)
    assert any("retinal images" in b for b in cataract.bullets)


AKHIL_RANA_WRAPPED_PDF_RESUME = """AKHIL RANA
akhil.rana@example.com | +91 9876543210 | Bengaluru, India | linkedin.com/in/akhil-rana

PROFESSIONAL SUMMARY
Experienced Senior Software Engineer with 4+ years of expertise in system software, macOS/iOS client engineering, cloud infrastructure, and full-stack development.

TECHNICAL SKILLS
Languages: Python, Swift, Objective-C, Go, JavaScript, TypeScript, C++, Shell
Frameworks & Tools: FastAPI, React, Node.js, Docker, Kubernetes, AWS, CoreWLAN, Git, CI/CD, Terraform
Databases: PostgreSQL, Redis, MongoDB, MySQL

WORK EXPERIENCE
Juniper Networks
Software Engineer - 3 (April 2024 - Present)
Software Engineer - 2 (April 2022 - March 2024)
Software Engineer Intern (January 2022 - March 2022)
Bengaluru, India

Marvis Client - MacOS/iOS Development:
• Maintained and enhanced Marvis Client applications for enterprise Wi-Fi
environments using SwiftUI and UIKit.
• Implemented telemetry collection using CoreWLAN frameworks and system profiler
commands to capture network performance metrics.
• Built automated network onboarding workflows with SCEP certificate
enrollment and credential provisioning.
• Developed Marvis-CLI tool for network diagnostics, log collection, non-UI based configuration and MDM integration.
• Created silent auto-upgrade mechanisms for BYOD devices using authenticated helper tools and privilege escalation.
• For iOS, implemented network onboarding using Network Extension frameworks and enterprise configuration profiles.

Application Infrastructure & Packaging: Architected modular application packaging pipelines,
achieving a 99.8% installer success rate across diverse macOS environments.
• Optimized binary build sizes with a 65% package-size reduction through dynamic framework linkage and asset pruning.
• Automated CI/CD and release pipelines via GitHub Actions and Jenkins, reducing release cycle duration from 3 hours to 10 minutes (90% manual effort reduction).

Indoor Location SDK & Platform:
• Engineered real-time indoor location tracking SDK components handling high-frequency telemetry packets.
• Integrated Bluetooth Low Energy (BLE) and Wi-Fi signal processing algorithms, improving location accuracy by 35%.

Full-Stack Development & Microservices (Freelance / Advisory):
• Led development of a full-stack scheduling and payment platform using FastAPI, React, and PostgreSQL, processing $200k+ transactions.
• Optimized database indexing and query execution plans, delivering a 45% page-load improvement.
• Consolidated third-party API dependencies, achieving an 80% SaaS spend reduction for the client.

EDUCATION
Bachelor of Technology in Computer Science and Engineering (2018 - 2022)
National Institute of Technology — CGPA: 8.8 / 10.0
"""


def test_experienced_resume_wrapped_lines_pdf_regression():
    """
    [REGRESSION] Tests physical PDF line wrapping on dense experienced resume (Akhil Rana).
    Guarantees:
    1. Wrapped lines are merged into complete semantic units before tailoring.
    2. Inline responsibility headings (e.g. 'Application Infrastructure & Packaging: Architected...')
       are cleanly separated into a structured heading and first bullet.
    3. Fragments are NEVER turned into independent bullets (e.g. no 'Built a environments...',
       'Engineered a commands...', 'Built a enrollment...').
    4. Metrics (99.8%, 65%, 3 hours to 10 minutes, 90%, 35%, $200k+, 45%, 80%) remain attached to correct evidence.
    """
    profile = extract_candidate_profile(AKHIL_RANA_WRAPPED_PDF_RESUME)
    
    assert len(profile.experience) >= 1
    exp = profile.experience[0]
    assert exp.company == "Juniper Networks"
    assert len(exp.progression) == 3
    
    # Check Responsibility Groups
    assert len(exp.responsibility_groups) == 4
    
    # Group 1: Marvis Client
    marvis_grp = exp.responsibility_groups[0]
    assert "Marvis Client" in marvis_grp.heading
    assert len(marvis_grp.bullets) == 6
    assert marvis_grp.bullets[0] == "Maintained and enhanced Marvis Client applications for enterprise Wi-Fi environments using SwiftUI and UIKit."
    assert marvis_grp.bullets[1] == "Implemented telemetry collection using CoreWLAN frameworks and system profiler commands to capture network performance metrics."
    assert marvis_grp.bullets[2] == "Built automated network onboarding workflows with SCEP certificate enrollment and credential provisioning."
    assert marvis_grp.bullets[3] == "Developed Marvis-CLI tool for network diagnostics, log collection, non-UI based configuration and MDM integration."
    assert marvis_grp.bullets[4] == "Created silent auto-upgrade mechanisms for BYOD devices using authenticated helper tools and privilege escalation."
    assert marvis_grp.bullets[5] == "For iOS, implemented network onboarding using Network Extension frameworks and enterprise configuration profiles."

    # Group 2: Application Infrastructure & Packaging
    infra_grp = exp.responsibility_groups[1]
    assert "Application Infrastructure & Packaging" in infra_grp.heading
    assert len(infra_grp.bullets) == 3
    assert infra_grp.bullets[0] == "Architected modular application packaging pipelines, achieving a 99.8% installer success rate across diverse macOS environments."
    assert "99.8%" in infra_grp.bullets[0]
    assert "65%" in infra_grp.bullets[1]
    assert "3 hours to 10 minutes" in infra_grp.bullets[2] or "90%" in infra_grp.bullets[2]

    # Check that NO evidence unit in the entire profile is a wrapped fragment
    for ev in profile.evidence_units:
        assert not ev.text.strip().lower().startswith("environments using swiftui")
        assert not ev.text.strip().lower().startswith("commands to capture network")
        assert not ev.text.strip().lower().startswith("enrollment and credential")
        assert not ev.text.strip().lower().startswith("achieving a 99.8%")
        assert not ev.text.strip().lower().startswith("built a environments")
        assert not ev.text.strip().lower().startswith("engineered a commands")
        assert not ev.text.strip().lower().startswith("built a enrollment")

    # Verify downstream AI fallback rewrite
    from app.core.ai_service.service import AIService
    from app.core.config import get_settings
    ai_service = AIService(settings=get_settings())
    struct = structure_resume_text(AKHIL_RANA_WRAPPED_PDF_RESUME)
    jd_text = "We are seeking a Staff / Senior Software Engineer with macOS/iOS, Swift, Python, and packaging automation experience."
    rewrite_res = ai_service._fallback_resume_rewrite(struct, jd_text, role="Senior Software Engineer", company="Flipkart")
    
    proposed_texts = [r.proposed for r in rewrite_res.experience_bullets]
    for text in proposed_texts:
        assert "Built a environments" not in text
        assert "Engineered a commands" not in text
        assert "Built a enrollment" not in text
        assert "Built a pkgbuild" not in text


AKHIL_RANA_AUTHORITATIVE_RESUME = """AKHIL RANA
akhil.rana@example.com | +91 9876543210 | Bengaluru, India | linkedin.com/in/akhil-rana | github.com/akhil-rana

PROFESSIONAL SUMMARY
Experienced Senior Software Engineer with 4+ years of expertise in system software, macOS/iOS client engineering, cloud infrastructure, and full-stack development.

PROFESSIONAL EXPERIENCE

Juniper Networks
Software Engineer - 3 (April 2024 - Present)
Software Engineer - 2 (April 2022 - March 2024)
Software Engineer Intern (January 2022 - March 2022)
Bengaluru, India

Marvis Client - MacOS/iOS Development:
• Maintained and enhanced Marvis Client applications for enterprise Wi-Fi environments using SwiftUI and UIKit.
• Implemented telemetry collection using CoreWLAN frameworks and system profiler commands to capture network performance metrics.
• Built automated network onboarding workflows with SCEP certificate enrollment and credential provisioning.
• Developed Marvis-CLI tool for network diagnostics, log collection, non-UI based configuration and MDM integration, reducing network troubleshooting time by 70%.
• Created silent auto-upgrade mechanisms for BYOD devices using authenticated helper tools and privilege escalation.
• For iOS, implemented network onboarding using Network Extension frameworks and enterprise configuration profiles, supporting 40k monthly active users.

Application Infrastructure & Packaging:
• Architected modular application packaging pipelines, achieving a 99.8% installer success rate across diverse macOS environments.
• Optimized binary build sizes with a 65% package-size reduction through dynamic framework linkage and asset pruning.

CI/CD & Release Automation:
• Automated CI/CD and release pipelines via GitHub Actions and Jenkins, reducing release cycle duration from 3 hours to 10 minutes (90% manual-effort reduction).

Indoor Location SDK:
• Engineered real-time indoor location tracking SDK components handling high-frequency telemetry packets.
• Integrated Bluetooth Low Energy (BLE) and Wi-Fi signal processing algorithms, improving location accuracy by 35%.

Squareboat Solutions
Software Engineer (June 2021 - December 2021)
Software Engineer Intern (January 2021 - May 2021)
Gurugram, India

Full-Stack Development:
• Led development of scalable microservices using FastAPI, React, and PostgreSQL, improving page-load performance by 45%.
• Consolidated third-party API dependencies, achieving an 80% SaaS spend reduction.

Custom Scheduling & Payment Platform:
• Architected custom scheduling and payment platform processing $200k+ transactions.
• Reduced booking-time duration by 70% through optimized checkout workflows.

PERSONAL PROJECTS

Pathology Algorithm Development Workbench
Python, PyTorch, OpenCV, Docker
• Developed deep learning computational pathology workbench for histopathology image analysis and cell segmentation.
• Implemented distributed inference pipeline processing high-resolution gigapixel whole slide images.

virtual-bg
C++, WebRTC, OpenGL
• Built real-time video background replacement utility using lightweight neural segmentation and WebRTC streams.
• Achieved 60 FPS processing speed with minimal CPU overhead.

Peerivate
Go, WebSockets, WebRTC, Cryptography
• Engineered decentralized end-to-end encrypted peer-to-peer file sharing protocol.
• Implemented zero-knowledge authentication and NAT traversal for resilient data transfer.

TECHNICAL SKILLS
Languages: Python, Swift, Objective-C, Go, JavaScript, TypeScript, C++, Shell
Frameworks & Tools: FastAPI, React, Node.js, Docker, Kubernetes, AWS, CoreWLAN, Git, CI/CD, Terraform, Jenkins
Databases: PostgreSQL, Redis, MongoDB, MySQL

ACHIEVEMENTS
• Winner, Juniper Networks Annual Innovation Hackathon (2023) for Marvis diagnostic agent.
• Published technical whitepaper on Enterprise macOS Network Provisioning.

SIDE QUESTS
• Open-source contributor to Swift networking and packaging libraries.
• Technical mentor for junior systems engineers and undergraduate student developers.

EDUCATION
Bachelor of Technology in Computer Science and Engineering (2018 - 2022)
National Institute of Technology — CGPA: 8.8 / 10.0
"""


def test_authoritative_akhil_rana_canonical_hierarchy():
    """
    [AUTHORITATIVE REGRESSION] Verifies complete canonical hierarchy preservation on Akhil Rana resume.
    Invariants:
    1. Professional Experience contains exactly 2 companies: Juniper Networks & Squareboat Solutions.
    2. Juniper Networks preserves all 3 roles, dates, and 4 responsibility groups with 11 bullets.
    3. Squareboat Solutions preserves both 2 roles, dates, and 2 responsibility groups with 4 bullets.
    4. Personal Projects (3 items), Technical Skills (37 items), Achievements (2 items), Side Quests (2 items),
       and Education remain 100% separate without cross-contamination.
    5. All quantified metrics remain strictly attached to their source entities.
    """
    profile = extract_candidate_profile(AKHIL_RANA_AUTHORITATIVE_RESUME)
    
    # 1. Experience Entity Count
    assert len(profile.experience) == 2, f"Expected 2 companies, got {len(profile.experience)}"
    
    # Juniper Networks
    juniper = profile.experience[0]
    assert juniper.company == "Juniper Networks"
    assert juniper.role == "Software Engineer - 3"
    assert juniper.dates == "April 2024 - Present"
    assert juniper.location == "Bengaluru, India"
    assert len(juniper.progression) == 3
    assert juniper.progression[0].title == "Software Engineer - 3"
    assert juniper.progression[1].title == "Software Engineer - 2"
    assert juniper.progression[2].title == "Software Engineer Intern"
    assert len(juniper.responsibility_groups) == 4
    assert len(juniper.bullets) == 11
    
    # Squareboat Solutions
    squareboat = profile.experience[1]
    assert squareboat.company == "Squareboat Solutions"
    assert squareboat.role == "Software Engineer"
    assert squareboat.dates == "June 2021 - December 2021"
    assert squareboat.location == "Gurugram, India"
    assert len(squareboat.progression) == 2
    assert squareboat.progression[0].title == "Software Engineer"
    assert squareboat.progression[1].title == "Software Engineer Intern"
    assert len(squareboat.responsibility_groups) == 2
    assert len(squareboat.bullets) == 4
    
    # 2. Personal Projects
    assert len(profile.projects) == 3
    titles = [p.title for p in profile.projects]
    assert "Pathology Algorithm Development Workbench" in titles
    assert "virtual-bg" in titles
    assert "Peerivate" in titles
    
    # 3. Technical Skills
    assert len(profile.skills) >= 20
    assert "FastAPI" in profile.skills
    assert not any("Frameworks & Tools:" in s for s in profile.skills)
    
    # 4. Achievements & Side Quests
    assert len(profile.achievements) == 2
    assert any("Innovation Hackathon" in a for a in profile.achievements)
    assert len(profile.side_quests) == 2
    assert any("Open-source contributor" in sq for sq in profile.side_quests)
    
    # 5. Metric Verification
    juniper_text = " ".join(juniper.bullets)
    assert "99.8%" in juniper_text
    assert "65%" in juniper_text
    assert "3 hours to 10 minutes" in juniper_text
    assert "90%" in juniper_text
    assert "40k" in juniper_text
    assert "70%" in juniper_text
    assert "35%" in juniper_text
    
    squareboat_text = " ".join(squareboat.bullets)
    assert "45%" in squareboat_text
    assert "80%" in squareboat_text
    assert "$200k+" in squareboat_text
    assert "70%" in squareboat_text


SYNTHETIC_COMMA_LOCATION_RESUME = """ALEX CHEN
alex@example.com | +1 555-0199 | San Francisco, CA

• Work Experience
Google LLC, Mountain View, CA
Senior Staff Engineer (January 2021 - Present)
• Architected global distributed consensus platform serving 100M+ QPS.

Meta Platforms, Menlo Park, CA
Staff Software Engineer (March 2018 - December 2020)
• Optimized real-time video transcoding pipeline delivering a 30% reduction in CPU compute costs.

• Technical Skills
Languages: Go, C++, Rust, Python
Tools & Technologies: Kubernetes, Docker, Envoy, gRPC

• Education
Stanford University, Stanford, CA
Master of Science in Computer Science (2016 - 2018)
"""


def test_synthetic_comma_location_and_bulleted_headers_regression():
    """
    [SYNTHETIC REGRESSION] Verifies bulleted section headings ('• Work Experience')
    and 'Company, Location' header lines on arbitrary resumes.
    """
    profile = extract_candidate_profile(SYNTHETIC_COMMA_LOCATION_RESUME)
    
    assert len(profile.experience) == 2
    google = profile.experience[0]
    assert google.company == "Google LLC"
    assert google.location == "Mountain View, CA"
    assert google.role == "Senior Staff Engineer"
    assert len(google.bullets) == 1
    assert "100M+ QPS" in google.bullets[0]
    
    meta = profile.experience[1]
    assert meta.company == "Meta Platforms"
    assert meta.location == "Menlo Park, CA"
    assert meta.role == "Staff Software Engineer"
    assert len(meta.bullets) == 1
    assert "30%" in meta.bullets[0]
    
    assert "Go" in profile.skills
    assert not any("Tools & Technologies:" in s for s in profile.skills)


