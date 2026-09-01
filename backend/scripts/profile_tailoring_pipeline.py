import time
import json
import asyncio
from typing import Any

from app.core.config import Settings
from app.core.ai_service.service import AIService
from app.modules.resume.models import CandidateProfile
from app.modules.resume.parsing.text_extraction import extract_pdf, extract_docx
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.resume.classification import classify_candidate_profile
from app.modules.tailoring.strategy import resolve_template_strategy
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.matching.evidence_mapping import map_resume_to_jd_evidence
from app.modules.tailoring.services import (
    _build_editable_subobject,
    compute_deterministic_skill_reorder,
    _truth_guard_warning,
    _merge_structured_tailoring,
)
from app.modules.tailoring.validation import (
    detect_fabricated_claims,
    detect_unsupported_metrics,
    detect_unsupported_action_verbs_and_scope,
    detect_entity_boundary_violations,
    measure_and_enforce_one_page_fit,
)
from app.modules.intelligence.ats_readability_validator import evaluate_ats_and_readability
from app.modules.tailoring.export import generate_pdf, generate_docx, render_pdf_from_structured


VIKAS_RESUME_TEXT = """VIKAS V
vikas.v@example.com | +91 9876543210 | Bengaluru, India | linkedin.com/in/vikas-v

PROFESSIONAL SUMMARY
Motivated Information Science undergraduate with hands-on experience in Full Stack Web Development and Machine Learning.

TECHNICAL SKILLS
Languages: Python, JavaScript, HTML, CSS, SQL, C++
Frameworks & Libraries: React, Node.js, Express, Streamlit, OpenCV, TensorFlow, Keras, Pandas, NumPy, Scikit-learn
Databases & Tools: MongoDB, MySQL, Git, GitHub, VS Code

ACADEMIC PROJECTS
AI-Based Ad Viral Potential Analyzer
Technologies: Python, Streamlit, OpenCV, ML
• Developed an AI-powered web application for advertisement virality prediction using Random Forest Regression.
• Implemented real-time video/image analysis and OpenCV feature extraction alongside NLP to analyze CTR, retention, and watch time metrics.
• Built interactive Streamlit dashboard for real-time viral potential prediction and visualization.

Cataract Prediction System Using Deep Learning
Technologies: Python, TensorFlow, Keras, DL
• Convolutional Neural Network (CNN) image classification model using Python, TensorFlow, and Keras to detect cataracts from retinal images, achieving 91% validation accuracy.
• Implemented end-to-end ML pipeline using NumPy and Pandas: data preprocessing, augmentation, model training, and evaluation via accuracy, precision, and recall metrics.
• Delivered the complete solution within a 6-week timeline across a 4-member team covering data collection, model building, and evaluation.

EDUCATION
Bachelor of Engineering in Information Science & Engineering (2021 - 2025)
Visvesvaraya Technological University — CGPA: 8.5 / 10.0

CERTIFICATIONS
- Machine Learning Specialization — DeepLearning.AI
- Python for Data Science — Coursera
"""

SAMPLE_JD_TEXT = """
Role: Machine Learning Engineer / Full Stack Developer
Company: TechVision Innovations
Location: Bengaluru, India (Hybrid)

About the Job:
We are seeking an energetic Machine Learning Engineer with Full Stack Development skills.

Key Responsibilities:
- Build and evaluate machine learning models for computer vision and NLP tasks using Python, TensorFlow, or PyTorch.
- Develop interactive web dashboards using React, Node.js, or Streamlit to visualize model predictions.
- Build automated ML pipelines for data preprocessing, augmentation, and feature extraction using NumPy, Pandas, and OpenCV.
- Collaborate in cross-functional agile teams to deliver production-ready software solutions.

Requirements:
- Strong programming skills in Python and JavaScript.
- Hands-on experience with deep learning frameworks (TensorFlow, Keras, or PyTorch).
- Experience with OpenCV for image/video processing.
- Familiarity with SQL and NoSQL databases (MongoDB, PostgreSQL).
"""


