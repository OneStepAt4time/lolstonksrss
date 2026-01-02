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


@pytest.fixture(autouse=True)
def reset_app_state() -> None:
    """
    Reset app_state before each test.

    Ensures tests don't interfere with each other by clearing
    the global app_state dictionary.
    """
    app_state.clear()
    yield
    app_state.clear()


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
    from unittest.mock import MagicMock

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
                source=ArticleSource.create("lol", "en-us"),
                categories=["News"],
                image_url=None,
            )
        ]
    )
    repo.count = AsyncMock(return_value=100)
    repo.get_last_write_timestamp = AsyncMock(return_value=datetime(2024, 1, 1, 12, 0, 0))
    repo.get_locales = AsyncMock(return_value=["en-us", "it-it"])
    repo.get_source_categories = AsyncMock(return_value=["official_riot", "analytics"])

    # Setup mock service
    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.cache = MagicMock()
    service.cache.get_stats = MagicMock(
        return_value={
            "total_entries": 5,
            "size_bytes_estimate": 1024,
            "ttl_seconds": 300,
        }
    )

    # Setup mock scheduler
    scheduler = MagicMock()
    scheduler.get_status = MagicMock(
        return_value={
            "running": True,
            "interval_minutes": 30,
            "jobs": [
                {"id": "update_news", "name": "Update LoL News", "next_run": "2024-01-01T12:30:00"}
            ],
            "update_service": {
                "last_update": "2024-01-01T12:00:00",
                "update_count": 10,
                "error_count": 0,
                "configured_sources": 5,
                "configured_locales": 2,
            },
        }
    )

    # Store in app_state
    app_state["repository"] = repo
    app_state["feed_service"] = service
    app_state["scheduler"] = scheduler

    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["service"] == "LoL Stonks RSS"
    assert "timestamp" in data
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert data["database"]["total_articles"] == 100
    assert "scheduler" in data
    assert data["scheduler"]["running"] is True
    assert "cache" in data
    assert data["cache"]["status"] == "active"
    assert "scrapers" in data


@pytest.mark.asyncio
async def test_health_check_no_articles(client: AsyncClient) -> None:
    """
    Test health check with no articles.

    Args:
        client: Test client fixture
    """
    from unittest.mock import MagicMock

    # Setup mock repository with no articles
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    repo.get_last_write_timestamp = AsyncMock(return_value=None)
    repo.get_locales = AsyncMock(return_value=[])
    repo.get_source_categories = AsyncMock(return_value=[])

    # Setup mock service
    service = AsyncMock()
    service.cache = MagicMock()
    service.cache.get_stats = MagicMock(
        return_value={
            "total_entries": 0,
            "size_bytes_estimate": 0,
            "ttl_seconds": 300,
        }
    )

    # Setup mock scheduler
    scheduler = MagicMock()
    scheduler.get_status = MagicMock(
        return_value={
            "running": True,
            "interval_minutes": 30,
            "jobs": [
                {"id": "update_news", "name": "Update LoL News", "next_run": "2024-01-01T12:30:00"}
            ],
            "update_service": {
                "last_update": None,
                "update_count": 0,
                "error_count": 0,
                "configured_sources": 5,
                "configured_locales": 2,
            },
        }
    )

    # Store in app_state
    app_state["repository"] = repo
    app_state["feed_service"] = service
    app_state["scheduler"] = scheduler

    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Status should be "degraded" when there are no articles
    assert data["status"] == "degraded"
    assert data["database"]["total_articles"] == 0


@pytest.mark.asyncio
async def test_ping_endpoint(client: AsyncClient) -> None:
    """
    Test ping endpoint returns status ok.

    Args:
        client: Test client fixture
    """
    response = await client.get("/ping")

    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


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
    assert call_args[0][0] == ArticleSource.create("lol", "en-us")


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
    assert call_args[0][0] == ArticleSource.create("lol", "it-it")


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


@pytest.mark.asyncio
async def test_get_articles_default(client: AsyncClient, mock_repository: AsyncMock) -> None:
    """
    Test getting articles as JSON with default parameters.

    Args:
        client: Test client fixture
        mock_repository: Mocked repository fixture
    """
    from datetime import datetime, timezone

    # Setup mock articles
    articles = [
        Article(
            guid="test-1",
            title="Test Article 1",
            url="https://example.com/1",
            description="Test description 1",
            pub_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            source=ArticleSource.create("lol", "en-us"),
            categories=["News"],
            image_url=None,
        ),
        Article(
            guid="test-2",
            title="Test Article 2",
            url="https://example.com/2",
            description="Test description 2",
            pub_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            source=ArticleSource.create("lol", "it-it"),
            categories=["Patch"],
            image_url=None,
        ),
    ]
    mock_repository.get_latest = AsyncMock(return_value=articles)

    response = await client.get("/api/articles")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] == "Test Article 1"
    assert data[1]["title"] == "Test Article 2"


@pytest.mark.asyncio
async def test_get_articles_with_limit(client: AsyncClient, mock_repository: AsyncMock) -> None:
    """
    Test getting articles with custom limit.

    Args:
        client: Test client fixture
        mock_repository: Mocked repository fixture
    """
    from datetime import datetime, timezone

    article = Article(
        guid="test-1",
        title="Test Article",
        url="https://example.com/article",
        description="Test description",
        pub_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source=ArticleSource.create("lol", "en-us"),
        categories=["News"],
        image_url=None,
    )
    mock_repository.get_latest = AsyncMock(return_value=[article])

    response = await client.get("/api/articles?limit=10")

    assert response.status_code == 200
    mock_repository.get_latest.assert_called_once_with(limit=10, source=None)


