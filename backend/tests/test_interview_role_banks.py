import pytest
from app.modules.interview.role_banks import (
    ROLE_QUESTION_BANKS,
    get_curated_role_questions,
)


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
    assert fe_questions == ROLE_QUESTION_BANKS["frontend"]

    # Backend matches
    be_questions = get_curated_role_questions("Python Backend Developer")
    assert be_questions == ROLE_QUESTION_BANKS["backend"]

    # Fullstack matches
    fs_questions = get_curated_role_questions("Full Stack Web Developer")
    assert fs_questions == ROLE_QUESTION_BANKS["full_stack"]

    # Data Science matches
    ds_questions = get_curated_role_questions("Machine Learning / AI Engineer")
    assert ds_questions == ROLE_QUESTION_BANKS["data_science"]

    # DevOps matches
    do_questions = get_curated_role_questions("Cloud DevOps & SRE Engineer")
    assert do_questions == ROLE_QUESTION_BANKS["devops"]

    # Fallback to Core SWE
    swe_questions = get_curated_role_questions("General Software Engineer")
    assert swe_questions == ROLE_QUESTION_BANKS["core_swe"]
