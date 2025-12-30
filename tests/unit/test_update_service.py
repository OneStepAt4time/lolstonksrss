"""
Tests for UpdateService.

This module tests the update service functionality including
fetching news from multiple sources and saving to database.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.services.update_service import UpdateService
from src.models import Article, ArticleSource


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def update_service(mock_repository: AsyncMock) -> UpdateService:
    """Create an UpdateService instance with mock repository."""
    return UpdateService(mock_repository)


@pytest.mark.asyncio
async def test_update_service_initialization(update_service: UpdateService) -> None:
    """Test that UpdateService initializes correctly."""
    assert update_service.repository is not None
    assert len(update_service.clients) == 2
    assert "en-us" in update_service.clients
    assert "it-it" in update_service.clients
    assert update_service.last_update is None
    assert update_service.update_count == 0
    assert update_service.error_count == 0


@pytest.mark.asyncio
async def test_update_all_sources(
    update_service: UpdateService, mock_repository: AsyncMock
) -> None:
    """Test updating all sources successfully."""
    # Create mock articles
    mock_articles = [
        Article(
            title="Test Article 1",
            url="http://test.com/1",
            pub_date=datetime.utcnow(),
            guid="test-1",
            source=ArticleSource.LOL_EN_US,
            description="Test description 1",
            categories=["News"],
        ),
        Article(
            title="Test Article 2",
            url="http://test.com/2",
            pub_date=datetime.utcnow(),
            guid="test-2",
            source=ArticleSource.LOL_EN_US,
            description="Test description 2",
            categories=["Patches"],
        ),
    ]

    # Mock API client
    mock_client = AsyncMock()
    mock_client.fetch_news = AsyncMock(return_value=mock_articles)

    # Replace clients with mock
    for locale in update_service.clients:
        update_service.clients[locale] = mock_client

    # Run update
    stats = await update_service.update_all_sources()

    # Verify stats
    assert stats["total_fetched"] == 4  # 2 articles x 2 locales
    assert stats["total_new"] == 4
    assert stats["total_duplicates"] == 0
    assert "en-us" in stats["sources"]
    assert "it-it" in stats["sources"]
    assert "started_at" in stats
    assert "completed_at" in stats
    assert "elapsed_seconds" in stats
    assert len(stats["errors"]) == 0

    # Verify service state updated
    assert update_service.last_update is not None
    assert update_service.update_count == 1
    assert update_service.error_count == 0


@pytest.mark.asyncio
async def test_update_all_sources_with_duplicates(
    update_service: UpdateService, mock_repository: AsyncMock
) -> None:
    """Test updating with duplicate articles."""
    # Create mock articles
    mock_articles = [
        Article(
            title="Test Article",
            url="http://test.com/1",
            pub_date=datetime.utcnow(),
            guid="test-1",
            source=ArticleSource.LOL_EN_US,
            description="Test description",
            categories=["News"],
        )
    ]

    # Mock repository to return False (duplicate) for some saves
    mock_repository.save = AsyncMock(side_effect=[True, False])

    # Mock API client
    mock_client = AsyncMock()
    mock_client.fetch_news = AsyncMock(return_value=mock_articles)

    for locale in update_service.clients:
        update_service.clients[locale] = mock_client

    # Run update
    stats = await update_service.update_all_sources()

    # Verify duplicates detected
    assert stats["total_fetched"] == 2
    assert stats["total_new"] == 1
    assert stats["total_duplicates"] == 1


@pytest.mark.asyncio
async def test_update_all_sources_with_errors(
    update_service: UpdateService, mock_repository: AsyncMock
) -> None:
    """Test updating with errors from one source."""
    # Mock one client to succeed and one to fail
    mock_success_client = AsyncMock()
    mock_success_client.fetch_news = AsyncMock(
        return_value=[
            Article(
                title="Test",
                url="http://test.com",
                pub_date=datetime.utcnow(),
                guid="test-1",
                source=ArticleSource.LOL_EN_US,
                description="Test",
                categories=["News"],
            )
        ]
    )

    mock_error_client = AsyncMock()
    mock_error_client.fetch_news = AsyncMock(side_effect=Exception("API Error"))

    update_service.clients["en-us"] = mock_success_client
    update_service.clients["it-it"] = mock_error_client

    # Run update
    stats = await update_service.update_all_sources()

    # Verify one source succeeded, one failed
    assert stats["total_fetched"] == 1  # Only en-us succeeded
    assert stats["total_new"] == 1
    assert len(stats["errors"]) == 1
    assert "it-it" in stats["errors"][0]
    assert update_service.error_count == 1


@pytest.mark.asyncio
async def test_get_status(update_service: UpdateService) -> None:
    """Test getting service status."""
    status = update_service.get_status()

    assert "last_update" in status
    assert "update_count" in status
    assert "error_count" in status
    assert "sources" in status
    assert status["sources"] == ["en-us", "it-it"]
    assert status["update_count"] == 0
    assert status["error_count"] == 0
    assert status["last_update"] is None


@pytest.mark.asyncio
async def test_get_status_after_update(
    update_service: UpdateService, mock_repository: AsyncMock
) -> None:
    """Test getting status after performing an update."""
    # Mock API client
    mock_client = AsyncMock()
    mock_client.fetch_news = AsyncMock(return_value=[])

    for locale in update_service.clients:
        update_service.clients[locale] = mock_client

    # Run update
    await update_service.update_all_sources()

    # Check status
    status = update_service.get_status()
    assert status["update_count"] == 1
    assert status["last_update"] is not None


@pytest.mark.asyncio
async def test_update_source_logging(
    update_service: UpdateService, mock_repository: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that update logging works correctly."""
    import logging

    caplog.set_level(logging.INFO)

    # Mock API client
    mock_client = AsyncMock()
    mock_client.fetch_news = AsyncMock(return_value=[])

    # Run update for one source
    stats = await update_service._update_source("en-us", mock_client)

    # Verify logging
    assert "Fetching articles for en-us" in caplog.text
    assert stats["fetched"] == 0
    assert stats["new"] == 0
    assert stats["duplicates"] == 0
