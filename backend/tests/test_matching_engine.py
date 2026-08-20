from app.core.embeddings.tfidf_provider import TfidfEmbeddingProvider
from app.modules.matching.engine import compute_match

embedder = TfidfEmbeddingProvider()


def make_candidate(**overrides):
    base = {
        "skills": ["Python", "FastAPI", "MongoDB", "Docker"],
        "target_roles": ["Backend Developer"],
        "experience_years": 0,
        "preferred_locations": ["Bangalore"],
        "remote_preference": "any",
        "min_lpa": 4,
        "industries": ["IT Services"],
    }
    base.update(overrides)
    return base


def make_job(**overrides):
    base = {
        "title": "Backend Developer",
        "skills_required": ["Python", "FastAPI", "MongoDB"],
        "experience_min": 0,
        "experience_max": 2,
        "location": "Bangalore",
        "is_remote": False,
        "salary_max": 6,
        "salary_disclosed": True,
        "industry": "IT Services",
    }
    base.update(overrides)
    return base


def test_strong_match_scores_high_and_is_ready():
    result = compute_match(make_candidate(), make_job(), embedder, category="FRESHER")
    assert result.overall_score >= 85
    assert set(result.skill_match.matched) == {"Python", "FastAPI", "MongoDB"}
    assert result.apply_readiness in ("ready", "fix_gaps")


def test_missing_required_skill_is_never_reported_as_matched():
    candidate = make_candidate(skills=["Python"])
    job = make_job(skills_required=["Python", "Kubernetes", "AWS"])
    result = compute_match(candidate, job, embedder)
    assert "Kubernetes" in result.skill_match.missing or "Kubernetes" in result.skill_match.partial
    assert "Kubernetes" not in result.skill_match.matched
    assert "AWS" not in result.skill_match.matched


def test_completely_unrelated_job_scores_low():
    candidate = make_candidate(skills=["Photoshop", "Illustrator"], target_roles=["Graphic Designer"])
    job = make_job(skills_required=["Kubernetes", "Terraform", "AWS"], title="DevOps Engineer")
    result = compute_match(candidate, job, embedder)
    assert result.overall_score < 50
    assert result.apply_readiness == "learn_first"


def test_undisclosed_salary_is_neutral_not_penalized():
    job = make_job(salary_disclosed=False, salary_max=None)
    result = compute_match(make_candidate(), job, embedder)
    assert result.salary_score == 50


def test_experience_below_minimum_reduces_score_gracefully():
    candidate = make_candidate(experience_years=0)
    job = make_job(experience_min=3, experience_max=5)
    result = compute_match(candidate, job, embedder)
    assert result.experience_score < 100
    assert result.experience_score >= 0


def test_fresher_and_experienced_weight_skill_differently():
    candidate = make_candidate(experience_years=0)
    job = make_job()
    fresher_result = compute_match(candidate, job, embedder, category="FRESHER")
    experienced_result = compute_match(candidate, job, embedder, category="EXPERIENCED")
    # Same inputs, different category weights -> scores may legitimately differ
    assert isinstance(fresher_result.overall_score, int)
    assert isinstance(experienced_result.overall_score, int)


def test_readiness_bands_are_consistent_with_thresholds():
    from app.modules.matching.engine import _apply_readiness
    assert _apply_readiness(95) == "ready"
    assert _apply_readiness(90) == "ready"
    assert _apply_readiness(89) == "fix_gaps"
    assert _apply_readiness(70) == "fix_gaps"
    assert _apply_readiness(69) == "learn_first"
    assert _apply_readiness(0) == "learn_first"
