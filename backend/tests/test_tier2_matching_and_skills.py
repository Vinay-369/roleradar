import pytest
from app.core.config import Settings
from app.core.embeddings.factory import build_embedding_provider
from app.core.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.modules.jobs.skill_vocabulary import extract_skills_from_text, KNOWN_SKILLS
from app.modules.jobs.live_provider import AdzunaJobProvider


def test_sentence_transformer_semantic_similarity():
    provider = SentenceTransformerEmbeddingProvider()

    # Direct match
    assert provider.similarity("Python Developer", "Python Developer") > 0.95

    # Non-literal semantic equivalents that pure keyword/TF-IDF would miss
    sim_fastapi = provider.similarity("Python backend developer with FastAPI", "FastAPI Python engineer")
    assert sim_fastapi > 0.75

    sim_martech = provider.similarity("Marketing automation MarTech specialist", "Marketing automation engineer")
    assert sim_martech > 0.65

    sim_k8s = provider.similarity("Kubernetes cluster manager", "K8s container orchestration")
    assert sim_k8s > 0.45

    # Unrelated domains should have low similarity
    sim_unrelated = provider.similarity("Frontend React Developer", "Dentist clinic assistant")
    assert sim_unrelated < 0.35


def test_embedding_factory_returns_sentence_transformer_by_default():
    settings = Settings(EMBEDDING_PROVIDER="sentence_transformer")
    provider = build_embedding_provider(settings)
    assert isinstance(provider, SentenceTransformerEmbeddingProvider)


def test_spacy_skill_extraction_canonical_and_niche():
    sample_jd = (
        "We are looking for a Senior Engineer experienced in LangChain, RAG architectures, "
        "and Vector Databases like Pinecone. Strong background in PyTorch, Kubernetes, and FastAPI required. "
        "Must be proficient in Terraform, Prometheus, and OAuth 2.0."
    )

    extracted = extract_skills_from_text(sample_jd)

    assert "LangChain" in extracted
    assert "FastAPI" in extracted
    assert "Kubernetes" in extracted
    assert "PyTorch" in extracted
    assert "Pinecone" in extracted
    assert "Terraform" in extracted
    assert "Prometheus" in extracted
    assert "OAuth 2.0" in extracted


def test_spacy_skill_extraction_alias_resolution():
    text = "Hands-on experience with k8s, golang, ts, postgres, and martech integrations."
    extracted = extract_skills_from_text(text)

    assert "Kubernetes" in extracted
    assert "Go" in extracted
    assert "TypeScript" in extracted
    assert "PostgreSQL" in extracted
    assert "Marketing Automation" in extracted


def test_spacy_skill_extraction_context_patterns():
    text = "Candidate must have strong understanding of Distributed Caching and hands-on with Redis."
    extracted = extract_skills_from_text(text)

    assert "Redis" in extracted


@pytest.mark.asyncio
async def test_adzuna_search_query_tuning_with_role_and_skills(monkeypatch):
    captured_params = {}

    class CapturingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            captured_params.update(params or {})

            class FakeResponse:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"results": []}

            return FakeResponse()

    monkeypatch.setattr("app.modules.jobs.live_provider.httpx.AsyncClient", lambda **kw: CapturingAsyncClient())

    settings = Settings(JWT_SECRET="test", ADZUNA_APP_ID="test-id", ADZUNA_APP_KEY="test-key", JOB_SOURCE_MODE="hybrid")
    provider = AdzunaJobProvider(settings)

    await provider.search({
        "role": "Backend Developer",
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        "location": "Bangalore",
    })

    assert captured_params["what"] == "Backend Developer"
    assert "Python" in captured_params["what_or"]
    assert "FastAPI" in captured_params["what_or"]
    assert captured_params["where"] == "Bangalore"
