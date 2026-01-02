"""
Configuration for Ortho Clinical UI.

GOVERNANCE:
- No LLM configuration
- No API keys for AI services
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Demo settings
    demo_clinician_id: str = "demo_clinician"

    # ortho_intelligence version (must match installed package)
    engine_version: str = "1.0.0"

    model_config = {"env_prefix": "ORTHO_CLINICAL_"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