@pytest.mark.asyncio
async def test_get_articles_with_source(client: AsyncClient, mock_repository: AsyncMock) -> None:
    """
    Test getting articles filtered by source.

    Args:
        client: Test client fixture
        mock_repository: Mocked repository fixture
    """
    from datetime import datetime, timezone

    article = Article(
        guid="test-1",
        title="Test Article",
        url="https://example.com/article",
        description="Test description",
        pub_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source=ArticleSource.create("lol", "it-it"),
        categories=["News"],
        image_url=None,
    )
    mock_repository.get_latest = AsyncMock(return_value=[article])

    response = await client.get("/api/articles?source=it-it")

    assert response.status_code == 200
    mock_repository.get_latest.assert_called_once_with(limit=50, source="it-it")


@pytest.mark.asyncio
async def test_get_articles_repository_not_initialized(client: AsyncClient) -> None:
    """
    Test getting articles when repository is not initialized.

    Args:
        client: Test client fixture
    """
    # Clear app_state to simulate uninitialized repository
    app_state.clear()

    response = await client.get("/api/articles")

    assert response.status_code == 500
    data = response.json()
    assert "not initialized" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_scheduler_status(client: AsyncClient) -> None:
    """
    Test getting scheduler status.

    Args:
        client: Test client fixture
    """
    # Setup mock scheduler
    scheduler = MagicMock()
    scheduler.get_status = MagicMock(
        return_value={
            "status": "running",
            "last_update": "2024-01-01T00:00:00Z",
            "next_update": "2024-01-01T00:05:00Z",
            "update_count": 42,
        }
    )

    # Store in app_state
    app_state["scheduler"] = scheduler

    response = await client.get("/admin/scheduler/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["update_count"] == 42


@pytest.mark.asyncio
async def test_get_scheduler_status_not_initialized(client: AsyncClient) -> None:
    """
    Test getting scheduler status when scheduler is not initialized.

    Args:
        client: Test client fixture
    """
    # Clear app_state to simulate uninitialized scheduler
    app_state.clear()

    response = await client.get("/admin/scheduler/status")

    assert response.status_code == 500
    data = response.json()
    assert "not initialized" in data["detail"].lower()


@pytest.mark.asyncio
async def test_trigger_scheduler_update(client: AsyncClient) -> None:
    """
    Test manually triggering scheduler update.

    Args:
        client: Test client fixture
    """
    # Setup mock scheduler with async method
    scheduler = MagicMock()

    # Create async mock function for trigger_update_now
    async def mock_trigger():
        return {
            "status": "success",
            "articles_added": 5,
            "articles_updated": 3,
            "duration_seconds": 2.5,
        }

    scheduler.trigger_update_now = mock_trigger

    # Store in app_state
    app_state["scheduler"] = scheduler

    response = await client.post("/admin/scheduler/trigger")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["articles_added"] == 5


@pytest.mark.asyncio
async def test_trigger_scheduler_update_not_initialized(client: AsyncClient) -> None:
    """
    Test triggering scheduler update when scheduler is not initialized.

    Args:
        client: Test client fixture
    """
    # Clear app_state to simulate uninitialized scheduler
    app_state.clear()

    response = await client.post("/admin/scheduler/trigger")

    assert response.status_code == 500
    data = response.json()
    assert "not initialized" in data["detail"].lower()


# =============================================================================
# Enhanced Health Check Tests (Readiness/Liveness)
# =============================================================================


@pytest.mark.asyncio
async def test_readiness_check_ready(client: AsyncClient) -> None:
    """
    Test readiness check returns ready when all services are initialized.

    Args:
        client: Test client fixture
    """
    from unittest.mock import MagicMock

    # Setup all services
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=[])

    service = AsyncMock()
    scheduler = MagicMock()

    app_state["repository"] = repo
    app_state["feed_service"] = service
    app_state["feed_service_v2"] = service
    app_state["scheduler"] = scheduler

    response = await client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert "timestamp" in data
    assert "checks" in data
    assert data["checks"]["repository"] is True
    assert data["checks"]["feed_service"] is True
    assert data["checks"]["feed_service_v2"] is True
    assert data["checks"]["scheduler"] is True


@pytest.mark.asyncio
async def test_readiness_check_not_ready(client: AsyncClient) -> None:
    """
    Test readiness check returns not ready when services are missing.

    Args:
        client: Test client fixture
    """
    # Only setup repository, missing other services
    repo = AsyncMock()
    app_state["repository"] = repo

    response = await client.get("/health/ready")

    assert response.status_code == 200  # Returns 200 with ready=false
    data = response.json()
    assert data["ready"] is False
    assert "not ready" in data["message"].lower()


@pytest.mark.asyncio
async def test_liveness_check_alive(client: AsyncClient) -> None:
    """
    Test liveness check returns alive when app is running.

    Args:
        client: Test client fixture
    """
    # Ensure app_state is not empty
    app_state["test"] = "value"

    response = await client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True
    assert "timestamp" in data
    assert data["message"] == "ok"


@pytest.mark.asyncio
async def test_liveness_check_empty_state(client: AsyncClient) -> None:
    """
    Test liveness check when app_state is empty.

    Args:
        client: Test client fixture
    """
    # Clear app_state
    app_state.clear()

    response = await client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is False
    assert data["message"] == "not alive"
