from app.modules.intelligence.dashboard import compute_rri, recommend_next_action


def test_rri_weights_skill_coverage_most_heavily():
    high_skill = compute_rri(parseability_score=50, recruiter_impact_score=50, best_match_skill_score=100)
    high_structure = compute_rri(parseability_score=100, recruiter_impact_score=50, best_match_skill_score=50)
    assert high_skill > high_structure


def test_rri_is_zero_when_everything_is_zero():
    assert compute_rri(0, 0, 0) == 0


def test_rri_is_100_when_everything_is_perfect():
    assert compute_rri(100, 100, 100) == 100


def test_next_action_prioritizes_onboarding_first():
    action = recommend_next_action(
        resume_uploaded=True, onboarding_completed=False,
        parseability_score=90, recruiter_impact_score=90, top_matches=[],
    )
    assert "profile" in action.lower()


def test_next_action_prioritizes_resume_upload_second():
    action = recommend_next_action(
        resume_uploaded=False, onboarding_completed=True,
        parseability_score=None, recruiter_impact_score=None, top_matches=[],
    )
    assert "upload" in action.lower()


def test_next_action_flags_structural_issues_before_matches():
    action = recommend_next_action(
        resume_uploaded=True, onboarding_completed=True,
        parseability_score=40, recruiter_impact_score=90,
        top_matches=[{"job_title": "X", "company": "Y", "overall_score": 95, "apply_readiness": "ready", "missing_skills": []}],
    )
    assert "structural" in action.lower() or "ats" in action.lower()


def test_next_action_recommends_ready_match_when_everything_is_healthy():
    action = recommend_next_action(
        resume_uploaded=True, onboarding_completed=True,
        parseability_score=90, recruiter_impact_score=90,
        top_matches=[{"job_title": "Backend Developer", "company": "Acme", "overall_score": 95, "apply_readiness": "ready", "missing_skills": []}],
    )
    assert "Backend Developer" in action
    assert "Acme" in action


def test_next_action_points_to_specific_missing_skill_when_not_ready():
    action = recommend_next_action(
        resume_uploaded=True, onboarding_completed=True,
        parseability_score=90, recruiter_impact_score=90,
        top_matches=[{"job_title": "DevOps Engineer", "company": "Acme", "overall_score": 60, "apply_readiness": "learn_first", "missing_skills": ["Kubernetes"]}],
    )
    assert "Kubernetes" in action