async def profile_pipeline():
    results = {}
    print("==================================================")
    print("PROFILING ROLERADAR RESUME TAILORING PIPELINE")
    print("==================================================\n")

    # Stage 1: PDF/DOCX Extraction (simulated via sample PDF / byte extraction)
    t0 = time.perf_counter()
    # Generate temporary PDF to test exact PDF extraction speed
    pdf_bytes = generate_pdf(VIKAS_RESUME_TEXT, candidate_name="Vikas V", template="modern")
    extracted_text, blocks = extract_pdf(pdf_bytes)
    t1 = time.perf_counter()
    results["1_extraction"] = {
        "name": "1. PDF/DOCX Extraction",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (PyMuPDF / docx2txt)",
        "input_size": f"{len(pdf_bytes)} bytes",
        "output_size": f"{len(extracted_text)} chars",
        "execution": "Synchronous / Parallelizable",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(file_bytes)",
    }

    # Stage 2: Resume Normalization
    t0 = time.perf_counter()
    lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
    normalized_text = "\n".join(lines)
    t1 = time.perf_counter()
    results["2_normalization"] = {
        "name": "2. Resume Normalization",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (Deterministic text cleaning regexes)",
        "input_size": f"{len(extracted_text)} chars",
        "output_size": f"{len(normalized_text)} chars",
        "execution": "Synchronous / In-memory",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(raw_text)",
    }

    # Stage 3: Resume Structuring
    t0 = time.perf_counter()
    parsed = structure_resume_text(normalized_text)
    candidate_profile = CandidateProfile.from_parsed_dict(parsed, normalized_text)
    t1 = time.perf_counter()
    results["3_structuring"] = {
        "name": "3. Resume Structuring",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (Deterministic Rule & Layout Parsing)",
        "input_size": f"{len(normalized_text)} chars",
        "output_size": f"{len(json.dumps(parsed))} chars ({len(candidate_profile.evidence_units)} evidence units)",
        "execution": "Synchronous / In-memory",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(normalized_text) + parser_version",
    }

    # Stage 4: Candidate Classification
    t0 = time.perf_counter()
    classification = classify_candidate_profile(candidate_profile)
    strategy = resolve_template_strategy(classification)
    t1 = time.perf_counter()
    results["4_classification"] = {
        "name": "4. Candidate Classification & Strategy",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (Rule-based heuristics on CandidateProfile)",
        "input_size": f"{len(candidate_profile.evidence_units)} evidence units",
        "output_size": f"Type: {classification.classification.value}, Strategy: {strategy.strategy_name.value} ({strategy.template_variant})",
        "execution": "Synchronous / In-memory",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(CandidateProfile)",
    }

    # Stage 5: JD Analysis
    t0 = time.perf_counter()
    jd_reqs = analyze_job_description(SAMPLE_JD_TEXT, "Machine Learning Engineer")
    t1 = time.perf_counter()
    results["5_jd_analysis"] = {
        "name": "5. JD Analysis",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (Deterministic Regex & Taxonomy Engine)",
        "input_size": f"{len(SAMPLE_JD_TEXT)} chars",
        "output_size": f"{len(jd_reqs.must_have_skills)} must-have, {len(jd_reqs.preferred_skills)} preferred",
        "execution": "Synchronous / Parallelizable with Resume Parsing",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(jd_text)",
    }

    # Stage 6: Resume <-> JD Matching & Evidence Mapping
    t0 = time.perf_counter()
    mapping = map_resume_to_jd_evidence(candidate_profile, jd_reqs)
    reordered_skills, matched_skills, unmatched_jd_skills, was_reordered = compute_deterministic_skill_reorder(
        parsed.get("skills", []), SAMPLE_JD_TEXT
    )
    t1 = time.perf_counter()
    results["6_matching"] = {
        "name": "6. Resume <-> JD Matching & Evidence Mapping",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (Deterministic Token & Substring Matcher / Embedding Index)",
        "input_size": f"{len(candidate_profile.evidence_units)} units + {len(jd_reqs.required_skills)} JD skills",
        "output_size": f"{len(mapping.mappings)} mappings, {len(matched_skills)} matched skills",
        "execution": "Synchronous / In-memory",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(CandidateProfile) + sha256(JDRequirements)",
    }

    # Stage 7: Tailoring Generation
    # Measure fallback vs LLM prompt construction
    editable_subobject = _build_editable_subobject(parsed)
    editable_json = json.dumps(editable_subobject, indent=2)
    settings = Settings()
    ai_service = AIService(settings)
    
    t0 = time.perf_counter()
    # Test internal deterministic fallback rewrite
    fallback_res = ai_service._fallback_resume_rewrite(
        editable_subobject, SAMPLE_JD_TEXT, "TechVision Innovations", "Machine Learning Engineer"
    )
    t1 = time.perf_counter()
    fallback_ms = (t1 - t0) * 1000

    results["7_tailoring_generation"] = {
        "name": "7. Tailoring Generation",
        "time_ms": fallback_ms,
        "llm_calls": "1 structured call (or 0 when using deterministic fast-path / fallback)",
        "model": settings.OLLAMA_MODEL,
        "input_size": f"{len(editable_json)} chars JSON prompt (~{len(editable_json)//4} tokens)",
        "output_size": f"StructuredTailoringResult (~{len(json.dumps(fallback_res.model_dump()))//4} tokens)",
        "execution": "Sequential (Single structured LLM generation call)",
        "can_be_deterministic": False, # (LLM reasoning with deterministic fallback)
        "can_be_cached": True,
        "cache_key": "sha256(editable_subobject) + sha256(JD) + prompt_version",
    }

    # Stage 8: Truth Guard Validation
    t0 = time.perf_counter()
    guard_warnings = []
    for pb in fallback_res.project_bullets:
        w = _truth_guard_warning(
            pb.original,
            pb.proposed,
            SAMPLE_JD_TEXT,
            parsed.get("skills", []),
            pb.source_evidence,
            require_verbatim_evidence=True,
            entity_id=f"proj_{pb.bullet_index}",
            all_evidence_units=candidate_profile.evidence_units,
        )
        if w:
            guard_warnings.append(w)
    t1 = time.perf_counter()
    results["8_truth_guard"] = {
        "name": "8. Truth Guard Validation",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (Deterministic Rule-Based Guard: Anti-Fabrication, Metric, Action Verb Scope)",
        "input_size": f"{len(fallback_res.project_bullets)} project bullets",
        "output_size": f"{len(guard_warnings)} warnings generated",
        "execution": "Synchronous / In-memory",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(original + proposed + skills)",
    }

    # Stage 9: ATS & Readability Validation
    t0 = time.perf_counter()
    initial_parsed = _merge_structured_tailoring(parsed, fallback_res.model_dump(mode="json"), approved_change_ids=None)
    ats_audit = evaluate_ats_and_readability(initial_parsed, master_data=candidate_profile)
    t1 = time.perf_counter()
    results["9_ats_validation"] = {
        "name": "9. ATS & Readability Validation",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (Deterministic ATS heuristic engine & readability formulas)",
        "input_size": f"{len(json.dumps(initial_parsed))} chars parsed resume",
        "output_size": f"ATS Score: {ats_audit.ats_format_validation.overall_ats_score}/100, Findings: {len(ats_audit.ats_format_validation.findings)}",
        "execution": "Synchronous / In-memory",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(tailored_parsed)",
    }

    # Stage 10: Template Rendering & One-Page Fit Enforcement
    t0 = time.perf_counter()
    raw_tailored_text = VIKAS_RESUME_TEXT # simulated tailored plain text
    final_text, fit_ok, page_count = measure_and_enforce_one_page_fit(
        raw_tailored_text, candidate_name="Vikas V", template="modern", max_pages=1
    )
    t1 = time.perf_counter()
    results["10_template_rendering"] = {
        "name": "10. Template Rendering & One-Page Enforcement",
        "time_ms": (t1 - t0) * 1000,
        "llm_calls": 0,
        "model": "None (ReportLab binary layout simulator + iterative line-trimming)",
        "input_size": f"{len(raw_tailored_text)} chars",
        "output_size": f"{len(final_text)} chars, fits 1 page: {fit_ok} ({page_count} pages)",
        "execution": "Synchronous / In-memory",
        "can_be_deterministic": True,
        "can_be_cached": False,
        "cache_key": "sha256(final_text + template)",
    }

    # Stage 11: PDF / DOCX Export
    t0 = time.perf_counter()
    pdf_out = generate_pdf(final_text, candidate_name="Vikas V", template="modern")
    t1 = time.perf_counter()
    pdf_ms = (t1 - t0) * 1000

    t0 = time.perf_counter()
    docx_out = generate_docx(final_text, candidate_name="Vikas V")
    t1 = time.perf_counter()
    docx_ms = (t1 - t0) * 1000

    results["11_export"] = {
        "name": "11. PDF/DOCX Export",
        "time_ms": pdf_ms + docx_ms,
        "details": f"PDF: {pdf_ms:.2f}ms, DOCX: {docx_ms:.2f}ms",
        "llm_calls": 0,
        "model": "None (ReportLab & python-docx binary generators)",
        "input_size": f"{len(final_text)} chars text",
        "output_size": f"PDF: {len(pdf_out)} bytes, DOCX: {len(docx_out)} bytes",
        "execution": "Synchronous / Parallelizable",
        "can_be_deterministic": True,
        "can_be_cached": True,
        "cache_key": "sha256(final_text + template + candidate_name)",
    }

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    asyncio.run(profile_pipeline())
