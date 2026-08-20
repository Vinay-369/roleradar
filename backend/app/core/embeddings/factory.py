import logging

from app.core.config import Settings
from app.core.embeddings.tfidf_provider import TfidfEmbeddingProvider

logger = logging.getLogger("roleradar.embeddings")
_cached_sentence_provider = None


def build_embedding_provider(settings: Settings):
    global _cached_sentence_provider
    provider = getattr(settings, "EMBEDDING_PROVIDER", "sentence_transformer")
    if provider == "sentence_transformer":
        if _cached_sentence_provider is not None:
            return _cached_sentence_provider
        try:
            from app.core.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
            _cached_sentence_provider = SentenceTransformerEmbeddingProvider(settings.EMBEDDING_MODEL)
            return _cached_sentence_provider
        except Exception as e:
            logger.warning("Could not initialize sentence-transformers (%s); falling back to TF-IDF", e)
            return TfidfEmbeddingProvider()
    return TfidfEmbeddingProvider()
