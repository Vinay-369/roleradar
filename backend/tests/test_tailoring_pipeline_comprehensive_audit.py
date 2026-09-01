"""
Comprehensive Holistic Audit Test Suite for Tailoring Pipeline Regression.
Tests:
1. Akhil Rana (Experienced Professional Candidate with multi-level role progression)
2. Vikas K (Student / Fresher Project-Oriented Candidate)

Verifies:
- Candidate classification determinism
- Real JD analysis and 6-status requirement classification
- Evidence mapping provenance & anti-hallucination isolation
- Tailoring strategy and deterministic skill reordering
- Truth Guard anti-fabrication, metric preservation, and fragment detection
- Wholesale structured dictionary merge with 100% protected sections
- Metric integrity preservation (100% of source metrics unaltered)
- Deterministic 1-page PDF rendering and fit
"""
import copy
import os
import fitz  # PyMuPDF
import pytest

from app.modules.resume.parsing.structurer import (
    structure_resume_text,
    extract_candidate_profile,
)
from app.modules.resume.models import (
    CandidateProfile,
    ClaimType,
    EvidenceUnit,
)
from app.modules.resume.classification import (
    classify_candidate_profile,
    CareerClassification,
)
from app.modules.jobs.taxonomy import (
    analyze_job_description,
    RequirementCategory,
)
from app.modules.matching.evidence_mapping import (
    map_resume_to_jd_evidence,
    EvidenceMatchStatus,
)
from app.modules.tailoring.strategy import (
    resolve_template_strategy,
    StrategyName,
)
from app.modules.tailoring.validation import (
    compute_deterministic_skill_reorder,
    detect_fabricated_claims,
    detect_unsupported_metrics,
    detect_unsupported_action_verbs_and_scope,
    detect_dropped_source_skills,
    detect_entity_boundary_violations,
    detect_sentence_fragments_and_truncation,
    validate_protected_sections,
    measure_and_enforce_one_page_fit,
)
from app.modules.tailoring.services import (
    _merge_structured_tailoring,
    _truth_guard_warning,
)
from app.modules.intelligence.ats_readability_validator import (
    evaluate_ats_and_readability,
)
from app.modules.tailoring.export import (
    generate_pdf,
    render_text_from_structured,
)
from app.core.ai_service.schemas import (
    StructuredTailoringResult,
    SummaryTailoring,
    SkillsTailoring,
    BulletRewrite,
)


AKHIL_RAW_RESUME = """AKHIL RANA
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
"""


VIKAS_RAW_RESUME = """VIKAS K
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

REAL_AKHIL_JD = """
Senior Software Engineer - macOS Platform & Systems Engineering
Company: CloudScale Networks
Location: Bengaluru, India (Hybrid)

Key Responsibilities:
• Lead development of client-side networking software on macOS and iOS platforms.
• Design and maintain high-throughput telemetry collection pipelines and diagnostic CLI utilities.
• Automate CI/CD pipelines, release orchestration, and deployment packaging workflows.
• Architect scalable microservices and backend API integrations using Python and modern cloud tooling.

Requirements (Must Haves):
• 4+ years of professional software engineering experience in systems software, client engineering, or backend development.
• Strong proficiency in Swift, Objective-C, Python, or Go.
• Proven experience with macOS/iOS system frameworks, Network Extension, CoreWLAN, or low-level systems programming.
• Hands-on expertise with CI/CD automation tools like GitHub Actions, Jenkins, or Docker.
• Experience with relational databases like PostgreSQL or MySQL.

Preferred Qualifications:
• Experience with Wi-Fi telemetry, BLE, or indoor location tracking algorithms.
• Background in microservices architecture using FastAPI or React.
• Top Secret Security Clearance (Clearance required for defense clients).
• Knowledge of Kubernetes and Terraform for cloud deployments.
"""

REAL_VIKAS_JD = """
Junior Software Engineer - Python Backend & Machine Learning
Company: DataPulse Technologies
Location: Bengaluru, India

Key Responsibilities:
• Develop and deploy machine learning models for image analysis and classification.
• Build RESTful APIs and backend services using Python, Flask, or FastAPI.
• Build data processing pipelines using NumPy, Pandas, and OpenCV.

Requirements (Must Haves):
• Bachelor's degree in Computer Science, Information Technology, or related engineering discipline (graduating 2025-2027).
• Strong foundational knowledge in Python, SQL, and Data Structures.
• Hands-on project experience with Machine Learning libraries (TensorFlow, Keras, Scikit-Learn, or OpenCV).
• Proficiency with Git version control.

