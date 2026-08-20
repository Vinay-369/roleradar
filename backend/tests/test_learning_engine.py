from app.modules.learning.engine import build_roadmap, compute_skill_gaps


def test_missing_required_skills_are_core_priority():
    gaps = compute_skill_gaps(
        missing_required=["Docker", "Kubernetes"],
        partial_required=[],
        missing_nice_to_have=[],
        job_title="Backend Developer",
    )
    assert len(gaps) == 2
    assert all(g.priority == "CORE" for g in gaps)
    assert all(g.current_evidence == "MISSING" for g in gaps)


def test_partial_required_skills_are_secondary_priority():
    gaps = compute_skill_gaps(
        missing_required=[],
        partial_required=["Machine Learning"],
        missing_nice_to_have=[],
        job_title="ML Engineer",
    )
    assert gaps[0].priority == "SECONDARY"
    assert gaps[0].current_evidence == "PARTIAL"


def test_nice_to_have_skills_are_bonus_priority():
    gaps = compute_skill_gaps(
        missing_required=[],
        partial_required=[],
        missing_nice_to_have=["GraphQL"],
        job_title="Backend Developer",
    )
    assert gaps[0].priority == "BONUS"


def test_every_gap_has_resources_and_a_project_suggestion():
    gaps = compute_skill_gaps(
        missing_required=["Docker"],
        partial_required=[],
        missing_nice_to_have=[],
        job_title="DevOps Engineer",
    )
    assert len(gaps[0].resources) > 0
    assert "Docker" in gaps[0].project_suggestion


def test_unknown_skill_gets_honest_fallback_resource_not_fabricated_link():
    gaps = compute_skill_gaps(
        missing_required=["SomeVeryObscureFramework123"],
        partial_required=[],
        missing_nice_to_have=[],
        job_title="Backend Developer",
    )
    assert "youtube.com/results" in gaps[0].resources[0]


def test_roadmap_prioritizes_core_gaps_earliest():
    gaps = compute_skill_gaps(
        missing_required=["Docker", "Kubernetes", "AWS"],
        partial_required=["Terraform", "CI/CD"],
        missing_nice_to_have=["GraphQL"],
        job_title="DevOps Engineer",
    )
    roadmap = build_roadmap(gaps)
    assert "Docker" in roadmap["immediate"] or "Kubernetes" in roadmap["immediate"]
    assert "GraphQL" in roadmap["month_1"]


def test_roadmap_handles_no_gaps():
    roadmap = build_roadmap([])
    assert roadmap == {"immediate": [], "week_1": [], "week_2": [], "month_1": []}


def test_roadmap_distributes_gaps_evenly_not_leaving_arbitrary_empty_windows():
    """Regression test: previously, a small number of CORE gaps with no
    SECONDARY/BONUS gaps would leave week_2 and month_1 completely
    empty even though there were more gaps that could have been
    scheduled there. Even distribution fixes this."""
    gaps = compute_skill_gaps(
        missing_required=["Docker", "Kubernetes", "AWS", "Terraform"],
        partial_required=[],
        missing_nice_to_have=[],
        job_title="DevOps Engineer",
    )
    roadmap = build_roadmap(gaps)
    non_empty_windows = sum(1 for bucket in roadmap.values() if bucket)
    assert non_empty_windows == 4  # all 4 CORE gaps spread across all 4 windows


def test_roadmap_never_drops_a_gap():
    gaps = compute_skill_gaps(
        missing_required=["A", "B", "C"],
        partial_required=["D", "E"],
        missing_nice_to_have=["F"],
        job_title="Role",
    )
    roadmap = build_roadmap(gaps)
    all_scheduled = roadmap["immediate"] + roadmap["week_1"] + roadmap["week_2"] + roadmap["month_1"]
    assert sorted(all_scheduled) == sorted(["A", "B", "C", "D", "E", "F"])
