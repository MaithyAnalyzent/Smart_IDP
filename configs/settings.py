from __future__ import annotations
import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All runtime configuration is loaded from environment variables.

    Copy .env.example to .env and fill in values before running.
    No secrets should ever appear in this file.
    """

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Doc Intelligence Platform"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.  Empty = deny all cross-origin.
    ALLOWED_ORIGINS: str = ""

    # ── Admin ─────────────────────────────────────────────────────────────────
    MASTER_API_KEY: str

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Object Storage (S3-compatible) ────────────────────────────────────────
    STORAGE_ENDPOINT: str = ""        # Leave blank for real AWS S3
    STORAGE_ACCESS_KEY: str
    STORAGE_SECRET_KEY: str
    STORAGE_BUCKET: str
    STORAGE_REGION: str = "us-east-1"
    STORAGE_USE_SSL: bool = True

    # ── LLM Provider ─────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"      # openai | anthropic
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: str = ""

    # ── Pipeline ─────────────────────────────────────────────────────────────
    PIPELINE_CONFIG_PATH: str = "configs/pipeline.yaml"
    MAX_FILE_SIZE_MB: int = 50
    PROCESSING_TIMEOUT_SECONDS: int = 300

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"          # json | console

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance. Call once per process."""
    return Settings()
