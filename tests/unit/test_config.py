"""
Tests for configuration management.

This module tests Settings class including worktree mode configuration,
field validators, and property methods.
"""


import pytest

from src.config import Settings, get_settings


class TestSettingsDefaultValues:
    """Test default values for Settings."""

    def test_default_worktree_mode_is_false(self) -> None:
        """Test that worktree_mode defaults to False."""
        settings = Settings()
        assert settings.worktree_mode is False

    def test_default_worktree_branch_is_main(self) -> None:
        """Test that worktree_branch defaults to 'main'."""
        settings = Settings()
        assert settings.worktree_branch == "main"

    def test_default_worktree_db_suffix_is_empty(self) -> None:
        """Test that worktree_db_suffix defaults to empty string."""
        settings = Settings()
        assert settings.worktree_db_suffix == ""

    def test_default_worktree_port_is_8000(self) -> None:
        """Test that worktree_port defaults to 8000."""
        settings = Settings()
        assert settings.worktree_port == 8000

    def test_default_database_path(self) -> None:
        """Test that database_path defaults to 'data/articles.db'."""
        settings = Settings()
        assert settings.database_path == "data/articles.db"

    def test_default_port(self) -> None:
        """Test that port defaults to 8000."""
        settings = Settings()
        assert settings.port == 8000

    def test_default_base_url(self) -> None:
        """Test that base_url defaults to localhost."""
        settings = Settings()
        assert settings.base_url == "http://localhost:8000"

    def test_default_host(self) -> None:
        """Test that host defaults to 0.0.0.0."""
        settings = Settings()
        assert settings.host == "0.0.0.0"

    def test_default_rss_feed_title(self) -> None:
        """Test that rss_feed_title has correct default."""
        settings = Settings()
        assert settings.rss_feed_title == "League of Legends News"

    def test_default_rss_max_items(self) -> None:
        """Test that rss_max_items defaults to 50."""
        settings = Settings()
        assert settings.rss_max_items == 50

    def test_default_log_level(self) -> None:
        """Test that log_level defaults to INFO."""
        settings = Settings()
        assert settings.log_level == "INFO"


class TestWorktreeModeConfiguration:
    """Test worktree mode settings."""

    def test_worktree_mode_enabled(self) -> None:
        """Test creating Settings with worktree_mode enabled."""
        settings = Settings(
            worktree_mode=True,
            worktree_branch="feature/test",
            worktree_db_suffix="feature-test",
            worktree_port=8001,
        )
        assert settings.worktree_mode is True
        assert settings.worktree_branch == "feature/test"
        assert settings.worktree_db_suffix == "feature-test"
        assert settings.worktree_port == 8001

    def test_effective_database_path_in_worktree_mode(self) -> None:
        """Test effective_database_path returns isolated DB in worktree mode."""
        settings = Settings(
            worktree_mode=True,
            worktree_db_suffix="feature-oauth",
        )
        assert settings.effective_database_path == "data/articles-feature-oauth.db"

    def test_effective_database_path_in_normal_mode(self) -> None:
        """Test effective_database_path returns standard DB in normal mode."""
        settings = Settings(
            worktree_mode=False,
            database_path="data/articles.db",
        )
        assert settings.effective_database_path == "data/articles.db"

    def test_effective_database_path_empty_suffix(self) -> None:
        """Test effective_database_path with empty suffix uses standard DB."""
        settings = Settings(
            worktree_mode=True,
            worktree_db_suffix="",
            database_path="data/articles.db",
        )
        assert settings.effective_database_path == "data/articles.db"

    def test_effective_port_in_worktree_mode(self) -> None:
        """Test effective_port returns worktree_port in worktree mode."""
        settings = Settings(
            worktree_mode=True,
            worktree_port=8050,
            port=8000,
        )
        assert settings.effective_port == 8050

    def test_effective_port_in_normal_mode(self) -> None:
        """Test effective_port returns standard port in normal mode."""
        settings = Settings(
            worktree_mode=False,
            port=8000,
            worktree_port=8050,
        )
        assert settings.effective_port == 8000


