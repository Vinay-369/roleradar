"""
Every runtime AI provider (Ollama, LM Studio, cloud fallback) implements
this single method. AIService only ever talks to this interface — it
never knows which concrete model is behind it.
"""
from typing import Protocol


class AIProvider(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        """Return the raw text completion from the runtime model."""
        ...
