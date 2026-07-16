"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "Bloom Scroll"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bloom_scroll"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # API Keys
    OPENALEX_EMAIL: str = ""

    # Service credential for machine callers of write endpoints (e.g. the
    # scheduled ingestion CronJob). Sent via the X-API-Key header. Empty
    # string disables the API-key path entirely.
    INGEST_API_KEY: str = ""

    # Janua Authentication
    JANUA_API_URL: str = "https://auth.madfam.io/api/v1"
    JANUA_JWKS_URI: str = "https://auth.madfam.io/.well-known/jwks.json"
    JANUA_JWT_ISSUER: str = "https://auth.madfam.io"
    JANUA_JWT_AUDIENCE: str = ""
    JANUA_JWT_SECRET: str = "dev-shared-janua-secret-32chars"
    JANUA_JWT_ALGORITHM: str = "RS256"
    JANUA_JWKS_CACHE_SECONDS: int = 300
    AUTH_ENABLED: bool = True

    # Model Configuration
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Selva (MADFAM LLM gateway, OpenAI-compatible /v1 — see ECOSYSTEM.md).
    # Perspective scoring stays dormant until SELVA_BASE_URL is set.
    SELVA_BASE_URL: str = ""
    SELVA_API_KEY: str = ""
    SELVA_SCORING_MODEL: str = "selva-default"

    # Observability (both dormant when unset/zero)
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # App-level request backstop per client IP per minute on public GETs.
    # In-memory per pod (2 replicas => effective limit is ~2x). 0 disables.
    RATE_LIMIT_PER_MINUTE: int = 120

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
