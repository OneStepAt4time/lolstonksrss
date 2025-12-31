"""
Tests for RSS feed service.

This module tests the FeedService class to ensure proper caching,
feed generation, and database integration.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import feedparser
import pytest

from src.models import Article, ArticleSource
from src.rss.feed_service import FeedService


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create mock article repository."""
    repo = AsyncMock()

    # Default articles for testing
    repo.get_latest = AsyncMock(
        return_value=[
            Article(
                title="Test Article 1",
                url="https://example.com/test1",
                pub_date=datetime(2025, 12, 28, 10, 0, 0, tzinfo=timezone.utc),
                guid="test-1",
                source=ArticleSource.LOL_EN_US,
                description="First test article",
                categories=["News", "Champions"],
            ),
            Article(
                title="Test Article 2",
                url="https://example.com/test2",
                pub_date=datetime(2025, 12, 27, 15, 30, 0, tzinfo=timezone.utc),
                guid="test-2",
                source=ArticleSource.LOL_EN_US,
                description="Second test article",
                categories=["Patches"],
            ),
            Article(
                title="Articolo di Test 3",
                url="https://example.com/test3",
                pub_date=datetime(2025, 12, 26, 8, 0, 0, tzinfo=timezone.utc),
                guid="test-3",
                source=ArticleSource.LOL_IT_IT,
                description="Terzo articolo di test",
                categories=["News"],
            ),
        ]
    )

    return repo


@pytest.mark.asyncio
async def test_feed_service_initialization(mock_repository: AsyncMock) -> None:
    """Test feed service initialization."""
    service = FeedService(mock_repository, cache_ttl=300)

    assert service.repository == mock_repository
    assert service.cache is not None
    assert service.generator_en is not None
    assert service.generator_it is not None


@pytest.mark.asyncio
async def test_get_main_feed(mock_repository: AsyncMock) -> None:
    """Test getting main RSS feed."""
    service = FeedService(mock_repository, cache_ttl=300)

    feed_xml = await service.get_main_feed("http://localhost:8000/feed.xml")

    # Should be valid RSS
    assert "<?xml" in feed_xml
    assert "<rss" in feed_xml
    assert 'version="2.0"' in feed_xml

    # Repository should be called once
    mock_repository.get_latest.assert_called_once_with(limit=50)

    # Parse and validate
    feed = feedparser.parse(feed_xml)
    assert len(feed.entries) == 3


@pytest.mark.asyncio
async def test_get_main_feed_with_limit(mock_repository: AsyncMock) -> None:
    """Test getting main feed with custom limit."""
    service = FeedService(mock_repository)

    await service.get_main_feed("http://localhost:8000/feed.xml", limit=10)

    mock_repository.get_latest.assert_called_once_with(limit=10)


@pytest.mark.asyncio
async def test_feed_caching(mock_repository: AsyncMock) -> None:
    """Test that feed caching works correctly."""
    service = FeedService(mock_repository, cache_ttl=300)

    # First call
    feed1 = await service.get_main_feed("http://localhost:8000/feed.xml")

    # Second call (should use cache)
    feed2 = await service.get_main_feed("http://localhost:8000/feed.xml")

    # Feeds should be identical
    assert feed1 == feed2

    # Repository should only be called once
    assert mock_repository.get_latest.call_count == 1


@pytest.mark.asyncio
async def test_different_limits_different_cache(mock_repository: AsyncMock) -> None:
    """Test that different limits use different cache keys."""
    service = FeedService(mock_repository, cache_ttl=300)

    # First call with limit 50
    await service.get_main_feed("http://localhost:8000/feed.xml", limit=50)

    # Second call with different limit
    await service.get_main_feed("http://localhost:8000/feed.xml", limit=25)

    # Repository should be called twice (different cache keys)
    assert mock_repository.get_latest.call_count == 2


@pytest.mark.asyncio
async def test_get_feed_by_source_en(mock_repository: AsyncMock) -> None:
    """Test getting feed filtered by English source."""
    service = FeedService(mock_repository)

    feed_xml = await service.get_feed_by_source(
        ArticleSource.LOL_EN_US, "http://localhost:8000/feed/en-us.xml"
    )

    # Should be valid RSS
    assert "<?xml" in feed_xml
    assert "<rss" in feed_xml

    # Repository should be called with source filter
    mock_repository.get_latest.assert_called_once_with(limit=50, source="lol-en-us")

    # Parse and validate
    feed = feedparser.parse(feed_xml)
    assert "lol-en-us" in feed.feed.title.lower()


