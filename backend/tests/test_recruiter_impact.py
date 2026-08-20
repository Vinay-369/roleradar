from app.modules.resume.parsing.recruiter_impact import analyze_recruiter_impact


def test_scores_strong_quantified_bullets_highly():
    bullets = [
        "Built a REST API serving 10,000 requests per day",
        "Reduced page load time by 40% through query optimization",
        "Led a team of 3 engineers to ship the feature 2 weeks early",
    ]
    result = analyze_recruiter_impact(bullets)
    assert result.score >= 70
    assert result.quantified_bullets == 3
    assert result.weak_verb_bullets == 0


def test_flags_weak_verbs_and_missing_numbers():
    bullets = [
        "Helped the team with various tasks",
        "Responsible for the backend",
        "Assisted in project development",
    ]
    result = analyze_recruiter_impact(bullets)
    assert result.score < 50
    assert result.weak_verb_bullets == 3
    assert result.quantified_bullets == 0
    assert any("weak verb" in issue for issue in result.issues)


def test_handles_empty_bullet_list():
    result = analyze_recruiter_impact([])
    assert result.score == 0
    assert result.bullets_analyzed == 0
    assert result.issues


def test_quantification_detects_percent_and_plain_numbers():
    bullets = ["Improved accuracy by 15%", "Managed a budget of 50000 rupees"]
    result = analyze_recruiter_impact(bullets)
    assert result.quantified_bullets == 2
