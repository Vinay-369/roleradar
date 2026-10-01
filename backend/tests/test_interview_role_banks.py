import pytest
from app.modules.interview.role_banks import (
    ROLE_QUESTION_BANKS,
    get_curated_role_questions,
)
from app.core.ai_service.prompts.interview import build_interview_user_prompt


def test_role_banks_completeness():
    expected_disciplines = ["full_stack", "backend", "frontend", "data_science", "devops", "core_swe"]
    for role_key in expected_disciplines:
        assert role_key in ROLE_QUESTION_BANKS
        questions = ROLE_QUESTION_BANKS[role_key]
        assert len(questions) >= 5
        for q in questions:
            assert "question" in q
            assert "category" in q
            assert q["category"] in {"technical", "managerial", "hr"}
            assert "star_hint" in q
            assert "strategy" in q
            assert "sample_answer" in q
            assert "pitfalls" in q


def test_get_curated_role_questions_matching():
    # Frontend matches
    fe_questions = get_curated_role_questions("Senior React Frontend Engineer")
    assert fe_questions[:len(ROLE_QUESTION_BANKS["frontend"])] == ROLE_QUESTION_BANKS["frontend"]

    # Backend matches
    be_questions = get_curated_role_questions("Python Backend Developer")
    assert be_questions[:len(ROLE_QUESTION_BANKS["backend"])] == ROLE_QUESTION_BANKS["backend"]

    # Fullstack matches
    fs_questions = get_curated_role_questions("Full Stack Web Developer")
    assert fs_questions[:len(ROLE_QUESTION_BANKS["full_stack"])] == ROLE_QUESTION_BANKS["full_stack"]

    # Data Science matches
    ds_questions = get_curated_role_questions("Machine Learning / AI Engineer")
    assert ds_questions[:len(ROLE_QUESTION_BANKS["data_science"])] == ROLE_QUESTION_BANKS["data_science"]

    # DevOps matches
    do_questions = get_curated_role_questions("Cloud DevOps & SRE Engineer")
    assert do_questions[:len(ROLE_QUESTION_BANKS["devops"])] == ROLE_QUESTION_BANKS["devops"]

    # Fallback to Core SWE
    swe_questions = get_curated_role_questions("General Software Engineer")
    assert swe_questions[:len(ROLE_QUESTION_BANKS["core_swe"])] == ROLE_QUESTION_BANKS["core_swe"]


@pytest.mark.parametrize(
    "role",
    [
        "Java Full Stack Developer",
        "Financial Analyst",
        "Registered Nurse",
    ],
)
def test_curated_fallback_has_more_questions_in_every_round(role):
    questions = get_curated_role_questions(role)
    counts = {
        category: sum(question["category"] == category for question in questions)
        for category in ("technical", "managerial", "hr")
    }

    assert len(questions) >= 17
    assert all(count >= 4 for count in counts.values())
    assert len({question["question"] for question in questions}) == len(questions)
    assert any(role in question["question"] for question in questions)


@pytest.mark.parametrize(
    "role",
    [
        "Java Full Stack Developer",
        "Python Full Stack Developer",
        "MERN Full Stack Developer",
        "Registered Nurse",
        "Financial Analyst",
    ],
)
def test_interview_prompt_preserves_exact_specialized_role(role):
    prompt = build_interview_user_prompt(
        resume_summary="Candidate has relevant experience.",
        jd_text="Role-specific job context.",
        target_role=role,
    )

    assert f'TARGET ROLE: {role}' in prompt
    assert f'the exact role "{role}"' in prompt
    assert "explicitly test the named stack, tools, standards, or workflows" in prompt
    assert "24-30 highly relevant interview questions" in prompt