@pytest.mark.asyncio
async def test_get_feed_by_source_it(mock_repository: AsyncMock) -> None:
    """Test getting feed filtered by Italian source."""
    # Create mock with only Italian articles
    mock_repo = AsyncMock()
    mock_repo.get_latest = AsyncMock(
        return_value=[
            Article(
                title="Articolo Italiano",
                url="https://example.com/it",
                pub_date=datetime(2025, 12, 28, 10, 0, 0, tzinfo=timezone.utc),
                guid="it-1",
                source=ArticleSource.LOL_IT_IT,
                description="Descrizione italiana",
                categories=["Notizie"],
            )
        ]
    )

    service = FeedService(mock_repo)

    feed_xml = await service.get_feed_by_source(
        ArticleSource.LOL_IT_IT, "http://localhost:8000/feed/it-it.xml"
    )

    # Should use Italian generator
    feed = feedparser.parse(feed_xml)
    assert feed.feed.language == "it"


@pytest.mark.asyncio
async def test_get_feed_by_source_caching(mock_repository: AsyncMock) -> None:
    """Test that source-filtered feeds are cached."""
    service = FeedService(mock_repository, cache_ttl=300)

    # First call
    feed1 = await service.get_feed_by_source(
        ArticleSource.LOL_EN_US, "http://localhost:8000/feed/en-us.xml"
    )

    # Second call (should use cache)
    feed2 = await service.get_feed_by_source(
        ArticleSource.LOL_EN_US, "http://localhost:8000/feed/en-us.xml"
    )

    assert feed1 == feed2
    assert mock_repository.get_latest.call_count == 1


@pytest.mark.asyncio
async def test_get_feed_by_category(mock_repository: AsyncMock) -> None:
    """Test getting feed filtered by category."""
    service = FeedService(mock_repository)

    feed_xml = await service.get_feed_by_category(
        "Champions", "http://localhost:8000/feed/champions.xml"
    )

    # Should be valid RSS
    assert "<?xml" in feed_xml
    assert "<rss" in feed_xml

    # Repository should fetch more articles for filtering
    mock_repository.get_latest.assert_called_once_with(limit=100)  # limit * 2

    # Parse and validate
    feed = feedparser.parse(feed_xml)
    assert "Champions" in feed.feed.title


@pytest.mark.asyncio
async def test_get_feed_by_category_filters_correctly(mock_repository: AsyncMock) -> None:
    """Test that category filtering works correctly."""
    service = FeedService(mock_repository)

    feed_xml = await service.get_feed_by_category(
        "Champions", "http://localhost:8000/feed/champions.xml"
    )

    feed = feedparser.parse(feed_xml)

    # Only articles with "Champions" category should be included
    # From mock_repository, only first article has "Champions"
    assert len(feed.entries) == 1
    assert feed.entries[0].title == "Test Article 1"


@pytest.mark.asyncio
async def test_get_feed_by_category_caching(mock_repository: AsyncMock) -> None:
    """Test that category-filtered feeds are cached."""
    service = FeedService(mock_repository, cache_ttl=300)

    # First call
    feed1 = await service.get_feed_by_category("News", "http://localhost:8000/feed/news.xml")

    # Second call (should use cache)
    feed2 = await service.get_feed_by_category("News", "http://localhost:8000/feed/news.xml")

    assert feed1 == feed2
    assert mock_repository.get_latest.call_count == 1


@pytest.mark.asyncio
async def test_invalidate_cache(mock_repository: AsyncMock) -> None:
    """Test cache invalidation."""
    service = FeedService(mock_repository, cache_ttl=300)

    # Generate feed (will be cached)
    await service.get_main_feed("http://localhost:8000/feed.xml")
    assert mock_repository.get_latest.call_count == 1

    # Invalidate cache
    service.invalidate_cache()

    # Generate again (should call repository again)
    await service.get_main_feed("http://localhost:8000/feed.xml")
    assert mock_repository.get_latest.call_count == 2


@pytest.mark.asyncio
async def test_empty_articles_list(mock_repository: AsyncMock) -> None:
    """Test feed generation with no articles."""
    # Create mock that returns empty list
    mock_repo = AsyncMock()
    mock_repo.get_latest = AsyncMock(return_value=[])

    service = FeedService(mock_repo)

    feed_xml = await service.get_main_feed("http://localhost:8000/feed.xml")

    # Should still be valid RSS
    assert "<?xml" in feed_xml
    assert "<rss" in feed_xml

    feed = feedparser.parse(feed_xml)
    assert len(feed.entries) == 0


