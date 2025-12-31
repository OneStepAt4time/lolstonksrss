"""
Configuration management for the LoL Stonks RSS application.

This module uses pydantic-settings for type-safe configuration management
with support for environment variables and .env files.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration with environment variable support.

    All settings can be overridden via environment variables or .env file.
    Environment variables should be uppercase (e.g., DATABASE_PATH).
    """

    # Worktree mode for parallel development
    worktree_mode: bool = Field(
        default=False,
        description="Enable worktree mode for parallel agent development",
    )
    worktree_branch: str = Field(
        default="main",
        description="Current branch name in worktree mode",
    )
    worktree_db_suffix: str = Field(
        default="",
        description="Suffix for isolated database in worktree mode",
    )
    worktree_port: int = Field(
        default=8000,
        description="Port allocated for this worktree",
    )

    # Database configuration
    database_path: str = "data/articles.db"

    @property
    def effective_database_path(self) -> str:
        """
        Get the actual database path considering worktree mode.

        In worktree mode, uses an isolated database per branch.
        Otherwise uses the standard database path.
        """
        if self.worktree_mode and self.worktree_db_suffix:
            return f"data/articles-{self.worktree_db_suffix}.db"
        return self.database_path

    @property
    def effective_port(self) -> int:
        """
        Get the actual port considering worktree mode.

        In worktree mode, uses the allocated port.
        Otherwise uses the standard port.
        """
        return self.worktree_port if self.worktree_mode else self.port

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
    # Bind to all interfaces - acceptable for containerized deployment behind reverse proxy
    host: str = "0.0.0.0"  # nosec: B104 - intentional for Docker deployment
    port: int = 8000
    reload: bool = False  # Set True for development

    # Update scheduling
    update_interval_minutes: int = 5

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

    # GitHub Pages Integration (Optional)
    github_token: str | None = Field(
        default=None, description="GitHub Personal Access Token for triggering workflows"
    )
    github_repository: str = Field(
        default="OneStepAt4time/lolstonks-rss",
        description="GitHub repository in format 'owner/repo'",
    )
    enable_github_pages_sync: bool = Field(
        default=False,
        description="Enable automatic GitHub Pages update when new articles found",
    )

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
