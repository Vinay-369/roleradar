"""
Tests for Phase 10: ATS Structure + Template Strategy.
Validates:
- Deterministic section ordering across career classifications (Fresher, Professional, Senior, Executive, Academic, Switcher)
- Dynamic page budgeting and bullet limits
- Content emphasis (Projects vs Experience)
- Standard ATS headings and parseability constraints
"""
import pytest
from app.modules.resume.classification import (
    CandidateAnalysisResult,
    CareerClassification,
    CareerClassificationResult,
)
from app.modules.tailoring.strategy import (
    STANDARD_ATS_HEADINGS,
    StrategyName,
    TemplateStrategy,
    resolve_template_strategy,
)


def test_fresher_strategy_prioritizes_education_and_projects():
    classification = CareerClassificationResult(
        classification=CareerClassification.FRESHER,
        confidence=0.95,
        years_of_experience=0.0,
        skill_count=6,
        project_count=3,
        role_count=0,
    )
    strategy = resolve_template_strategy(classification, target_role="Junior Python Developer")

    assert strategy.strategy_name == StrategyName.FRESHER_STUDENT
    assert strategy.highlight_education_top is True
    assert strategy.project_emphasis is True
    assert strategy.experience_emphasis is False
    assert strategy.page_budget == 1

    # Education precedes Experience in section order
    edu_idx = strategy.section_order.index("education")
    exp_idx = strategy.section_order.index("experience")
    proj_idx = strategy.section_order.index("projects")
    assert edu_idx < exp_idx
    assert proj_idx < exp_idx


def test_experienced_professional_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.PROFESSIONAL,
        confidence=0.90,
        years_of_experience=4.5,
        skill_count=12,
        project_count=2,
        role_count=2,
    )
    strategy = resolve_template_strategy(classification, target_role="Backend Software Engineer")

    assert strategy.strategy_name == StrategyName.PROFESSIONAL
    assert strategy.highlight_education_top is False
    assert strategy.experience_emphasis is True
    assert strategy.page_budget == 1

    exp_idx = strategy.section_order.index("experience")
    edu_idx = strategy.section_order.index("education")
    assert exp_idx < edu_idx


def test_senior_and_executive_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.LEADERSHIP,
        confidence=0.95,
        years_of_experience=10.0,
        skill_count=15,
        project_count=1,
        role_count=4,
    )
    strategy = resolve_template_strategy(classification, target_role="Director of Engineering")

    assert strategy.strategy_name == StrategyName.LEADERSHIP
    assert strategy.summary_style == "EXECUTIVE"
    assert strategy.page_budget == 2
    assert strategy.primary_emphasis == "EXECUTIVE_LEADERSHIP_AND_STRATEGY"


def test_academic_and_research_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.RESEARCH,
        confidence=0.95,
        years_of_experience=3.0,
        skill_count=8,
        project_count=2,
        role_count=1,
    )
    strategy = resolve_template_strategy(classification, target_role="Research Scientist")

    assert strategy.strategy_name == StrategyName.ACADEMIC_RESEARCH
    assert strategy.highlight_education_top is True
    assert "publications" in strategy.included_sections
    assert "research" in strategy.included_sections

    pub_idx = strategy.section_order.index("publications")
    exp_idx = strategy.section_order.index("experience")
    assert pub_idx < exp_idx


def test_career_switcher_strategy():
    classification = CareerClassificationResult(
        classification=CareerClassification.CAREER_SWITCHER,
        confidence=0.90,
        years_of_experience=5.0,
        skill_count=10,
        project_count=4,
        role_count=2,
    )
    strategy = resolve_template_strategy(classification, target_role="Full Stack Developer")

    assert strategy.strategy_name == StrategyName.CAREER_SWITCHER
    assert strategy.project_emphasis is True

    # Projects precede historical experience
    proj_idx = strategy.section_order.index("projects")
    exp_idx = strategy.section_order.index("experience")
    assert proj_idx < exp_idx


def test_standard_ats_headings_are_clean_and_parseable():
    for key, heading in STANDARD_ATS_HEADINGS.items():
        assert heading.isupper()
        assert len(heading) >= 3
        # Zero non-standard decorative symbols
        assert not any(c in heading for c in ["★", "●", "◆", "▶", "|", "~"])
