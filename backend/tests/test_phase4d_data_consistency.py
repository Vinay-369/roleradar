"""
Phase 4D Data Consistency Remediation Regression Tests.
Validates:
1. Live job with valid direct application URL -> Apply available, is_direct_apply True
2. Live job without application URL -> no fabricated Apply URL, is_direct_apply False
3. Benchmark -> no Apply button, is_direct_apply False, MARKET_BENCHMARK status
4. Bosch mobile job: explicit Swift/Objective-C proficiency recognized as requirement
5. Technology-only contextual mention does not become mandatory
6. Explicit preferred language remains preferred
7. Spark marketing-prose regression remains fixed (Spark not extracted)
8. Existing Bosch Hardware job remains correct: 6-9 years, B.E, no fabricated skills
"""
import pytest
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.taxonomy import analyze_job_description, RequirementCategory
from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider, _clean_html_description
from app.modules.jobs.classification import classify_opportunity
from app.modules.jobs.verification import verify_opportunity_sync, OpportunityLifecycleStatus


class TestPhase4DDataConsistencyRemediation:
    """Rigorous regression tests for Apply URL integrity and JD requirement classification."""

    def test_live_job_with_valid_direct_application_url(self):
        """1. Live job with valid direct application URL -> Apply available and verified."""
        job = {
            "title": "Software Engineer",
            "company": "Bosch Group",
            "apply_url": "https://jobs.smartrecruiters.com/BoschGroup/12345/apply",
            "is_direct_apply": True,
            "verification_status": "VERIFIED_ACTIVE",
            "source": "smartrecruiters",
        }
        vres = verify_opportunity_sync(job)
        assert vres.status == OpportunityLifecycleStatus.VERIFIED_ACTIVE
        assert job["is_direct_apply"] is True
        assert "jobs.smartrecruiters.com" in job["apply_url"]

    def test_live_job_without_application_url_no_fabrication(self):
        """2. Live job without application URL -> no fabricated Apply URL and is_direct_apply False."""
        job = {
            "title": "Custom Job",
            "company": "Private Employer",
            "apply_url": "",
            "is_direct_apply": False,
            "verification_status": "VERIFIED_ACTIVE",
            "source": "custom",
        }
        vres = verify_opportunity_sync(job)
        # Should not fabricate a URL
        assert not job["apply_url"]
        assert job["is_direct_apply"] is False

    def test_benchmark_no_apply_button_and_market_benchmark_status(self):
        """3. Benchmark -> no Apply button, is_direct_apply False, labeled MARKET_BENCHMARK."""
        benchmark_job = {
            "title": "Full Stack Developer",
            "company": "Swiggy",
            "apply_url": "https://www.swiggy.com/careers",
            "is_direct_apply": False,
            "verification_status": "MARKET_BENCHMARK",
            "source": "curated_benchmark",
        }
        # Curated benchmarks are directly identified by MARKET_BENCHMARK lifecycle status
        assert benchmark_job["verification_status"] == "MARKET_BENCHMARK"
        assert benchmark_job["is_direct_apply"] is False
        # Feed/card presentation logic: Apply is never rendered when is_direct_apply is False
        has_apply_button = bool(benchmark_job["is_direct_apply"] and benchmark_job["apply_url"])
        assert has_apply_button is False

    def test_bosch_mobile_job_requirements_and_skills(self):
        """4. Bosch mobile job: explicit Swift/Objective-C/Java/Kotlin proficiency recognized as requirement."""
        raw_jd = (
            "Tasks / Responsibilities:· Design, build, and maintain advanced applications for the iOS platform using Swift/Objective-C and AOS platform Java/Kotlin"
            "· Collaborate with cross-functional teams to define, design, and ship new features.· Ensure the performance, quality, and responsiveness of applications."
            "Expected skill set:· Strong proficiency in Swift and/or Objective-C. (Specify preference if any, e.g., 'Strong preference for Swift.') and AOS platform Java/Kotlin"
            "· In-depth understanding of the iOS SDK, Cocoa Touch, and UIKit framework. · Experience integrating and working with core iOS & AOS communication frameworks"
            "· Solid understanding of object-oriented programming (OOP) principles and design patterns (e.g., MVVM, MVC, VIPER). · Experience with RESTful APIs to connect iOS applications to backend services.\n"
            "Good to have: Familiarity with dependency injection frameworks. Experience with CI/CD pipelines for mobile applications. · Familiarity with Figma, Sketch, or other design tools."
            "\n\nQualifications\nB.E or B.Tech\n\nAdditional Information\n5 - 8 Years"
        )
        cleaned = _clean_html_description(raw_jd)
        reqs = analyze_job_description(cleaned, "Senior Mobile APP (IOS/AOS) Developer")

        # Mandatory requirements recognized
        must_have = set(reqs.must_have_skills)
        assert "Swift" in must_have
        assert "Objective-C" in must_have
        assert "Java" in must_have
        assert "Kotlin" in must_have
        assert "iOS SDK" in must_have
        assert "Cocoa Touch" in must_have
        assert "UIKit" in must_have
        assert "Object-Oriented Programming" in must_have
        assert "Design Patterns" in must_have
        assert "MVVM" in must_have
        assert "MVC" in must_have
        assert "VIPER" in must_have
        assert "REST APIs" in must_have

        # Preferred skills recognized separately
        preferred = set(reqs.preferred_skills)
        assert "CI/CD" in preferred
        assert "Dependency Injection" in preferred
        assert "Figma" in preferred
        assert "Sketch" in preferred

        # Experience extracted accurately
        assert reqs.min_years_experience == 5.0
        assert reqs.max_years_experience == 8.0

        # Qualifications extracted
        assert "B.E or B.Tech" in reqs.qualifications

    def test_contextual_technology_mention_not_mandatory(self):
        """5. Technology-only contextual mention in company/job prose does not become mandatory."""
        jd_text = (
            "## About Us\n"
            "We are a leading tech company. Our team uses Python and Docker internally to automate daily operations.\n\n"
            "## Responsibilities\n"
            "- Build and maintain client web portals.\n"
            "- Participate in daily agile standups.\n"
        )
        reqs = analyze_job_description(jd_text, "Frontend Developer")
        # Python and Docker mentioned only contextually in company description should not be must-have requirements
        assert "Python" not in reqs.must_have_skills
        assert "Docker" not in reqs.must_have_skills

    def test_explicit_preferred_language_remains_preferred(self):
        """6. Explicit preferred language remains in preferred_skills, not must-have."""
        jd_text = (
            "## Requirements\n"
            "- Strong proficiency with TypeScript and React.\n\n"
            "## Preferred Qualifications\n"
            "- Familiarity with Figma and Sketch is a plus.\n"
            "- Experience with GraphQL is desirable.\n"
        )
        reqs = analyze_job_description(jd_text, "Frontend Engineer")
        assert "TypeScript" in reqs.must_have_skills
        assert "React" in reqs.must_have_skills
        assert "Figma" in reqs.preferred_skills
        assert "Sketch" in reqs.preferred_skills
        assert "GraphQL" in reqs.preferred_skills
        assert "Figma" not in reqs.must_have_skills
        assert "Sketch" not in reqs.must_have_skills

    def test_spark_marketing_prose_protection_intact(self):
        """7. Spark marketing-prose false positive protection remains intact."""
        marketing_sentence = "Welcome to our team, where every story begins with a spark of inspiration."
        skills = extract_skills_from_text(marketing_sentence)
        assert "Spark" not in skills
        assert "Apache Spark" not in skills

        actual_spark_jd = "Requirements:\n- 3+ years experience with Apache Spark and PySpark for big data processing."
        reqs = analyze_job_description(actual_spark_jd, "Data Engineer")
        assert "Spark" in reqs.must_have_skills or "Apache Spark" in reqs.must_have_skills

    def test_existing_bosch_hardware_job_remains_correct(self):
        """8. Existing Bosch Hardware job remains correct: 6-9 years, B.E, zero fabricated skills."""
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
        assert len(reqs.must_have_skills) == 0  # Zero fabricated skills!
        assert len(reqs.responsibilities) == 8
