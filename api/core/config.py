"""
Configuration management for StudyWise AI API
"""

import os
import secrets
from functools import lru_cache
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator, model_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = ConfigDict(env_file=".env", extra="ignore")

    # Application settings
    app_name: str = "StudyWise AI API"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",  # Frontend Vite dev server
        "http://localhost:8081",  # Frontend Vite dev server (alternate port)
        "http://localhost:8082",  # Frontend Vite dev server (alternate port)
        "http://127.0.0.1:8080",  # Alternative localhost format
        "http://127.0.0.1:8081",  # Alternative localhost format
        "http://127.0.0.1:8082"   # Alternative localhost format
    ]

    # Database settings (will use existing env vars)
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    # Vector database settings (will use existing env vars)
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None

    # AI service settings (will use existing env vars)
    openai_api_key: Optional[str] = None

    # Security settings
    environment: str = "development"  # development, staging, production
    secret_key: Optional[str] = None
    access_token_expire_minutes: int = 30

    @model_validator(mode='after')
    def validate_production_requirements(self):
        """
        Validate production-specific requirements after model creation.
        """
        # Only validate if we're in production and secret_key is auto-generated
        environment = os.getenv('ENVIRONMENT', 'development')
        secret_from_env = os.getenv('SECRET_KEY')
        
        if environment == 'production' and not secret_from_env:
            raise ValueError(
                "SECRET_KEY environment variable is required in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        # Set secret_key if not already set
        if self.secret_key is None:
            if secret_from_env:
                self.secret_key = secret_from_env
            elif environment != 'production':
                # Generate a secure random key for development/staging
                self.secret_key = secrets.token_urlsafe(32)
        
        return self

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # File upload settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = [".pdf", ".txt", ".md", ".docx"]
    upload_path: str = "uploads"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Application settings instance
    """
    return Settings()

def get_settings_no_cache() -> Settings:
    """
    Get application settings without caching (for testing).

    Returns:
        Application settings instance
    """
    return Settings()
