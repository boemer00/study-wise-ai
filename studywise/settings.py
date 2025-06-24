from __future__ import annotations

"""Centralised configuration for the StudyWise AI application.

This module provides a single source of truth for environment-driven
settings shared by the CLI code under ``src/`` and the FastAPI backend
under ``api/``.  It replaces the duplicated configuration logic
currently spread across ``src/config.py`` and ``api/core/config.py``.

Only type declarations and public interface are defined at this stage;
implementation will be filled in during the *Implement* phase.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator
from dotenv import load_dotenv
import secrets

__all__ = [
    "Settings",
    "get_settings",
    "get_settings_no_cache",
]

# Load environment variables from .env (do this once at module import time)
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ------------------------------------------------------------------
    # Core application metadata
    # ------------------------------------------------------------------
    app_name: str = "StudyWise AI API"
    environment: str = "development"  # development, staging, production
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8082",
        "https://studywise-frontend-459478398975.us-central1.run.app",
    ]

    # ------------------------------------------------------------------
    # Database – Supabase
    # ------------------------------------------------------------------
    supabase_url: Optional[str] = None
    # Complete Supabase credentials set
    supabase_key: Optional[str] = None  # Generic service/anon key alias used in legacy code
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # ------------------------------------------------------------------
    # Vector database – Weaviate
    # ------------------------------------------------------------------
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None

    # ------------------------------------------------------------------
    # AI services
    # ------------------------------------------------------------------
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = "gpt-4o-mini"

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    secret_key: Optional[str] = None
    access_token_expire_minutes: int = 30

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # ------------------------------------------------------------------
    # File uploads
    # ------------------------------------------------------------------
    upload_path: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    allowed_file_types: List[str] = [".pdf", ".txt", ".md", ".docx"]

    # ------------------------------------------------------------------
    # Pydantic settings
    # ------------------------------------------------------------------
    model_config = ConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_requirements(self):  # noqa: D401, D403
        """Validate production-specific requirements."""
        # Ensure SECRET_KEY is present for production deployments.
        if self.environment == "production" and not (self.secret_key or secrets.token_urlsafe):
            raise ValueError(
                "SECRET_KEY environment variable is required in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # For non-production environments generate an ephemeral key if missing.
        if self.secret_key is None:
            self.secret_key = secrets.token_urlsafe(32)

        return self

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    @property
    def cors_origins(self) -> List[str]:  # noqa: D401
        """Return allowed origins, wildcard when in debug for convenience."""
        if self.debug:
            return self.allowed_origins or ["*"]
        return self.allowed_origins


@lru_cache()
def get_settings() -> Settings:
    """Return a *cached* Settings instance loaded from env vars."""
    return Settings()


def get_settings_no_cache() -> Settings:
    """Return a non-cached Settings instance (useful for tests)."""
    return Settings()
