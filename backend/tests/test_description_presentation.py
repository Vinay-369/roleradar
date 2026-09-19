"""
Regression tests for Job and Internship Description Presentation Normalization.

Covers all 15 required verification scenarios:
A. Repeated JOB DESCRIPTION headings
B. Repeated QUALIFICATIONS headings
C. Heading with colon ("Job Description:")
D. Markdown heading ("## Job Description")
E. Inline heading ("Expected skill set:", "Tasks / Responsibilities:")
F. HTML paragraph heading ("<p><b>Job Description:</b></p>")
G. Same content appearing in canonical section + detailed description (deduplication)
H. No meaningful section -> no empty UI section
I. Internship description normalization
J. SmartRecruiters provider normalization
K. Lever provider normalization
L. Greenhouse provider normalization
M. Existing Bosch Mobile requirements remain unchanged
N. Existing Bosch Hardware extraction remains unchanged
O. Spark false-positive protection remains unchanged
"""
import pytest
from app.modules.jobs.description_presentation import (
    normalize_job_description_presentation,
    clean_raw_description,
)
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.jobs.smartrecruiters_provider import _clean_html_description


class TestDescriptionPresentationNormalization:
    """Comprehensive test matrix for presentation normalizer."""

    def test_a_repeated_job_description_headings(self):
        """A. Repeated JOB DESCRIPTION headings are deduplicated/normalized."""
        raw_text = (
            "## Job Description\n"
            "Job Description:\n"
            "- Build scalable web applications\n"
            "- Collaborate with engineering teams\n\n"
            "JOB DESCRIPTION\n"
            "- Write clean, maintainable code\n"
        )
        res = normalize_job_description_presentation(raw_text)
        # Should not have multiple detailed sections with "Job Description" as title
        titles = [sec.title.lower() for sec in res.detailed_sections if sec.title]
        assert titles.count("job description") == 0
        # If responsibilities were empty, source items populate canonical responsibilities
        assert len(res.responsibilities) > 0

    def test_b_repeated_qualifications_headings(self):
        """B. Repeated QUALIFICATIONS headings are normalized."""
        raw_text = (
            "## Qualifications\n"
            "Qualifications:\n"
            "- B.Tech in Computer Science\n\n"
            "QUALIFICATIONS\n"
            "- 3+ years experience\n"
        )
        res = normalize_job_description_presentation(raw_text)
        titles = [sec.title.lower() for sec in res.detailed_sections if sec.title]
        assert titles.count("qualifications") == 0
        assert len(res.qualifications) > 0

    def test_c_heading_with_colon(self):
        """C. Heading with trailing colon is cleanly recognized."""
        raw_text = "Role Overview:\nWe are looking for a Software Engineer to join our core platform."
        res = normalize_job_description_presentation(raw_text)
        assert res.summary is not None
        assert any("Software Engineer" in item.text for item in res.summary.items)

    def test_d_markdown_heading(self):
        """D. Markdown heading hashes ('## ') are recognized and stripped from titles."""
        raw_text = "## About Us\nWe are building the future of hiring intelligence."
        res = normalize_job_description_presentation(raw_text)
        assert res.summary is not None
        assert res.summary.title == "Job Summary"

    def test_e_inline_heading(self):
        """E. Inline headings like 'Expected skill set:' and 'Tasks / Responsibilities:' are cleanly split."""
        raw_text = (
            "Tasks / Responsibilities: Design and maintain backend APIs.\n"
            "Expected skill set: Python, FastAPI, MongoDB."
        )
        res = normalize_job_description_presentation(
            raw_text,
            responsibilities=["Design and maintain backend APIs."],
            skills_required=["Python", "FastAPI", "MongoDB"],
        )
        # The inline headings must not leak as repeated raw prose or duplicate cards
        assert len(res.responsibilities) == 1
        # Detailed sections should not contain duplicate skill chips
        for sec in res.detailed_sections:
            for item in sec.items:
                assert item.text.strip() != "Expected skill set:"

    def test_f_html_paragraph_heading(self):
        """F. HTML paragraph headings like '<p><b>Job Description:</b></p>' are normalized."""
        html_text = "<p><b>Job Description:</b></p><p>Develop high performance microservices.</p>"
        res = normalize_job_description_presentation(html_text)
        # Responsibilities populated or detailed section clean
        all_text = " ".join(item.text for sec in res.detailed_sections for item in sec.items)
        assert "<b>" not in all_text
        assert "Develop high performance microservices." in (res.responsibilities or all_text)

    def test_g_same_content_in_canonical_card_suppressed_from_detailed_description(self):
        """G. Content already appearing in canonical section is suppressed from detailed description."""
        canonical_resp = [
            "Develop scalable microservices in Go and Python.",
            "Maintain 99.9% uptime across production clusters.",
        ]
        raw_text = (
            "## About Us\n"
            "Leading fintech platform in India.\n\n"
            "## Job Description\n"
            "- Develop scalable microservices in Go and Python.\n"
            "- Maintain 99.9% uptime across production clusters.\n"
        )
        res = normalize_job_description_presentation(
            raw_text,
            responsibilities=canonical_resp,
        )
        # Summary should exist
        assert res.summary is not None
        # Detailed sections should NOT repeat the exact same responsibilities
        detailed_items = [i.text for sec in res.detailed_sections for i in sec.items]
        for r in canonical_resp:
            assert r not in detailed_items

    def test_h_no_meaningful_section_no_empty_ui_section(self):
        """H. If a section has no meaningful content, it is omitted (no empty UI section)."""
        raw_text = "## Job Description\n\n## Qualifications\n\n## Additional Information\n"
        res = normalize_job_description_presentation(raw_text)
        assert res.summary is None
        assert res.additional_info is None
        assert len(res.detailed_sections) == 0

    def test_i_internship_description_normalization(self):
        """I. Internship descriptions are normalized identically to full-time jobs."""
        internship_text = (
            "## About Company\n"
            "Exciting fast-growing startup.\n\n"
            "## Job Description\n"
            "Internship Responsibilities:\n"
            "- Assist senior engineers in feature delivery\n"
            "- Write unit tests\n\n"
            "## Qualifications\n"
            "- Enrolled in B.Tech / B.E in CS\n"
        )
        res = normalize_job_description_presentation(internship_text)
        assert res.summary is not None
        assert len(res.responsibilities) > 0
        assert len(res.qualifications) > 0
        # No repeated "Job Description" headings in detailed sections
        for sec in res.detailed_sections:
            assert sec.title != "Job Description"

    def test_j_smartrecruiters_provider_normalization(self):
        """J. SmartRecruiters multi-section descriptions are normalized into clean hierarchy."""
        sr_desc = (
            "## Company Description\n"
            "Blueberry Digital Labs is a leading digital technology company.\n\n"
            "## Job Description\n"
            "Location: Waverock SEZ, Hyderabad\n"
            "Job Description:\n"
            "- Develop, test and deploy PHP web applications\n"
            "- Develop fast, scalable architecture\n\n"
            "## Qualifications\n"
            "B-tech, M-Tech\n\n"
            "## Additional Information\n"
            "Please send your resume to jobs@blueberrylabs.com\n"
        )
        canonical_resp = [
            "Develop, test and deploy PHP web applications",
            "Develop fast, scalable architecture",
        ]
        canonical_qual = ["B-tech, M-Tech"]

        res = normalize_job_description_presentation(
            sr_desc,
            responsibilities=canonical_resp,
            qualifications=canonical_qual,
        )
        assert res.summary is not None
        assert "Blueberry" in res.summary.items[0].text
        assert res.additional_info is not None
        assert any("jobs@blueberrylabs.com" in i.text for i in res.additional_info.items)
        # Responsibilities and qualifications should not be duplicated in detailed_sections
        detailed_texts = [i.text for sec in res.detailed_sections for i in sec.items]
        assert "Develop, test and deploy PHP web applications" not in detailed_texts
        assert "B-tech, M-Tech" not in detailed_texts

    def test_k_lever_provider_normalization(self):
        """K. Lever prose sections (Role Overview, Responsibilities) are normalized cleanly."""
        lever_desc = (
            "About Us\n"
            "Paytm is India's leading payments Super App.\n\n"
            "Role Overview\n"
            "We are looking for a strategic Analytics Leader.\n\n"
            "Key Responsibilities\n"
            "- Define and own analytics roadmap\n"
            "- Translate business problems into ML frameworks\n"
        )
        res = normalize_job_description_presentation(lever_desc)
        assert res.summary is not None
        assert len(res.responsibilities) > 0

    def test_l_greenhouse_provider_normalization(self):
        """L. Greenhouse HTML/markdown sections are normalized cleanly."""
        gh_desc = (
            "## The Opportunity\n"
            "At Postman, we are revolutionizing API collaboration.\n\n"
            "## What You'll Do\n"
            "- Build and manage scalable microservices\n"
            "- Optimize code for high throughput\n\n"
            "## Must Have Qualifications\n"
            "- 5+ years building backend systems\n"
        )
        res = normalize_job_description_presentation(gh_desc)
        assert res.summary is not None
        assert len(res.responsibilities) > 0

    def test_m_existing_bosch_mobile_requirements_remain_unchanged(self):
        """M. Existing Bosch Mobile extraction remains unchanged."""
        raw_jd = (
            "Tasks / Responsibilities:· Design, build, and maintain advanced applications for the iOS platform using Swift/Objective-C and AOS platform Java/Kotlin"
            "· Collaborate with cross-functional teams to define, design, and ship new features."
            "Expected skill set:· Strong proficiency in Swift and/or Objective-C. and AOS platform Java/Kotlin"
            "· In-depth understanding of the iOS SDK, Cocoa Touch, and UIKit framework."
            "· Solid understanding of object-oriented programming (OOP) principles and design patterns (e.g., MVVM, MVC, VIPER)."
            "· Experience with RESTful APIs to connect iOS applications to backend services.\n"
            "Good to have: Familiarity with dependency injection frameworks. Experience with CI/CD pipelines for mobile applications. · Familiarity with Figma, Sketch, or other design tools."
            "\n\nQualifications\nB.E or B.Tech\n\nAdditional Information\n5 - 8 Years"
        )
        cleaned = _clean_html_description(raw_jd)
        reqs = analyze_job_description(cleaned, "Senior Mobile APP (IOS/AOS) Developer")

        must_have = set(reqs.must_have_skills)
        expected_must_haves = [
            "Swift", "Objective-C", "Java", "Kotlin", "iOS SDK",
            "Cocoa Touch", "UIKit", "Object-Oriented Programming",
            "Design Patterns", "MVVM", "MVC", "VIPER", "REST APIs"
        ]
        for skill in expected_must_haves:
            assert skill in must_have, f"Missing required skill {skill}"

        preferred = set(reqs.preferred_skills)
        expected_preferred = ["CI/CD", "Dependency Injection", "Figma", "Sketch"]
        for skill in expected_preferred:
            assert skill in preferred, f"Missing preferred skill {skill}"

        assert reqs.min_years_experience == 5.0
        assert reqs.max_years_experience == 8.0
        assert "B.E or B.Tech" in reqs.qualifications

    def test_n_existing_bosch_hardware_extraction_remains_unchanged(self):
        """N. Existing Bosch Hardware extraction remains unchanged: 6-9 years, B.E, 0 fabricated skills."""
        raw_hw_jd = (
            "## Job Description\n"
            "Tasks / Responsibilities:\n"
            "- Requirement analysis and concept definition\n"
            "- Module / ECU design & Development - Worst case calculation & Simulation\n"
            "- Schematic & BOM preparation\n"
            "- Layout development - coordination\n"
            "- Sample development coordination with plant\n"
            "- Test plan preparation , ECU testing\n"
            "- EMC Test plan and EMC Tests co-ordination\n"
            "- Project documentation is per defined processDFMEA and Functional safety co-ordination\n\n"
            "## Qualifications\n"
            "B.E\n\n"
            "## Additional Information\n"
            "6 - 9 years"
        )
        cleaned = _clean_html_description(raw_hw_jd)
        reqs = analyze_job_description(cleaned, "Lead Hardware Engineer")

        assert reqs.min_years_experience == 6.0
        assert reqs.max_years_experience == 9.0
        assert "B.E" in reqs.qualifications
        assert len(reqs.must_have_skills) == 0
        assert len(reqs.responsibilities) == 8

    def test_o_spark_marketing_prose_protection_remains_unchanged(self):
        """O. Spark false-positive protection remains intact."""
        marketing_sentence = "Welcome to our team, where every story begins with a spark of inspiration."
        skills = extract_skills_from_text(marketing_sentence)
        assert "Spark" not in skills
        assert "Apache Spark" not in skills

        spark_jd = "Requirements:\n- 3+ years experience with Apache Spark and PySpark."
        reqs = analyze_job_description(spark_jd, "Data Engineer")
        assert "Spark" in reqs.must_have_skills or "Apache Spark" in reqs.must_have_skills