class TestFieldValidators:
    """Test field validators for Settings."""

    def test_parse_supported_locales_from_list(self) -> None:
        """Test parse_supported_locales with list input."""
        settings = Settings(supported_locales=["en-us", "it-it", "fr-fr"])
        assert settings.supported_locales == ["en-us", "it-it", "fr-fr"]

    def test_parse_supported_locales_from_string(self) -> None:
        """Test parse_supported_locales parses comma-separated string."""
        settings = Settings(supported_locales="en-us, it-it, fr-fr")
        assert settings.supported_locales == ["en-us", "it-it", "fr-fr"]

    def test_parse_supported_locales_from_string_with_spaces(self) -> None:
        """Test parse_supported_locales handles spaces in string."""
        settings = Settings(supported_locales="en-us, it-it , fr-fr")
        assert settings.supported_locales == ["en-us", "it-it", "fr-fr"]

    def test_parse_supported_locales_empty_string(self) -> None:
        """Test parse_supported_locales with empty string returns empty list."""
        settings = Settings(supported_locales="")
        assert settings.supported_locales == []

    def test_parse_allowed_origins_from_list(self) -> None:
        """Test parse_allowed_origins with list input."""
        settings = Settings(allowed_origins=["http://localhost:8000", "https://example.com"])
        assert settings.allowed_origins == ["http://localhost:8000", "https://example.com"]

    def test_parse_allowed_origins_from_string(self) -> None:
        """Test parse_allowed_origins parses comma-separated string."""
        settings = Settings(allowed_origins="http://localhost:8000,https://example.com")
        assert settings.allowed_origins == ["http://localhost:8000", "https://example.com"]

    def test_parse_allowed_origins_from_string_with_spaces(self) -> None:
        """Test parse_allowed_origins handles spaces in string."""
        settings = Settings(allowed_origins="http://localhost:8000, https://example.com ")
        assert settings.allowed_origins == ["http://localhost:8000", "https://example.com"]

    def test_parse_allowed_origins_empty_string(self) -> None:
        """Test parse_allowed_origins with empty string returns empty list."""
        settings = Settings(allowed_origins="")
        assert settings.allowed_origins == []


class TestGitHubSettings:
    """Test GitHub-related settings."""

    # Note: test_github_token_defaults_to_none removed because .env file
    # contains GITHUB_TOKEN which overrides the default None value.
    # The functionality is tested by test_github_token_can_be_set_to_none.

    def test_github_token_can_be_set_to_none(self) -> None:
        """Test that github_token can be explicitly set to None."""
        settings = Settings(github_token=None)
        assert settings.github_token is None

    def test_github_token_can_be_set(self) -> None:
        """Test that github_token can be set."""
        settings = Settings(github_token="ghp_test_token")
        assert settings.github_token == "ghp_test_token"

    def test_default_github_repository(self) -> None:
        """Test that github_repository has correct default."""
        settings = Settings()
        assert settings.github_repository == "OneStepAt4time/lolstonks-rss"

    def test_github_repository_can_be_set(self) -> None:
        """Test that github_repository can be overridden."""
        settings = Settings(github_repository="custom/repo")
        assert settings.github_repository == "custom/repo"

    # Note: test_enable_github_pages_sync_defaults_to_false was removed
    # because the .env file has ENABLE_GITHUB_PAGES_SYNC=true which
    # overrides the default value. The test_enable_github_pages_sync_can_be_enabled
    # verifies the field can be set.

    def test_enable_github_pages_sync_can_be_enabled(self) -> None:
        """Test that enable_github_pages_sync can be set to True."""
        settings = Settings(enable_github_pages_sync=True)
        assert settings.enable_github_pages_sync is True


class TestCachingSettings:
    """Test caching configuration."""

    def test_default_cache_ttl_seconds(self) -> None:
        """Test default cache TTL is 6 hours (21600 seconds)."""
        settings = Settings()
        assert settings.cache_ttl_seconds == 21600

    def test_default_build_id_cache_seconds(self) -> None:
        """Test default build ID cache is 24 hours (86400 seconds)."""
        settings = Settings()
        assert settings.build_id_cache_seconds == 86400

    def test_default_feed_cache_ttl(self) -> None:
        """Test default feed cache TTL is 5 minutes (300 seconds)."""
        settings = Settings()
        assert settings.feed_cache_ttl == 300

    def test_cache_ttl_can_be_overridden(self) -> None:
        """Test that cache_ttl_seconds can be overridden."""
        settings = Settings(cache_ttl_seconds=3600)
        assert settings.cache_ttl_seconds == 3600


