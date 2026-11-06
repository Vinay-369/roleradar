from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.ai_service import service as ai_service_module
from app.core.ai_service.schemas import InterviewQuestion, InterviewQuestionsResult
from app.core.ai_service.service import AIService
from app.modules.interview.role_banks import (
    ROLE_QUESTION_BANKS,
    get_curated_role_questions,
    get_role_specific_questions,
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


def test_non_software_roles_get_distinct_domain_questions():
    finance_questions = get_curated_role_questions("Financial Analyst")
    nursing_questions = get_curated_role_questions("Registered Nurse")

    finance_text = " ".join(question["question"] for question in finance_questions).lower()
    nursing_text = " ".join(question["question"] for question in nursing_questions).lower()

    assert finance_questions != nursing_questions
    assert "financial modeling" in finance_text
    assert "patient assessment" in nursing_text
    assert not any("software engineer" in question["question"].lower() for question in nursing_questions)


def test_role_specific_anchor_contains_selected_role():
    questions = get_role_specific_questions("Cybersecurity Analyst")
    assert len(questions) == 6
    assert all("cybersecurity analyst" in question["question"].lower() for question in questions)


@pytest.mark.asyncio
async def test_successful_ai_generation_keeps_role_specific_anchor(monkeypatch):
    service = AIService.__new__(AIService)
    service._settings = SimpleNamespace(AI_MAX_RETRIES=0, AI_PROVIDER="test")
    service._provider = object()
    service._log_operation = AsyncMock()
    monkeypatch.setattr(
        ai_service_module,
        "generate_structured",
        AsyncMock(
            return_value=InterviewQuestionsResult(
                questions=[
                    InterviewQuestion(
                        question="Tell me about a challenging project.",
                        category="hr",
                    )
                ]
            )
        ),
    )

    result = await service.generate_interview_questions(
        resume_summary="Candidate background",
        jd_text="Security monitoring and incident response",
        target_role="Cybersecurity Analyst",
        company="Example Security",
    )

    assert "cybersecurity analyst" in result.questions[0].question.lower()
    assert any(question.question == "Tell me about a challenging project." for question in result.questions)


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
