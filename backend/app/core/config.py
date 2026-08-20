"""
Central application configuration.
All environment-dependent values live here — never hardcode secrets,
model names, or provider choices elsewhere in the codebase.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "RoleRadar"
    ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h, fine for an FYP demo

    # --- Database ---
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "roleradar"

    # --- File storage ---
    UPLOAD_DIR: str = "./storage/uploads"
    GENERATED_DIR: str = "./storage/generated"
    MAX_UPLOAD_MB: int = 5

    # --- Runtime AI (provider-agnostic) ---
    # AI_PROVIDER selects which implementation AIService delegates to.
    # Business logic NEVER imports a provider directly — only AIService.
    AI_PROVIDER: str = "ollama"  # "ollama" | "lmstudio" | "cloud_fallback"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi4-mini"  # Microsoft Phi-4 Mini (3.8B) for fast, accurate local inference

    LMSTUDIO_BASE_URL: str = "http://localhost:1234/v1"
    LMSTUDIO_MODEL: str = "local-model"

    # Optional cloud fallback — only used if AI_PROVIDER=cloud_fallback
    CLOUD_FALLBACK_PROVIDER: str = "gemini"  # "gemini" | "openai"
    CLOUD_FALLBACK_API_KEY: str = ""
    CLOUD_FALLBACK_MODEL: str = "gemini-2.0-flash"

    AI_REQUEST_TIMEOUT_SECONDS: int = 300
    AI_MAX_RETRIES: int = 2  # for JSON-repair retry loop

    # --- Job sources ---
    # "curated": only the seeded demo dataset (default — works with zero
    #   external config, matches the originally tested/demoed behavior).
    # "hybrid": also fetches real listings from Adzuna and merges them in.
    JOB_SOURCE_MODE: str = "curated"
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    ADZUNA_COUNTRY: str = "in"
    ADZUNA_RESULTS_PER_QUERY: int = 30
    EMBEDDING_PROVIDER: str = "sentence_transformer"  # "sentence_transformer" | "tfidf"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