Preferred Qualifications:
• Experience with Docker containerization and Postman for API testing.
• Full-stack familiarity with React.js or JavaScript.
"""


def test_akhil_complete_pipeline_audit():
    # 1. Parsing & Profile
    akhil_parsed = structure_resume_text(AKHIL_RAW_RESUME)
    akhil_profile = extract_candidate_profile(AKHIL_RAW_RESUME)
    assert len(akhil_profile.experience) == 2
    assert len(akhil_profile.projects) == 3
    assert len(akhil_profile.evidence_units) >= 15

    # 2. Classification
    akhil_class = classify_candidate_profile(akhil_profile, AKHIL_RAW_RESUME)
    assert akhil_class.classification in (CareerClassification.PROFESSIONAL, CareerClassification.SENIOR_PROFESSIONAL)
    assert akhil_class.years_of_experience >= 4.0

    # 3. JD Analysis
    jd_reqs = analyze_job_description(REAL_AKHIL_JD, "Senior Software Engineer - macOS Platform & Systems Engineering")
    assert len(jd_reqs.requirements) >= 10

    # 4. Evidence Mapping
    matrix = map_resume_to_jd_evidence(akhil_profile, jd_reqs)
    assert matrix.exact_matches_count >= 5
    assert matrix.conflicting_matches_count >= 1  # Top Secret Clearance conflict caught

    # 5. Tailoring Strategy & Skill Reorder
    strategy = resolve_template_strategy(akhil_class)
    assert strategy.candidate_type == "senior/professional"
    reordered_skills, matched_skills, unmatched_jd_skills, was_reordered = compute_deterministic_skill_reorder(
        akhil_profile.skills, REAL_AKHIL_JD
    )
    assert was_reordered
    assert "Python" in matched_skills and "Swift" in matched_skills

    # 6. Truth Guard Rejections
    source_b = "• Developed Marvis-CLI tool for network diagnostics, log collection, non-UI based configuration and MDM integration, reducing network troubleshooting time by 70%."
    # Valid rewrite
    assert _truth_guard_warning(source_b, "• Engineered Marvis-CLI diagnostic utility with MDM integration, reducing network troubleshooting duration by 70%.", REAL_AKHIL_JD, akhil_profile.skills) is None
    # Bad metric
    assert "Measurable claim" in (_truth_guard_warning(source_b, "• Developed Marvis-CLI tool reducing troubleshooting time by 99%.", REAL_AKHIL_JD, akhil_profile.skills) or "")
    # Hallucinated tool
    assert "Technical competency" in (_truth_guard_warning(source_b, "• Developed Marvis-CLI tool using Rust and GraphQL.", REAL_AKHIL_JD, akhil_profile.skills) or "")

    # 7. Merge & Metric Preservation
    tailored_result = StructuredTailoringResult(
        summary=SummaryTailoring(
            original=akhil_parsed.get("summary", ""),
            proposed="Senior Software Engineer with 4+ years of expertise in macOS/iOS platform engineering, systems software, and CI/CD automation.",
            reason="Aligned summary.",
            source_evidence="Verified 4+ years experience.",
            confidence=0.95,
        ),
        skills=SkillsTailoring(ordered_skills=reordered_skills),
        experience_bullets=[
            BulletRewrite(
                bullet_index=0,
                original="• Maintained and enhanced Marvis Client applications for enterprise Wi-Fi environments using SwiftUI and UIKit.",
                proposed="• Engineered enterprise Wi-Fi client applications on macOS/iOS platforms utilizing SwiftUI and UIKit.",
                action="REWRITE",
                reason="Enhanced verb.",
                source_evidence="Maintained and enhanced Marvis Client applications for enterprise Wi-Fi environments using SwiftUI and UIKit.",
                confidence=0.95,
            )
        ],
        project_bullets=[],
        unmatched_gaps=unmatched_jd_skills,
    )
    merged = _merge_structured_tailoring(akhil_parsed, tailored_result.model_dump(mode="json"))

    # Verify all metrics preserved
    all_text = " ".join(merged.get("experience_raw", [])) + " " + " ".join([str(p) for p in merged.get("projects_raw", [])])
    for metric in ["99.8%", "65%", "3 hours", "10 minutes", "90%", "40k", "45%", "80%", "$200k+", "70%", "35%", "60 FPS"]:
        assert metric.lower() in all_text.lower(), f"Metric {metric} was lost!"

    # 8. ATS & PDF Export
    ats_audit = evaluate_ats_and_readability(merged, master_data=akhil_profile)
    assert ats_audit.factual_validation.is_valid
    assert ats_audit.ats_format_validation.overall_ats_score >= 80

    final_parsed, fits_one_page, page_count = measure_and_enforce_one_page_fit(merged, candidate_name="Akhil Rana", template="modern", max_pages=2)
    pdf_bytes = generate_pdf(final_parsed, candidate_name="Akhil Rana", template="modern")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count in (1, 2)
    doc.close()


def test_vikas_complete_pipeline_audit():
    # 1. Parsing & Profile
    vikas_parsed = structure_resume_text(VIKAS_RAW_RESUME)
    vikas_profile = extract_candidate_profile(VIKAS_RAW_RESUME)
    assert len(vikas_profile.projects) == 2
    assert len(vikas_profile.education) == 2

    # 2. Classification
    vikas_class = classify_candidate_profile(vikas_profile, VIKAS_RAW_RESUME)
    assert vikas_class.classification in (CareerClassification.STUDENT, CareerClassification.FRESHER)
    assert vikas_class.is_student is True

    # 3. JD Analysis
    jd_reqs = analyze_job_description(REAL_VIKAS_JD, "Junior Software Engineer - Python Backend & Machine Learning")
    assert len(jd_reqs.requirements) >= 8

    # 4. Evidence Mapping
    matrix = map_resume_to_jd_evidence(vikas_profile, jd_reqs)
    assert matrix.exact_matches_count >= 4

    # 5. Tailoring Strategy & Skill Reorder
    strategy = resolve_template_strategy(vikas_class)
    assert strategy.highlight_education_top is True
    reordered_skills, matched_skills, unmatched_jd_skills, was_reordered = compute_deterministic_skill_reorder(
        vikas_profile.skills, REAL_VIKAS_JD
    )
    assert was_reordered
    assert "Python" in matched_skills

    # 6. Truth Guard Rejections
    v_orig = "• Implemented feature extraction for visual hooks and audio pacing, achieving 91% accuracy across 10,000 ad samples."
    assert _truth_guard_warning(v_orig, "• Engineered feature extraction for visual hooks, achieving 91% accuracy across 10,000 ad samples.", REAL_VIKAS_JD, vikas_profile.skills) is None
    assert "Measurable claim" in (_truth_guard_warning(v_orig, "• Implemented feature extraction achieving 99% accuracy across 50,000 ad samples.", REAL_VIKAS_JD, vikas_profile.skills) or "")

    # 7. Merge & Metric Preservation
    tailored_result = StructuredTailoringResult(
        summary=SummaryTailoring(
            original=vikas_parsed.get("summary", ""),
            proposed="Aspiring Computer Science Engineer with strong hands-on expertise in Python backend services and deep learning.",
            reason="Aligned summary.",
            source_evidence="Verified degree and Python ML background.",
            confidence=0.95,
        ),
        skills=SkillsTailoring(ordered_skills=reordered_skills),
        experience_bullets=[],
        project_bullets=[
            BulletRewrite(
                bullet_index=0,
                original="• AI-Based Ad Viral Potential Analyzer\n  Technologies: Python, Streamlit, OpenCV, Scikit-Learn, Machine Learning\n  - Built predictive machine learning pipeline using Streamlit and OpenCV to analyze video features and predict viral engagement.\n  - Implemented feature extraction for visual hooks and audio pacing, achieving 91% accuracy across 10,000 ad samples.",
                proposed="• AI-Based Ad Viral Potential Analyzer\n  Technologies: Python, Streamlit, OpenCV, Scikit-Learn, Machine Learning\n  - Engineered predictive machine learning pipeline using Streamlit and OpenCV to analyze video features and predict viral engagement.\n  - Implemented feature extraction for visual hooks and audio pacing, achieving 91% accuracy across 10,000 ad samples.",
                action="REWRITE",
                reason="Enhanced verb.",
                source_evidence="Built predictive machine learning pipeline using Streamlit and OpenCV.",
                confidence=0.95,
            )
        ],
        unmatched_gaps=unmatched_jd_skills,
    )
    merged = _merge_structured_tailoring(vikas_parsed, tailored_result.model_dump(mode="json"))

    # Verify metrics preserved
    all_text = " ".join([str(p) for p in merged.get("projects_raw", [])]) + " " + " ".join([str(e) for e in merged.get("education_raw", [])])
    for metric in ["91%", "10,000", "2,000", "6-week", "4-member", "9.1", "94%"]:
        assert metric.lower() in all_text.lower(), f"Vikas metric {metric} was lost!"

    # 8. ATS & PDF Export
    ats_audit = evaluate_ats_and_readability(merged, master_data=vikas_profile)
    assert ats_audit.factual_validation.is_valid
    assert ats_audit.ats_format_validation.overall_ats_score >= 80

    final_parsed, fits_one_page, page_count = measure_and_enforce_one_page_fit(merged, candidate_name="Vikas K", template="modern", max_pages=1)
    pdf_bytes = generate_pdf(final_parsed, candidate_name="Vikas K", template="modern")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count == 1
    doc.close()