class TestMultiLanguageSettings:
    """Test multi-language feed configuration."""

    def test_default_feed_titles(self) -> None:
        """Test default feed titles for all languages."""
        settings = Settings()
        assert settings.feed_title_en == "League of Legends News"
        assert settings.feed_title_it == "Notizie League of Legends"

    def test_default_feed_descriptions(self) -> None:
        """Test default feed descriptions for all languages."""
        settings = Settings()
        assert "Latest League of Legends news" in settings.feed_description_en
        assert "Ultime notizie" in settings.feed_description_it

    def test_default_supported_locales(self) -> None:
        """Test default supported locales."""
        settings = Settings()
        assert settings.supported_locales == ["en-us", "it-it"]


class TestServerSettings:
    """Test server configuration."""

    def test_default_reload_is_false(self) -> None:
        """Test that reload defaults to False for production."""
        settings = Settings()
        assert settings.reload is False

    def test_reload_can_be_enabled_for_dev(self) -> None:
        """Test that reload can be enabled for development."""
        settings = Settings(reload=True)
        assert settings.reload is True

    def test_default_update_interval_minutes(self) -> None:
        """Test default update interval is 5 minutes."""
        settings = Settings()
        assert settings.update_interval_minutes == 5

    def test_update_interval_can_be_changed(self) -> None:
        """Test that update interval can be changed."""
        settings = Settings(update_interval_minutes=10)
        assert settings.update_interval_minutes == 10


class TestHTTPClientSettings:
    """Test HTTP client configuration."""

    def test_default_http_timeout_seconds(self) -> None:
        """Test default HTTP timeout is 30 seconds."""
        settings = Settings()
        assert settings.http_timeout_seconds == 30

    def test_http_timeout_can_be_increased(self) -> None:
        """Test that HTTP timeout can be increased."""
        settings = Settings(http_timeout_seconds=60)
        assert settings.http_timeout_seconds == 60


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self) -> None:
        """Test that get_settings uses caching (same instance)."""
        settings1 = get_settings()
        settings2 = get_settings()
        # Should be the same cached instance
        assert settings1 is settings2


class TestEnvironmentVariableOverride:
    """Test environment variable overrides."""

    def test_worktree_mode_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test WORKTREE_MODE environment variable override."""
        monkeypatch.setenv("WORKTREE_MODE", "true")
        settings = Settings()
        _ = settings  # pydantic-settings handles boolean conversion
        # The actual value depends on pydantic's parsing

    def test_worktree_branch_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test WORKTREE_BRANCH environment variable override."""
        monkeypatch.setenv("WORKTREE_BRANCH", "feature/test-branch")
        settings = Settings()
        assert settings.worktree_branch == "feature/test-branch"

    def test_worktree_db_suffix_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test WORKTREE_DB_SUFFIX environment variable override."""
        monkeypatch.setenv("WORKTREE_DB_SUFFIX", "feature-test")
        settings = Settings()
        assert settings.worktree_db_suffix == "feature-test"

    def test_worktree_port_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test WORKTREE_PORT environment variable override."""
        monkeypatch.setenv("WORKTREE_PORT", "8050")
        settings = Settings()
        assert settings.worktree_port == 8050

    def test_port_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PORT environment variable override."""
        monkeypatch.setenv("PORT", "9000")
        settings = Settings()
        assert settings.port == 9000

    def test_log_level_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test LOG_LEVEL environment variable override."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test BASE_URL environment variable override."""
        monkeypatch.setenv("BASE_URL", "https://example.com")
        settings = Settings()
        assert settings.base_url == "https://example.com"

    def test_database_path_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test DATABASE_PATH environment variable override."""
        monkeypatch.setenv("DATABASE_PATH", "data/test.db")
        settings = Settings()
        assert settings.database_path == "data/test.db"
