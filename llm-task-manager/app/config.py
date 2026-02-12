"""
Configuration module for LLM Task Manager.

Manages environment variables and application settings using Pydantic Settings.
All secrets should be stored in Google Secret Manager.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    PROJECT_NAME: str = "LLM Task Manager"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["dev", "staging", "production"] = "dev"
    DEBUG: bool = False

    # Database - Cloud SQL connection
    # For dev: postgresql+asyncpg://user:pass@localhost/db (via Cloud SQL Proxy)
    # For prod: postgresql+asyncpg://user:pass@/db?host=/cloudsql/PROJECT_ID:REGION:INSTANCE
    DATABASE_URL: str

    # Database connection pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # JWT Authentication
    JWT_SECRET_KEY: str  # Stored in Secret Manager
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # GCP Settings
    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str = "europe-west1"
    CLOUD_SQL_INSTANCE: str | None = None  # Format: PROJECT_ID:REGION:INSTANCE_NAME

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "dev"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to avoid re-reading environment variables on every call.
    """
    return Settings()


# Export settings instance
settings = get_settings()
