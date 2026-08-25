"""
Tests verifying Career Copilot (Feature 20 / v4) prompt calibration and formatting guidelines.
"""
from app.core.ai_service.prompts.chatbot import (
    CHAT_PROMPT_VERSION,
    COPILOT_SYSTEM_PROMPT,
    build_copilot_user_prompt,
)


def test_copilot_prompt_version():
    assert CHAT_PROMPT_VERSION == "v4"


def test_copilot_formatting_guidelines_contain_all_conditional_rules():
    """Verifies that the prompt contains all explicit rules for prose, headers, bullets, and bolding."""
    prompt = COPILOT_SYSTEM_PROMPT

    # 1. Prose rule for simple/quick questions
    assert "Match structure to the question's actual complexity" in prompt
    assert "2-4 sentences of plain prose" in prompt

    # 2. Bullet point conditional rule
    assert "Use bullet points ONLY for genuinely parallel/list-like content" in prompt
    assert "Never bullet a narrative explanation" in prompt

    # 3. Section headers conditional rule (3+ distinct sections)
    assert "Use section headers (###) ONLY when the answer has 3 or more genuinely distinct sections" in prompt

    # 4. Bold term calibration
    assert "Use bold for the 1-3 most important terms" in prompt
    assert "Over-bolding defeats its own purpose" in prompt

    # 5. Code block usage rule
    assert "Use code blocks with a language tag ONLY for actual code, commands, or config" in prompt

    # 6. Paragraph separation and no dense mergers
    assert "default to short paragraphs (2-4 sentences each)" in prompt
    assert "NEVER merge multiple distinct points into a single dense paragraph" in prompt

    # 7. No preamble / No unearned conclusions
    assert "No preamble" in prompt
    assert "No unearned closing summary" in prompt


def test_copilot_prompt_contains_calibrated_few_shot_examples():
    """Verifies few-shot examples demonstrating BAD vs GOOD formatting matching question complexity."""
    prompt = COPILOT_SYSTEM_PROMPT

    # Example 1: Quick factual comparison (SQL vs NoSQL) -> Plain prose, no unnecessary headers
    assert "What's the difference between SQL and NoSQL?" in prompt
    assert "BAD (over-structured for a simple question):" in prompt
    assert "GOOD (matches complexity" in prompt

    # Example 2: Complex System Design -> Warrants headers (###)
    assert "Design a URL shortener system" in prompt
    assert "### Requirements" in prompt
    assert "### High-Level Architecture" in prompt

    # Example 3: Parallel Steps -> Warrants bullets
    assert "How do I answer 'tell me about yourself'?" in prompt
    assert "**Present**:" in prompt
    assert "**Past**:" in prompt
    assert "**Future**:" in prompt


def test_build_copilot_user_prompt_includes_formatting_instructions():
    """Verifies user prompt instructs mentor to match formatting to complexity with zero preamble."""
    user_prompt = build_copilot_user_prompt(
        context_block="SKILLS: Python, FastAPI",
        user_message="What is the time complexity of quicksort?",
    )
    assert "USER'S QUESTION:" in user_prompt
    assert "What is the time complexity of quicksort?" in user_prompt
    assert "Match formatting structure to the question's complexity per the Formatting Guidelines." in user_prompt
    assert "Zero conversational preamble." in user_prompt
