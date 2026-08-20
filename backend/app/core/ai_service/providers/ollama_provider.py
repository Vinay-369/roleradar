"""
Local runtime provider using Ollama's HTTP API.
This is the default provider for the exhibition/demo build: no external
API key, no network dependency, no per-request cost.
"""
import httpx

from app.core.config import Settings


class OllamaProvider:
    def __init__(self, settings: Settings):
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL
        # Responsive timeout (15s max) so interactive UI never stalls if local model is loading
        self._timeout = min(settings.AI_REQUEST_TIMEOUT_SECONDS, 15)

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
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_ctx": 4096,
            },
        }
        if json_mode:
            payload["format"] = "json"

        timeout_config = httpx.Timeout(self._timeout, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
