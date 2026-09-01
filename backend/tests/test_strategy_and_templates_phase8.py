"""
Dedicated Test Suite for Phase 8: Data-Driven ATS Strategy & Resume Layout Mapping.
Validates:
- student/fresher strategy resolution
- entry-level strategy resolution
- experienced / early-career strategy resolution
- senior/professional strategy resolution
- candidate type, section priority, ordering, template variant
- data-driven rendering of the SAME CandidateProfile across multiple strategies without fact alteration
"""
import pytest
from app.modules.resume.classification import (
    CareerClassification,
    CareerClassificationResult,
    classify_candidate_profile,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.strategy import (
    StrategyName,
    TemplateStrategy,
    render_profile_with_strategy,
    resolve_template_strategy,
)

SAMPLE_RESUME = """
ALEX CHEN
San Francisco, CA | alex@example.com | 555-0199

PROFESSIONAL SUMMARY
Full Stack Engineer with 4 years experience building distributed web services.

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, Go, SQL
Frameworks & Databases: FastAPI, React, Node.js, PostgreSQL, Redis, Docker

WORK EXPERIENCE
Software Engineer at ScaleData (2022 - Present) - San Francisco, CA
• Architected real-time stream processing pipeline using Python and Redis, reducing latency by 35%.
• Optimized PostgreSQL query execution plans across 50M records.

Software Engineer Intern at BetaCorp (2021 - 2022) - Remote
• Built automated CI/CD deployment pipelines using Docker.

PROJECTS
• Distributed File Storage Engine (Go, Raft): Built fault-tolerant distributed key-value store.

EDUCATION
University of California, Berkeley
B.S. in Computer Science (2018 - 2022) - GPA: 3.8

CERTIFICATIONS
AWS Certified Developer Associate (2023)

LANGUAGES
English (Fluent), Mandarin (Native)
"""


def test_student_fresher_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.FRESHER,
        confidence=0.95,
        reasoning=["Student/Fresher profile with strong academic projects"],
        experience_depth="ACADEMIC_INTERNSHIP",
        project_depth="COMPREHENSIVE_SHOWCASE",
    )
    strategy = resolve_template_strategy(classification)
    
    assert strategy.strategy_name == StrategyName.FRESHER_STUDENT
    assert strategy.candidate_type == "student/fresher"
    assert strategy.template_variant == "modern"
    assert strategy.highlight_education_top is True
    # Education appears before projects and internships
    edu_idx = strategy.section_order.index("education")
    proj_idx = strategy.section_order.index("projects")
    assert edu_idx < proj_idx


def test_entry_level_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.ENTRY_LEVEL,
        confidence=0.90,
        reasoning=["Entry level engineer with 1-2 years experience"],
        experience_depth="EARLY_PROFESSIONAL",
        project_depth="PRACTICAL_SHOWCASE",
    )
    strategy = resolve_template_strategy(classification)
    
    assert strategy.strategy_name == StrategyName.ENTRY_LEVEL
    assert strategy.candidate_type == "entry-level"
    assert strategy.template_variant == "modern"
    assert strategy.highlight_education_top is False
    assert "experience" in strategy.section_order


def test_experienced_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.EARLY_CAREER,
        confidence=0.92,
        reasoning=["Experienced engineer with 3-5 years track record"],
        experience_depth="CORE_ENGINEERING",
        project_depth="SUPPORTING_PORTFOLIO",
    )
    strategy = resolve_template_strategy(classification)
    
    assert strategy.strategy_name == StrategyName.EARLY_CAREER
    assert strategy.candidate_type == "experienced"
    assert strategy.template_variant == "classic"
    assert strategy.primary_emphasis == "CORE_ENGINEERING_AND_OWNERSHIP"


def test_senior_professional_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.SENIOR_PROFESSIONAL,
        confidence=0.95,
        reasoning=["Senior technical lead with 7+ years track record"],
        experience_depth="SENIOR_STAFF",
        project_depth="EXECUTIVE_IMPACT",
    )
    strategy = resolve_template_strategy(classification)
    
    assert strategy.strategy_name == StrategyName.SENIOR
    assert strategy.candidate_type == "senior/professional"
    assert strategy.template_variant == "executive"
    assert strategy.max_recommended_bullets_per_role == 5


def test_same_profile_renderable_across_strategies_without_fact_alteration():
    """
    Guarantees that the same CandidateProfile can be rendered into different strategy layouts
    without altering any candidate facts, metrics, or evidence units.
    """
    profile = extract_candidate_profile(SAMPLE_RESUME)
    
    # 1. Fresher Strategy (Education prioritized at top)
    fresher_strat = TemplateStrategy(
        strategy_name=StrategyName.FRESHER_STUDENT,
        candidate_type="student/fresher",
        template_variant="modern",
        section_order=["summary", "skills", "education", "projects", "experience", "certifications", "languages"],
        highlight_education_top=True,
    )
    rendered_fresher = render_profile_with_strategy(profile, fresher_strat)

    # 2. Senior Strategy (Experience & Impact prioritized)
    senior_strat = TemplateStrategy(
        strategy_name=StrategyName.SENIOR,
        candidate_type="senior/professional",
        template_variant="executive",
        section_order=["summary", "skills", "experience", "projects", "certifications", "education", "languages"],
        highlight_education_top=False,
    )
    rendered_senior = render_profile_with_strategy(profile, senior_strat)

    # Invariants: Factual content must remain 100% identical across strategies
    assert rendered_fresher["personal"]["name"] == rendered_senior["personal"]["name"] == "ALEX CHEN"
    assert rendered_fresher["skills"] == rendered_senior["skills"]
    assert rendered_fresher["education_raw"] == rendered_senior["education_raw"]
    assert rendered_fresher["experience_raw"] == rendered_senior["experience_raw"]
    assert rendered_fresher["projects_raw"] == rendered_senior["projects_raw"]

    # Invariants: Strategy metadata and ordering reflect the distinct strategies
    assert rendered_fresher["_ordered_sections"] == fresher_strat.section_order
    assert rendered_senior["_ordered_sections"] == senior_strat.section_order
