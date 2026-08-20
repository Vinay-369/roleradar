"""
Embedding provider abstraction — mirrors the AIService/AIProvider
pattern exactly, for the same reason: matching logic must never depend
on which specific embedding backend is behind it.
"""
from typing import Protocol


class EmbeddingProvider(Protocol):
    def similarity(self, text_a: str, text_b: str) -> float:
        """Returns a 0.0-1.0 similarity score between two short texts
        (e.g. a candidate skill and a JD requirement)."""
        ...
