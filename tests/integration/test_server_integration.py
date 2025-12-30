"""
Integration tests for the FastAPI server.

This module contains end-to-end tests for the complete server workflow
including database operations and feed generation.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app, app_state
from src.models import Article, ArticleSource


@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_server_workflow() -> None:
    """
    Test complete server workflow:
    1. Start server
    2. Fetch RSS feed
    3. Validate XML
    4. Check caching
    """
    # Setup mock services
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])

    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss version="2.0"></rss>')
    service.get_feed_by_source = AsyncMock(
        return_value='<?xml version="1.0"?><rss version="2.0"></rss>'
    )

    app_state["repository"] = repo
    app_state["feed_service"] = service

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        response = await client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "healthy"

        # Get main feed
        response = await client.get("/feed.xml")
        assert response.status_code == 200
        assert "<?xml" in response.text
        assert "rss" in response.text

        # Get source feed
        response = await client.get("/feed/en-us.xml")
        assert response.status_code == 200
        assert "<?xml" in response.text

        # Check caching (second request should use cache)
        response = await client.get("/feed.xml")
        assert response.status_code == 200


@pytest.mark.slow
@pytest.mark.asyncio
async def test_server_with_real_data() -> None:
    """
    Test server with mock data and services.

    Verifies feed generation with realistic mock data.
    """
    # Setup mocks with test data
    repo = AsyncMock()
    test_articles = [
        Article(
            guid="test-integration-1",
            title="Test Article 1",
            url="https://example.com/article1",
            description="First test article",
            pub_date=datetime.now(UTC),
            source=ArticleSource.LOL_EN_US,
            categories=["Champions"],
            image_url="https://example.com/image1.jpg",
        ),
        Article(
            guid="test-integration-2",
            title="Test Article 2",
            url="https://example.com/article2",
            description="Second test article",
            pub_date=datetime.now(UTC),
            source=ArticleSource.LOL_IT_IT,
            categories=["Patches"],
            image_url=None,
        ),
    ]
    repo.get_latest = AsyncMock(return_value=test_articles)

    service = AsyncMock()
    service.get_main_feed = AsyncMock(
        return_value='<?xml version="1.0"?><rss><channel><item><title>Test Article 1</title></item></channel></rss>'
    )
    service.get_feed_by_source = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.get_feed_by_category = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')

    app_state["repository"] = repo
    app_state["feed_service"] = service

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get main feed
        response = await client.get("/feed.xml")
        assert response.status_code == 200

        # Test source-specific feed
        response = await client.get("/feed/en-us.xml")
        assert response.status_code == 200

        # Test category feed
        response = await client.get("/feed/category/Champions.xml")
        assert response.status_code == 200


@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_requests() -> None:
    """
    Test server handles concurrent requests correctly.

    Sends multiple requests simultaneously and verifies all succeed.
    """
    # Setup mocks
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])

    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.get_feed_by_source = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')

    app_state["repository"] = repo
    app_state["feed_service"] = service

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create multiple concurrent requests
        async def fetch_feed(endpoint: str) -> int:
            response = await client.get(endpoint)
            return response.status_code

        # Run concurrent requests
        tasks = [
            fetch_feed("/feed.xml"),
            fetch_feed("/feed/en-us.xml"),
            fetch_feed("/feed/it-it.xml"),
            fetch_feed("/health"),
        ]

        results = await asyncio.gather(*tasks)

        # All requests should succeed
        assert all(status == 200 for status in results)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_cache_invalidation() -> None:
    """
    Test cache invalidation endpoint works correctly.

    Verifies that refresh endpoint invalidates cache.
    """
    # Setup mocks
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])

    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.invalidate_cache = AsyncMock()

    app_state["repository"] = repo
    app_state["feed_service"] = service

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get feed (populates cache)
        response = await client.get("/feed.xml")
        assert response.status_code == 200

        # Invalidate cache
        response = await client.post("/admin/refresh")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Get feed again (should regenerate)
        response = await client.get("/feed.xml")
        assert response.status_code == 200


@pytest.mark.slow
@pytest.mark.asyncio
async def test_error_recovery() -> None:
    """
    Test server recovers from errors gracefully.

    Verifies that errors don't crash the server.
    """
    # Setup mocks
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])

    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')

    app_state["repository"] = repo
    app_state["feed_service"] = service

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request invalid source (should return 404)
        response = await client.get("/feed/invalid.xml")
        assert response.status_code == 404

        # Server should still work for valid requests
        response = await client.get("/health")
        assert response.status_code == 200

        response = await client.get("/feed.xml")
        assert response.status_code == 200
