from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.interview import routes


@pytest.mark.asyncio
async def test_generate_prep_formats_structured_resume_entries(monkeypatch):
    resume = {
        "parsed": {
            "skills": ["Java", "Spring Boot"],
            "experience_raw": [
                {
                    "role": "Software Engineer",
                    "company": "Example Corp",
                    "bullets": ["Built a REST API"],
                }
            ],
            "projects_raw": [
                {
                    "title": "Inventory Platform",
                    "tech_stack": "Java, PostgreSQL",
                    "bullets": ["Reduced stock reconciliation time by 30%"],
                }
            ],
        }
    }
    generate_questions = AsyncMock(return_value=SimpleNamespace(questions=[]))
    ai_service = SimpleNamespace(generate_interview_questions=generate_questions)
    monkeypatch.setattr(
        routes.resume_repo,
        "get_active_master_resume",
        AsyncMock(return_value=resume),
    )
    monkeypatch.setattr(routes.profile_repo, "get_profile", AsyncMock(return_value=None))

    result = await routes._generate_prep(
        db=object(),
        ai_service=ai_service,
        user_id="user-1",
        role="Java Full Stack Developer",
    )

    resume_summary = generate_questions.await_args.kwargs["resume_summary"]
    assert "Skills: Java, Spring Boot." in resume_summary
    assert "Software Engineer — Example Corp — Built a REST API" in resume_summary
    assert (
        "Inventory Platform — Technologies: Java, PostgreSQL — "
        "Reduced stock reconciliation time by 30%"
    ) in resume_summary
    assert result.job_title == "Java Full Stack Developer"


def test_format_resume_entries_keeps_legacy_strings_and_skips_invalid_values():
    entries = ["Built web services", {"title": "Project", "bullets": ["Shipped feature"]}, None, 42]

    assert routes._format_resume_entries(entries) == (
        "Built web services | Project — Shipped feature"
    )
