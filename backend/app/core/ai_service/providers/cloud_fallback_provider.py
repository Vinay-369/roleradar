"""
Optional cloud fallback provider. Not used by default — the exhibition
build runs entirely on a local model. This exists only so that, if a
demo machine can't run a local model fast enough, you can flip
AI_PROVIDER=cloud_fallback in .env without touching any business logic.

Deliberately supports only a minimal, provider-agnostic call shape;
extend the branch for whichever cloud SDK you actually wire up.
"""
import httpx

from app.core.config import Settings


class CloudFallbackProvider:
    def __init__(self, settings: Settings):
        self._settings = settings
        if not settings.CLOUD_FALLBACK_API_KEY:
            raise RuntimeError(
                "CLOUD_FALLBACK_API_KEY is not set. Cloud fallback provider "
                "requires an API key configured in .env."
            )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        provider = self._settings.CLOUD_FALLBACK_PROVIDER.lower()
        if provider == "gemini":
            return await self._complete_gemini(system_prompt, user_prompt, json_mode, model_override)
        elif provider in ("openai", "groq", "openrouter", "together", "deepseek"):
            return await self._complete_openai_compatible(system_prompt, user_prompt, json_mode, model_override)
        raise NotImplementedError(
            f"Cloud fallback provider '{provider}' is not supported. "
            "Supported providers: gemini, openai, groq, openrouter, together, deepseek."
        )

    async def _complete_gemini(self, system_prompt: str, user_prompt: str, json_mode: bool, model_override: str | None = None) -> str:
        raw_model = model_override or self._settings.CLOUD_FALLBACK_MODEL or "gemini-2.5-flash"
        model = raw_model.strip("'\" \t\r\n").removeprefix("models/")
        api_key = (self._settings.CLOUD_FALLBACK_API_KEY or "").strip("'\" \t\r\n")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
        }
        if json_mode:
            payload["generationConfig"] = {"response_mime_type": "application/json"}

        async with httpx.AsyncClient(timeout=self._settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _complete_openai_compatible(self, system_prompt: str, user_prompt: str, json_mode: bool, model_override: str | None = None) -> str:
        provider = self._settings.CLOUD_FALLBACK_PROVIDER.lower()
        base_urls = {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "together": "https://api.together.xyz/v1",
            "deepseek": "https://api.deepseek.com/v1",
        }
        base_url = base_urls.get(provider, "https://api.openai.com/v1")
        model = model_override or self._settings.CLOUD_FALLBACK_MODEL or ("gpt-4o-mini" if provider == "openai" else "llama-3.3-70b-versatile")

        headers = {
            "Authorization": f"Bearer {self._settings.CLOUD_FALLBACK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self._settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"{provider.title()} API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]
