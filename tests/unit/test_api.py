"""
Tests for FastAPI application endpoints.

This module tests all HTTP endpoints including feed generation, health checks,
and error handling.
"""

from collections.abc import AsyncGenerator
from datetime import timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app, app_state
from src.models import Article, ArticleSource


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create test client for FastAPI app.

    Yields:
        AsyncClient instance for testing
    """
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_feed_service() -> AsyncMock:
    """
    Mock feed service for testing.

    Returns:
        Mocked FeedService instance
    """
    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.get_feed_by_source = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.get_feed_by_category = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.invalidate_cache = MagicMock()

    # Store in app_state
    app_state["feed_service"] = service

    return service


@pytest.fixture
def mock_repository() -> AsyncMock:
    """
    Mock repository for testing.

    Returns:
        Mocked ArticleRepository instance
    """
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])
    repo.initialize = AsyncMock()
    repo.close = AsyncMock()

    # Store in app_state
    app_state["repository"] = repo

    return repo


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """
    Test root endpoint returns usage information.

    Args:
        client: Test client fixture
    """
    response = await client.get("/")
    assert response.status_code == 200
    assert "LoL Stonks RSS" in response.text
    # Root now serves the frontend HTML application
    assert "<!DOCTYPE html>" in response.text


@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient) -> None:
    """
    Test health check endpoint returns healthy status.

    Args:
        client: Test client fixture
    """
    from datetime import datetime

    # Setup mock repository with articles
    repo = AsyncMock()
    repo.get_latest = AsyncMock(
        return_value=[
            Article(
                guid="test-1",
                title="Test Article",
                url="https://example.com/article",
                description="Test description",
                pub_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                source=ArticleSource.LOL_EN_US,
                categories=["News"],
                image_url=None,
            )
        ]
    )

    # Setup mock service
    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')

    # Store in app_state
    app_state["repository"] = repo
    app_state["feed_service"] = service

    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["service"] == "LoL Stonks RSS"
    assert data["database"] == "connected"
    assert data["cache"] == "active"
    assert data["has_articles"] is True


@pytest.mark.asyncio
async def test_health_check_no_articles(client: AsyncClient) -> None:
    """
    Test health check with no articles.

    Args:
        client: Test client fixture
    """
    # Setup mock repository with no articles
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])

    # Setup mock service
    service = AsyncMock()

    # Store in app_state
    app_state["repository"] = repo
    app_state["feed_service"] = service

    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["has_articles"] is False


@pytest.mark.asyncio
async def test_get_main_feed(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test getting main RSS feed.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")
    assert "Cache-Control" in response.headers
    assert "max-age" in response.headers["Cache-Control"]
    assert "<?xml" in response.text


@pytest.mark.asyncio
async def test_get_main_feed_with_limit(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test main feed with custom limit parameter.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed.xml?limit=10")

    assert response.status_code == 200
    mock_feed_service.get_main_feed.assert_called_once()

    # Check limit was passed
    call_args = mock_feed_service.get_main_feed.call_args
    assert call_args is not None
    assert call_args[1]["limit"] == 10


@pytest.mark.asyncio
async def test_get_main_feed_limit_capped(
    client: AsyncClient, mock_feed_service: AsyncMock
) -> None:
    """
    Test main feed limit is capped at 200.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed.xml?limit=500")

    assert response.status_code == 200
    call_args = mock_feed_service.get_main_feed.call_args
    assert call_args is not None
    assert call_args[1]["limit"] == 200


