from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    APP_NAME: str = "AI Tutor"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "dev-secret-change-me-minimum-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str = "postgresql+asyncpg://tutor:tutor@postgres:5432/tutor"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5

    REDIS_URL: str = "redis://redis:6379/0"

    # --- LLM (OpenAI-compatible — works for OpenAI and Ollama) ---
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = "http://host.docker.internal:11434/v1"
    LLM_API_KEY: str = "ollama"
    LLM_MODEL_LARGE: str = "gpt-oss:20b"
    LLM_MODEL_MEDIUM: str = "gpt-oss:20b"
    LLM_MODEL_SMALL: str = "gpt-oss:20b"

    # --- Embeddings (Ollama) ---
    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_BASE_URL: str = "http://host.docker.internal:11434"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIM: int = 768

    MAX_INPUT_LENGTH: int = 2000
    RATE_LIMIT_PER_MINUTE: int = 60

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def force_async_driver(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql+psycopg2://"):
            v = v.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