@pytest.mark.asyncio
async def test_multiple_categories_per_article(mock_repository: AsyncMock) -> None:
    """Test feed generation with articles having multiple categories."""
    service = FeedService(mock_repository)

    feed_xml = await service.get_main_feed("http://localhost:8000/feed.xml")
    feed = feedparser.parse(feed_xml)

    # Find article with multiple categories (Test Article 1)
    entry = next(e for e in feed.entries if "Test Article 1" in e.title)
    tags = [tag["term"] for tag in entry.tags]

    assert "News" in tags
    assert "Champions" in tags


@pytest.mark.asyncio
async def test_feed_service_with_custom_cache_ttl(mock_repository: AsyncMock) -> None:
    """Test feed service with custom cache TTL."""
    service = FeedService(mock_repository, cache_ttl=600)

    # Verify cache is initialized with correct TTL
    assert service.cache.default_ttl == 600


@pytest.mark.asyncio
async def test_concurrent_requests(mock_repository: AsyncMock) -> None:
    """Test handling of concurrent feed requests."""
    service = FeedService(mock_repository, cache_ttl=300)

    # Make multiple concurrent requests
    import asyncio

    feeds = await asyncio.gather(
        service.get_main_feed("http://localhost:8000/feed.xml"),
        service.get_main_feed("http://localhost:8000/feed.xml"),
        service.get_main_feed("http://localhost:8000/feed.xml"),
    )

    # All should return the same feed
    assert feeds[0] == feeds[1] == feeds[2]


@pytest.mark.asyncio
async def test_feed_url_in_output(mock_repository: AsyncMock) -> None:
    """Test that feed URL appears in the generated feed."""
    service = FeedService(mock_repository)

    feed_url = "http://example.com/custom/feed.xml"
    feed_xml = await service.get_main_feed(feed_url)

    # Feed URL should be in the XML (as self link)
    assert feed_url in feed_xml


@pytest.mark.asyncio
async def test_category_feed_with_no_matches(mock_repository: AsyncMock) -> None:
    """Test category feed when no articles match."""
    service = FeedService(mock_repository)

    # Request feed for category that doesn't exist
    feed_xml = await service.get_feed_by_category(
        "NonExistentCategory", "http://localhost:8000/feed/nonexistent.xml"
    )

    feed = feedparser.parse(feed_xml)

    # Should return empty feed
    assert len(feed.entries) == 0
    assert "NonExistentCategory" in feed.feed.title


@pytest.mark.asyncio
async def test_source_feed_with_no_articles(mock_repository: AsyncMock) -> None:
    """Test source feed when no articles are returned."""
    # Create mock that returns empty list
    mock_repo = AsyncMock()
    mock_repo.get_latest = AsyncMock(return_value=[])

    service = FeedService(mock_repo)

    feed_xml = await service.get_feed_by_source(
        ArticleSource.LOL_EN_US, "http://localhost:8000/feed/en-us.xml"
    )

    feed = feedparser.parse(feed_xml)
    assert len(feed.entries) == 0


@pytest.mark.asyncio
async def test_feed_service_uses_config_settings() -> None:
    """Test that feed service uses configuration settings."""
    mock_repo = AsyncMock()
    mock_repo.get_latest = AsyncMock(return_value=[])

    # Mock settings
    with patch("src.rss.feed_service.settings") as mock_settings:
        mock_settings.feed_title_en = "Custom EN Title"
        mock_settings.feed_title_it = "Custom IT Title"
        mock_settings.feed_description_en = "Custom EN Description"
        mock_settings.feed_description_it = "Custom IT Description"

        service = FeedService(mock_repo)

        # Generators should use custom settings
        assert service.generator_en.feed_title == "Custom EN Title"
        assert service.generator_it.feed_title == "Custom IT Title"
        assert service.generator_en.feed_description == "Custom EN Description"
        assert service.generator_it.feed_description == "Custom IT Description"


@pytest.mark.asyncio
async def test_cache_keys_are_unique() -> None:
    """Test that different feed types have unique cache keys."""
    mock_repo = AsyncMock()
    mock_repo.get_latest = AsyncMock(return_value=[])

    service = FeedService(mock_repo, cache_ttl=300)

    # Generate different feeds
    await service.get_main_feed("http://localhost/main.xml", limit=50)
    await service.get_feed_by_source(ArticleSource.LOL_EN_US, "http://localhost/en.xml", limit=50)
    await service.get_feed_by_category("News", "http://localhost/news.xml", limit=50)

    # Each should trigger a repository call (different cache keys)
    assert mock_repo.get_latest.call_count == 3