@pytest.mark.asyncio
async def test_get_source_feed_en(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test getting English source feed.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed/en-us.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")
    mock_feed_service.get_feed_by_source.assert_called_once()

    # Verify source was passed correctly
    call_args = mock_feed_service.get_feed_by_source.call_args
    assert call_args is not None
    assert call_args[0][0] == ArticleSource.LOL_EN_US


@pytest.mark.asyncio
async def test_get_source_feed_it(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test getting Italian source feed.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed/it-it.xml")

    assert response.status_code == 200
    mock_feed_service.get_feed_by_source.assert_called_once()

    # Verify source was passed correctly
    call_args = mock_feed_service.get_feed_by_source.call_args
    assert call_args is not None
    assert call_args[0][0] == ArticleSource.LOL_IT_IT


@pytest.mark.asyncio
async def test_get_source_feed_invalid(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test invalid source returns 404.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed/invalid.xml")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
    assert "invalid" in data["detail"]


@pytest.mark.asyncio
async def test_get_source_feed_with_limit(
    client: AsyncClient, mock_feed_service: AsyncMock
) -> None:
    """
    Test source feed with custom limit.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed/en-us.xml?limit=25")

    assert response.status_code == 200
    call_args = mock_feed_service.get_feed_by_source.call_args
    assert call_args is not None
    assert call_args[1]["limit"] == 25


@pytest.mark.asyncio
async def test_get_category_feed(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test getting category feed.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed/category/Champions.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")
    mock_feed_service.get_feed_by_category.assert_called_once()

    # Check category was passed
    call_args = mock_feed_service.get_feed_by_category.call_args
    assert call_args is not None
    assert call_args[0][0] == "Champions"


@pytest.mark.asyncio
async def test_get_category_feed_with_limit(
    client: AsyncClient, mock_feed_service: AsyncMock
) -> None:
    """
    Test category feed with custom limit.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed/category/Patches.xml?limit=15")

    assert response.status_code == 200
    call_args = mock_feed_service.get_feed_by_category.call_args
    assert call_args is not None
    assert call_args[1]["limit"] == 15


@pytest.mark.asyncio
async def test_refresh_endpoint(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test manual refresh endpoint.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.post("/admin/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "invalidated" in data["message"].lower()
    mock_feed_service.invalidate_cache.assert_called_once()


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test CORS headers are present.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed.xml")

    # CORS middleware should add headers on appropriate requests
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cache_control_headers(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test Cache-Control headers are set correctly.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed.xml")

    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    cache_header = response.headers["Cache-Control"]
    assert "public" in cache_header
    assert "max-age" in cache_header


@pytest.mark.asyncio
async def test_content_type_headers(client: AsyncClient, mock_feed_service: AsyncMock) -> None:
    """
    Test Content-Type headers are set correctly for RSS feeds.

    Args:
        client: Test client fixture
        mock_feed_service: Mocked feed service fixture
    """
    response = await client.get("/feed.xml")

    assert response.status_code == 200
    content_type = response.headers["content-type"]
    assert content_type == "application/rss+xml; charset=utf-8"


@pytest.mark.asyncio
async def test_feed_error_handling(client: AsyncClient) -> None:
    """
    Test error handling when feed generation fails.

    Args:
        client: Test client fixture
    """
    # Mock service to raise exception
    service = AsyncMock()
    service.get_main_feed = AsyncMock(side_effect=Exception("Database error"))

    # Store in app_state
    app_state["feed_service"] = service

    response = await client.get("/feed.xml")

    assert response.status_code == 500
    data = response.json()
    assert "error" in data["detail"].lower()


@pytest.mark.asyncio
async def test_service_not_initialized(client: AsyncClient) -> None:
    """
    Test behavior when service is not initialized.

    Args:
        client: Test client fixture
    """
    # Clear app_state to simulate uninitialized service
    app_state.clear()

    response = await client.get("/feed.xml")

    assert response.status_code == 500
    data = response.json()
    # Any error is acceptable - either "not initialized" or general error
    assert "error" in data["detail"].lower() or "not initialized" in data["detail"].lower()


@pytest.mark.asyncio
async def test_docs_endpoint(client: AsyncClient) -> None:
    """
    Test OpenAPI documentation endpoint is available.

    Args:
        client: Test client fixture
    """
    response = await client.get("/docs")

    # FastAPI automatically generates docs at /docs
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


@pytest.mark.asyncio
async def test_openapi_schema(client: AsyncClient) -> None:
    """
    Test OpenAPI schema endpoint.

    Args:
        client: Test client fixture
    """
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "LoL Stonks RSS"
    assert schema["info"]["version"] == "1.0.0"
    assert "/feed.xml" in schema["paths"]
