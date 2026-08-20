"""
Enforces Feature 7 from the project spec: AI free-form output is never
trusted directly. Every structured call goes through this helper, which
parses + validates against a Pydantic schema and retries with a
"repair" instruction if the model's output doesn't validate.
"""
import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.ai_service.providers.base import AIProvider

logger = logging.getLogger("roleradar.ai")

T = TypeVar("T", bound=BaseModel)


class AIOutputError(Exception):
    """Raised when the model could not produce valid structured output
    even after the repair-retry loop. Callers must handle this and fail
    safely (never store/display unvalidated AI output)."""


def _extract_json_block(text: str) -> str:
    """Models sometimes wrap JSON in markdown fences despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()


async def generate_structured(
    provider: AIProvider,
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    max_retries: int = 2,
) -> T:
    """
    Calls the provider, parses the response as JSON, validates it against
    `schema`. On failure, re-prompts with the validation error attached
    and asks the model to correct it. Raises AIOutputError if it still
    can't produce valid output after max_retries.
    """
    last_error: Exception | None = None
    current_user_prompt = user_prompt

    for attempt in range(max_retries + 1):
        raw = await provider.complete(system_prompt, current_user_prompt, json_mode=True)
        try:
            parsed = json.loads(_extract_json_block(raw))
            return schema.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning("AI structured output failed validation (attempt %s): %s", attempt, exc)
            current_user_prompt = (
                f"{user_prompt}\n\n"
                f"Your previous response was invalid: {exc}\n"
                f"Respond again with ONLY valid JSON matching the required schema. "
                f"No markdown fences, no commentary."
            )

    raise AIOutputError(
        f"Model failed to produce valid structured output after {max_retries + 1} attempts: {last_error}"
    )
