"""
High-performance semantic embedding provider using sentence-transformers.

Uses `all-MiniLM-L6-v2` by default:
  - Lightweight (~80MB footprint, 384-dimensional dense vectors)
  - Optimal speed/quality balance for short-text semantic matching (skills, bullet points, role titles)
  - Sub-millisecond similarity scoring when combined with in-memory embedding caching
  - Singleton-instantiated via factory.py so model weights are loaded once in memory

Implements the EmbeddingProvider protocol (similarity: text_a, text_b -> float [0.0, 1.0]).
"""


from typing import Any


class SentenceTransformerEmbeddingProvider:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer, util
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Run "
                "`pip install sentence-transformers` to use this provider."
            ) from exc
        self._util = util
        self._torch = torch
        try:
            self._model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            self._model = SentenceTransformer(model_name)
        self._cache: dict[str, Any] = {}

    def _get_embedding(self, text: str):
        cleaned = text.strip().lower()
        if not cleaned:
            return None
        if cleaned not in self._cache:
            self._cache[cleaned] = self._model.encode(cleaned, convert_to_tensor=True)
        return self._cache[cleaned]

    def similarity(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0
        emb_a = self._get_embedding(text_a)
        emb_b = self._get_embedding(text_b)
        if emb_a is None or emb_b is None:
            return 0.0
        score = self._util.cos_sim(emb_a, emb_b).item()
        return max(0.0, min(1.0, score))
