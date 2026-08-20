"""
Local runtime provider using LM Studio's OpenAI-compatible local server.
Alternative to Ollama — pick whichever runtime performs better after
testing (see AIService docstring / project README for the test matrix).
"""
import httpx

from app.core.config import Settings


class LMStudioProvider:
    def __init__(self, settings: Settings):
        self._base_url = settings.LMSTUDIO_BASE_URL.rstrip("/")
        self._model = settings.LMSTUDIO_MODEL
        self._timeout = settings.AI_REQUEST_TIMEOUT_SECONDS

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
