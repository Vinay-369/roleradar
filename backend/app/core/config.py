"""
Central application configuration.
All environment-dependent values live here — never hardcode secrets,
model names, or provider choices elsewhere in the codebase.
"""
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # --- Rate Limiting ---
    RATE_LIMITING_ENABLED: bool = True
    AUTH_RATE_LIMIT_MAX_REQUESTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

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
    OLLAMA_MODEL: str = "phi4-mini:latest"  # Fast, accurate local model
    OLLAMA_CHAT_MODEL: str | None = None  # Uses OLLAMA_MODEL or auto-detects available installed model
    COPILOT_MODEL: str | None = None
    LMSTUDIO_MODEL: str = "local-model"

    # Optional cloud fallback — only used if AI_PROVIDER=cloud_fallback
    CLOUD_FALLBACK_PROVIDER: str = "gemini"  # "gemini" | "openai"
    CLOUD_FALLBACK_API_KEY: str = ""
    CLOUD_FALLBACK_MODEL: str = "gemini-2.5-flash"

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

    # --- Direct ATS: Greenhouse Configuration ---
    GREENHOUSE_ENABLED: bool = True
    GREENHOUSE_COMPANIES: str = "postman,inmobi,groww,figma,airbnb,stripe"
    GREENHOUSE_REQUEST_TIMEOUT_SECONDS: int = 15
    MAX_VERIFICATION_AGE_HOURS: int = 48

    # --- Direct ATS: Lever Configuration ---
    LEVER_ENABLED: bool = False
    LEVER_COMPANIES: str = "paytm,meesho,cred,fi"
    LEVER_REQUEST_TIMEOUT_SECONDS: int = 15

    # --- Direct ATS: SmartRecruiters Configuration ---
    SMARTRECRUITERS_ENABLED: bool = False
    SMARTRECRUITERS_COMPANIES: str = "BoschGroup,Sandisk,AveryDennison,BlueberryLabsPrivateLimited,Ubisoft2"
    SMARTRECRUITERS_REQUEST_TIMEOUT_SECONDS: int = 15

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.ENV.lower() == "production":
            insecure_defaults = {
                "change-me-in-env",
                "replace-with-a-long-random-string",
                "secret",
                "test",
                "",
            }
            raw_secret = (self.JWT_SECRET or "").strip()
            if not raw_secret or raw_secret in insecure_defaults or len(raw_secret) < 16:
                raise ValueError(
                    "Production configuration error: A strong, non-default JWT_SECRET "
                    "environment variable must be configured when ENV=production."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
