"""
Configuration management for the LoL Stonks RSS application.

This module uses pydantic-settings for type-safe configuration management
with support for environment variables and .env files.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration with environment variable support.

    All settings can be overridden via environment variables or .env file.
    Environment variables should be uppercase (e.g., DATABASE_PATH).
    """

    # Database configuration
    database_path: str = "data/articles.db"

    # API configuration
    lol_news_base_url: str = "https://www.leagueoflegends.com"
    supported_locales: list[str] | str = ["en-us", "it-it"]

    @field_validator("supported_locales", mode="before")
    @classmethod
    def parse_supported_locales(cls, v: list[str] | str) -> list[str]:
        """Parse supported_locales from env string or list."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [loc.strip() for loc in v.split(",") if loc.strip()]
        return ["en-us", "it-it"]

    # Caching configuration (in seconds)
    cache_ttl_seconds: int = 21600  # 6 hours
    build_id_cache_seconds: int = 86400  # 24 hours

    # RSS feed configuration
    rss_feed_title: str = "League of Legends News"
    rss_feed_description: str = "Latest League of Legends news and updates"
    rss_feed_link: str = "https://www.leagueoflegends.com/news"
    rss_max_items: int = 50
    feed_cache_ttl: int = 300  # 5 minutes

    # Multi-language RSS feed titles
    feed_title_en: str = "League of Legends News"
    feed_title_it: str = "Notizie League of Legends"

    # Multi-language RSS feed descriptions
    feed_description_en: str = "Latest League of Legends news and updates"
    feed_description_it: str = "Ultime notizie e aggiornamenti di League of Legends"

    # Server configuration
    base_url: str = "http://localhost:8000"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False  # Set True for development

    # Update scheduling
    update_interval_minutes: int = 30

    # Logging
    log_level: str = "INFO"

    # CORS Configuration
    allowed_origins: list[str] | str = ["http://localhost:8000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: list[str] | str) -> list[str]:
        """Parse allowed_origins from env string or list."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return ["http://localhost:8000"]

    # HTTP Client Configuration
    http_timeout_seconds: int = 30

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to ensure only one Settings instance is created
    during the application lifetime.

    Returns:
        Cached Settings instance
    """
    return Settings()
