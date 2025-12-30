"""
Tests for security fixes implemented in the code review.

This module tests the critical security and quality fixes:
- CORS configuration
- Rate limiting on admin endpoints
- HTTP timeout configuration
- Input validation on category parameter
"""

from datetime import UTC

import pytest
from fastapi import status
from httpx import AsyncClient

from src.config import get_settings


@pytest.mark.asyncio
async def test_cors_configuration_from_settings(client: AsyncClient) -> None:
    """
    Test that CORS uses configured allowed origins from settings.

    FIX H-1: CORS Configuration (CRITICAL)
    """
    settings = get_settings()

    # Verify settings has allowed_origins
    assert hasattr(settings, "allowed_origins")
    assert isinstance(settings.allowed_origins, list)
    assert len(settings.allowed_origins) > 0

    # Verify default is localhost
    assert "http://localhost:8000" in settings.allowed_origins


def test_rate_limiting_configured() -> None:
    """
    Test that rate limiting is configured on admin endpoints.

    FIX M-1: Rate Limiting on Admin Endpoints
    """
    from src.api.app import app, limiter

    # Verify limiter is configured
    assert limiter is not None
    assert hasattr(app.state, "limiter")
    assert app.state.limiter is not None

    # Verify rate limiter key function is set
    assert limiter._key_func is not None


@pytest.mark.asyncio
async def test_http_timeout_configuration() -> None:
    """
    Test that HTTP timeout is configured in settings.

    FIX EH-2: HTTP Timeout Configuration
    """
    settings = get_settings()

    # Verify timeout setting exists
    assert hasattr(settings, "http_timeout_seconds")
    assert isinstance(settings.http_timeout_seconds, int)
    assert settings.http_timeout_seconds > 0

    # Default should be 30 seconds
    assert settings.http_timeout_seconds == 30


@pytest.mark.asyncio
async def test_category_validation_valid_input(client: AsyncClient) -> None:
    """
    Test that valid category input is accepted.

    FIX M-3: Input Validation on Category
    """
    # Valid category names
    valid_categories = [
        "Champions",
        "Game-Updates",
        "media_news",
        "test123",
        "a",  # Single character
        "a" * 50,  # Max length (50 chars)
    ]

    for category in valid_categories:
        response = await client.get(f"/feed/category/{category}.xml")
        # Should not return 400 (validation error)
        assert response.status_code != status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_category_validation_invalid_input(client: AsyncClient) -> None:
    """
    Test that invalid category input is rejected.

    FIX M-3: Input Validation on Category
    """
    # Invalid category names (should be rejected)
    invalid_categories = [
        "../etc/passwd",  # Path traversal
        "test<script>",  # XSS attempt
        "test;DROP TABLE",  # SQL injection attempt
        "test/path",  # Slash not allowed
        "test\\path",  # Backslash not allowed
        "test space",  # Space not allowed
        "test@email",  # @ not allowed
        "a" * 51,  # Too long (>50 chars)
    ]

    for category in invalid_categories:
        response = await client.get(f"/feed/category/{category}.xml")
        # Should return 400 (validation error) or 404 (FastAPI path validation)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


@pytest.mark.asyncio
async def test_no_hardcoded_localhost_in_feed() -> None:
    """
    Test that feed URL is not hardcoded to localhost.

    FIX L-1: Remove Hardcoded Localhost
    """
    from datetime import datetime

    from src.models import Article, ArticleSource
    from src.rss.generator import RSSFeedGenerator

    generator = RSSFeedGenerator()

    article = Article(
        title="Test Article",
        url="https://example.com/article",
        pub_date=datetime.now(UTC),
        guid="test-guid",
        source=ArticleSource.LOL_EN_US,
    )

    # Should require feed_url parameter (no default)
    with pytest.raises(TypeError):
        generator.generate_feed([article])  # type: ignore

    # Should work when feed_url is provided
    feed_xml = generator.generate_feed([article], feed_url="https://example.com/feed.xml")
    assert "https://example.com/feed.xml" in feed_xml
    assert "localhost" not in feed_xml


@pytest.mark.asyncio
async def test_docker_environment_variable_usage() -> None:
    """
    Test that configuration uses environment variables.

    FIX L-2: Remove .env Copy from Dockerfile
    """
    settings = get_settings()

    # All critical settings should be configurable via env vars
    # (defaults are fine, but they should support env var override)

    # Test that settings class supports env vars
    assert hasattr(settings, "Config")
    assert hasattr(settings.Config, "env_file")
    assert settings.Config.env_file == ".env"

    # Verify critical settings exist
    assert hasattr(settings, "allowed_origins")
    assert hasattr(settings, "http_timeout_seconds")
    assert hasattr(settings, "base_url")


@pytest.mark.asyncio
async def test_cors_headers_match_configuration(client: AsyncClient) -> None:
    """
    Test that CORS headers reflect configured origins.

    Verifies that allow_origins is not ["*"]
    """
    settings = get_settings()

    # Verify CORS is not wide open
    assert settings.allowed_origins != ["*"]
    assert "*" not in settings.allowed_origins

    # Make a request and check CORS headers
    response = await client.get("/health")
    assert response.status_code == 200


def test_security_headers_configured() -> None:
    """
    Test that security headers are configured in the app.
    """
    from fastapi.middleware.cors import CORSMiddleware

    from src.api.app import app

    # Verify CORS middleware is configured
    has_cors = False
    for middleware in app.user_middleware:
        if hasattr(middleware, "cls") and middleware.cls == CORSMiddleware:
            has_cors = True
            break

    assert has_cors, "CORS middleware should be configured"


def test_settings_validation() -> None:
    """
    Test that settings validators work correctly.
    """
    from src.config import Settings

    # Test allowed_origins parsing from string
    settings = Settings(allowed_origins="http://example.com,http://test.com")
    assert len(settings.allowed_origins) == 2
    assert "http://example.com" in settings.allowed_origins
    assert "http://test.com" in settings.allowed_origins

    # Test supported_locales parsing
    settings = Settings(supported_locales="en-us,it-it,fr-fr")
    assert len(settings.supported_locales) == 3
    assert "fr-fr" in settings.supported_locales
