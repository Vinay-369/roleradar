"""
Default embedding provider: TF-IDF + cosine similarity via scikit-learn.

This is a deliberate, documented trade-off — it catches lexical overlap
and shared word stems well (e.g. "React.js" vs "React", "developed
APIs" vs "API development"), but it is NOT true semantic
understanding: it won't connect "supervised classification" with
"labeled data modeling" the way a sentence embedding model would.

Chosen as the default because it has no heavy ML runtime dependency
(unlike sentence-transformers, which pulls in PyTorch) and works
identically in any environment, including constrained ones. Swap in
SentenceTransformerProvider (same file) on a machine with more disk/
compute for meaningfully better semantic matching — nothing else in
the matching engine needs to change, since both implement the same
EmbeddingProvider protocol.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TfidfEmbeddingProvider:
    def similarity(self, text_a: str, text_b: str) -> float:
        a, b = text_a.strip().lower(), text_b.strip().lower()
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        try:
            vectorizer = TfidfVectorizer().fit([a, b])
            vectors = vectorizer.transform([a, b])
            score = cosine_similarity(vectors[0], vectors[1])[0][0]
            return float(max(0.0, min(1.0, score)))
        except ValueError:
            # e.g. both strings are pure stopwords with no vocabulary overlap
            return 0.0
