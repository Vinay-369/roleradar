import pytest
from app.modules.resume.parsing.skills_depth import analyze_skills_depth


def test_skills_depth_comprehensive_stack():
    skills = [
        "Python", "TypeScript", "FastAPI", "React", "Next.js",
        "PostgreSQL", "Redis", "Docker", "Kubernetes", "AWS",
        "Data Structures", "System Design", "Git", "CI/CD",
    ]
    res = analyze_skills_depth(skills)
    assert res.score >= 80
    assert res.domain_coverage_count == 5  # Covers all 5 domains
    assert res.verified_skills_count >= 10
    assert len(res.missing_domains) == 0


def test_skills_depth_sparse_stack_with_junk():
    skills = [
        "Python", "Team player", "Good communication", "Hardworking",
    ]
    res = analyze_skills_depth(skills)
    assert res.verified_skills_count == 1  # Only Python is verified
    assert res.domain_coverage_count == 1
    assert len(res.missing_domains) >= 3
    assert len(res.issues) >= 1


def test_skills_depth_empty():
    res = analyze_skills_depth([])
    assert res.score <= 20
    assert res.verified_skills_count == 0
    assert res.domain_coverage_count == 0
