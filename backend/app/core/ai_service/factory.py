from app.core.config import Settings
from app.core.ai_service.providers.base import AIProvider
from app.core.ai_service.providers.ollama_provider import OllamaProvider
from app.core.ai_service.providers.lmstudio_provider import LMStudioProvider
from app.core.ai_service.providers.cloud_fallback_provider import CloudFallbackProvider


from app.core.ai_service.providers.mock_provider import MockAIProvider


def build_provider(settings: Settings) -> AIProvider:
    """
    Single switch point for runtime AI provider selection.
    Nothing else in the codebase should ever import a provider directly —
    this is the only place AI_PROVIDER is read.
    """
    if settings.AI_PROVIDER == "mock":
        return MockAIProvider(settings)
    if settings.AI_PROVIDER == "ollama":
        return OllamaProvider(settings)
    if settings.AI_PROVIDER == "lmstudio":
        return LMStudioProvider(settings)
    if settings.AI_PROVIDER == "cloud_fallback":
        return CloudFallbackProvider(settings)
    raise ValueError(f"Unknown AI_PROVIDER: {settings.AI_PROVIDER}")
