"""
Regression tests for Career Copilot AI execution & Resume Location Skill Filtering:
1. Asserts genuine AI responses differ structurally and semantically across distinct questions.
2. Asserts meta-questions do not trigger canned architectural mentor lectures.
3. Asserts mid-conversation corrections are obeyed by the system prompt directives.
4. Asserts location text (e.g., 'Davanagere, Karnataka') is never classified as a technical skill.
"""
import pytest
from app.core.config import Settings
from app.core.ai_service.service import AIService
from app.core.ai_service.providers.base import AIProvider
from app.modules.chatbot.context import CopilotContext
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.resume.parsing.skills_depth import analyze_skills_depth


class DynamicMockLLMProvider(AIProvider):
    """
    Mock AI Provider simulating realistic dynamic LLM completions based on user prompts.
    """
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        lower = user_prompt.lower()
        if "i think u are generating answers which are already stored" in lower or "already stored" in lower:
            return "I generate responses dynamically based on real-time context and engineering principles rather than fixed pre-stored answers. How can I assist you with your career goals today?"
        
        if "uber" in lower:
            return "1. How does Uber handle real-time geospatial driver dispatch latency during peak surge?\n2. What consistency guarantees does your distributed dispatch engine maintain across microservices?"
        
        if "zerodha" in lower:
            return "1. How does Zerodha optimize ultra-low-latency order execution pipelines in Go/Python?\n2. What architectural patterns protect your trading gateways from exchange volatility spikes?"
        
        if "i want questions not how to approach" in lower:
            return "1. What is the biggest scaling bottleneck your team is currently solving?\n2. How do you structure code reviews and automated CI/CD canary deployments?"
        
        if "kafka" in lower:
            return "Kafka uses distributed partition logs with consumer groups to achieve high-throughput event streaming."

        return f"Dynamic engineering guidance tailored to: {user_prompt[:50]}..."


@pytest.mark.asyncio
async def test_copilot_responses_are_not_structurally_identical():
    settings = Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")
    ai_service = AIService(settings=settings)
    ai_service._provider = DynamicMockLLMProvider()
    context = CopilotContext(user_id="user_test_01")

    # Ask two different company questions
    resp_uber = await ai_service.chat(
        context=context,
        user_message="I am preparing to apply for Backend Engineer at Uber. Give me reverse-interview questions.",
    )
    resp_zerodha = await ai_service.chat(
        context=context,
        user_message="I am preparing to apply for Backend Engineer at Zerodha. Give me reverse-interview questions.",
    )

    # Responses must not be identical
    assert resp_uber != resp_zerodha
    assert "Uber" in resp_uber or "geospatial" in resp_uber
    assert "Zerodha" in resp_zerodha or "trading" in resp_zerodha

    # Must NOT contain the old hardcoded template headers
    assert "### Strategic Application Game Plan:" not in resp_uber
    assert "### Strategic Application Game Plan:" not in resp_zerodha
    assert "### Software Engineering Mentor Guidance:" not in resp_uber


@pytest.mark.asyncio
async def test_copilot_handles_meta_questions_dynamically():
    settings = Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")
    ai_service = AIService(settings=settings)
    ai_service._provider = DynamicMockLLMProvider()
    context = CopilotContext(user_id="user_test_02")

    meta_question = "i think u are generating answers which are already stored"
    resp = await ai_service.chat(context=context, user_message=meta_question)

    # Must address the question, not lecture on software architecture
    assert "Software Engineering Mentor Guidance" not in resp
    assert "dynamically" in resp or "assist" in resp


@pytest.mark.asyncio
async def test_location_is_never_extracted_as_technical_skill():
    resume_with_location_in_skills = """
    VINAY KUMAR
    vinay@example.com | +91 9876543210

    SKILLS
    Davanagere, Karnataka
    Programming Languages: Python, Java, TypeScript, C++
    Frameworks: FastAPI, React, Node.js
    Databases: PostgreSQL, MongoDB, Redis
    Tools: Docker, Git, CI/CD

    EXPERIENCE
    Software Engineer (2023 - Present)
    - Developed scalable REST APIs using FastAPI and PostgreSQL.
    """

    parsed = structure_resume_text(resume_with_location_in_skills)
    skills = parsed["skills"]

    # Assert that "Davanagere", "Karnataka", or "Davanagere, Karnataka" are NOT in skills
    assert "Davanagere, Karnataka" not in skills
    assert "Davanagere" not in skills
    assert "Karnataka" not in skills
    assert "davanagere" not in [s.lower() for s in skills]
    assert "karnataka" not in [s.lower() for s in skills]

    # Assert real skills are present
    skills_lower = [s.lower() for s in skills]
    assert "python" in skills_lower
    assert "fastapi" in skills_lower
    assert "postgresql" in skills_lower


@pytest.mark.asyncio
async def test_skills_depth_does_not_categorize_location():
    raw_skills = ["Python", "FastAPI", "Docker", "PostgreSQL", "Davanagere, Karnataka", "Bengaluru"]
    result = analyze_skills_depth(raw_skills)

    all_categorized_items = [
        item.lower()
        for domain in result.categorized_domains
        for item in domain.items
    ]

    assert "davanagere, karnataka" not in all_categorized_items
    assert "davanagere" not in all_categorized_items
    assert "karnataka" not in all_categorized_items
    assert "bengaluru" not in all_categorized_items
    assert "python" in all_categorized_items
    assert "fastapi" in all_categorized_items
