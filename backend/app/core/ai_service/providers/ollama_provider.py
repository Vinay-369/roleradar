"""
Local runtime provider using Ollama's HTTP API.
This is the default provider for the exhibition/demo build: no external
API key, no network dependency, no per-request cost.
Includes automatic model discovery and fallback across locally installed models.
"""
import logging
import httpx

from app.core.config import Settings

logger = logging.getLogger("roleradar.ai.ollama")


class OllamaProvider:
    def __init__(self, settings: Settings):
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL
        # Full timeout allowing local models to load into memory safely
        self._timeout = max(settings.AI_REQUEST_TIMEOUT_SECONDS, 120)

    async def _get_available_models(self, client: httpx.AsyncClient) -> list[str]:
        """Queries Ollama /api/tags to discover all locally installed models."""
        try:
            resp = await client.get(f"{self._base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", []) if "name" in m]
                return models
        except Exception as e:
            logger.warning("Failed to query Ollama tags: %s", e)
        return []

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        target_model = model_override or self._model
        timeout_config = httpx.Timeout(self._timeout, connect=5.0)

        async with httpx.AsyncClient(timeout=timeout_config) as client:
            payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_ctx": 2048,
                },
            }
            if json_mode:
                payload["format"] = "json"

            try:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                if resp.status_code == 404:
                    # Model not found — query installed models and retry
                    available = await self._get_available_models(client)
                    if available:
                        fallback_model = available[0]
                        # Prefer phi4-mini or qwen if in list
                        for m in available:
                            if any(k in m.lower() for k in ["phi4", "qwen", "llama"]):
                                fallback_model = m
                                break
                        logger.info("Model '%s' not found; auto-switching to installed model '%s'", target_model, fallback_model)
                        payload["model"] = fallback_model
                        resp = await client.post(f"{self._base_url}/api/chat", json=payload)

                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    # Retry with first available model if not tried yet
                    available = await self._get_available_models(client)
                    if available and available[0] != target_model:
                        payload["model"] = available[0]
                        resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                        resp.raise_for_status()
                        return resp.json()["message"]["content"]
                raise
