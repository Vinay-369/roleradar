import pytest
from app.modules.resume.parsing.action_verbs import analyze_action_verbs


def test_action_verbs_strong_bullets():
    bullets = [
        "Architected and deployed microservices backend using FastAPI and PostgreSQL.",
        "Optimized database query performance, reducing p99 latency by 45%.",
        "Engineered automated CI/CD pipeline with GitHub Actions and Docker.",
        "Spearheaded the migration of monolithic services to distributed Kubernetes clusters.",
    ]
    res = analyze_action_verbs(bullets)
    assert res.score >= 85
    assert res.total_bullets == 4
    assert res.strong_verb_bullets == 4
    assert res.weak_verb_bullets == 0
    assert res.power_verb_rate == 1.0
    assert len(res.strong_verbs_found) >= 3


def test_action_verbs_weak_bullets():
    bullets = [
        "Helped the team with bug fixes and code review.",
        "Responsible for writing SQL queries.",
        "Assisted senior developer with backend tasks.",
        "Participated in daily standups and sprint planning.",
    ]
    res = analyze_action_verbs(bullets)
    assert res.score < 60
    assert res.weak_verb_bullets >= 3
    assert len(res.weak_verbs_found) >= 2
    assert len(res.issues) >= 1
    assert len(res.recommendations) >= 1


def test_action_verbs_empty():
    res = analyze_action_verbs([])
    assert res.score == 0
    assert res.total_bullets == 0
