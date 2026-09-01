"""
Tests for Phase 2 Multi-Signal Career Classification and Template Strategy.
"""
import pytest
from app.modules.resume.classification import (
    CareerClassification,
    classify_candidate_profile,
)
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.strategy import (
    StrategyName,
    resolve_template_strategy,
)

STUDENT_RESUME = """
VIKAS K
Davangere, Karnataka | vikas@example.com | +91 9876543210

PROFESSIONAL SUMMARY
Motivated Computer Science undergraduate seeking Software Engineering internship.

EDUCATION
Bapuji Institute of Engineering and Technology
B.E in Computer Science and Engineering (2023 - 2027) | CGPA: 9.1 / 10.0

TECHNICAL SKILLS
Languages: Python, Java, C, JavaScript

TECHNICAL PROJECTS
• AI Viral Analyzer: Built Flask and OpenCV model achieving 91% accuracy.
• ShopVerse: Built full stack React and Node.js e-commerce app.

CERTIFICATIONS
• Smart India Hackathon
"""

SENIOR_RESUME = """
SARAH M
Seattle, WA | sarah@example.com | +1 206 555 0199

PROFESSIONAL SUMMARY
Senior Engineering Director with 12+ years of experience leading engineering organizations and distributed cloud architectures.

WORK EXPERIENCE
Director of Engineering at CloudVentures (2020 - Present) - Seattle, WA
• Managed 4 engineering teams totaling 28 engineers delivering enterprise SaaS platform.
• Spearheaded architecture modernization reducing cloud infrastructure costs by $1.2M annually.

Senior Software Architect at EnterpriseTech (2014 - 2020) - San Francisco, CA
• Architected multi-tenant Kubernetes platform handling 250M daily API calls.
• Mentored 15 junior and senior engineers across multiple global sites.

EDUCATION
University of Washington
M.S. in Computer Science (2012 - 2014)
"""


def test_classify_student_and_resolve_strategy():
    profile = extract_candidate_profile(STUDENT_RESUME)
    res = classify_candidate_profile(profile)

    assert res.classification in (CareerClassification.STUDENT, CareerClassification.FRESHER)
    assert res.is_student is True
    assert res.experience_level in ("STUDENT", "FRESHER/STUDENT")
    assert res.experience_depth == "NONE"
    assert res.project_depth == "STRONG"
    assert res.career_continuity == "STUDENT"
    assert res.confidence >= 0.85

    strategy = resolve_template_strategy(res)
    assert strategy.strategy_name == StrategyName.FRESHER_STUDENT
    assert strategy.highlight_education_top is True
    assert "education" in strategy.section_order[:4]


def test_classify_senior_leadership_and_resolve_strategy():
    profile = extract_candidate_profile(SENIOR_RESUME)
    res = classify_candidate_profile(profile)

    assert res.classification == CareerClassification.LEADERSHIP
    assert res.leadership_evidence is True
    assert res.years_of_experience >= 8.0
    assert res.experience_depth == "EXTENSIVE"
    assert res.professional_role_count == 2
    assert res.career_continuity == "CONTINUOUS"

    strategy = resolve_template_strategy(res)
    assert strategy.strategy_name == StrategyName.LEADERSHIP
    assert strategy.primary_emphasis == "EXECUTIVE_LEADERSHIP_AND_STRATEGY"


EARLY_CAREER_RESUME = """
ANIL SHARMA
Bangalore, India | anil@example.com | +91 9123456789

SUMMARY
Full Stack Engineer with 2.5 years of experience building web applications.

WORK EXPERIENCE
Software Engineer at TechCorp (2023 - Present) - Bangalore
• Developed React and Node.js microservices serving 100k daily requests.
• Optimized PostgreSQL query indexes, reducing latency by 25%.

Junior Developer at WebSolutions (2022 - 2023) - Bangalore
• Built frontend components using TypeScript and Tailwind CSS.

EDUCATION
VTU Belagavi
B.E in Information Science (2018 - 2022)

PROJECTS
• TaskFlow: Built Kanban task management app using React and Firebase.
"""

def test_classify_early_career_profile():
    profile = extract_candidate_profile(EARLY_CAREER_RESUME)
    res = classify_candidate_profile(profile)

    assert res.classification == CareerClassification.EARLY_CAREER
    assert res.experience_level == "EARLY_CAREER"
    assert res.years_of_experience >= 1.5
    assert res.professional_role_count == 2
    assert res.internship_presence is True or res.professional_role_count >= 2

    strategy = resolve_template_strategy(res)
    assert strategy.strategy_name == StrategyName.EARLY_CAREER
    assert strategy.highlight_education_top is False
    assert strategy.section_order[2] == "experience"

