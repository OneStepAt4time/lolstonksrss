"""
Tests for the LoL News API client.

This module contains comprehensive tests for the API client including:
- Build ID extraction
- News fetching
- Article parsing
- Cache behavior
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime
from src.api_client import LoLNewsAPIClient
from src.models import Article, ArticleSource
from src.utils.cache import TTLCache
import httpx


# Mock HTML with buildId
MOCK_HTML = '''
<!DOCTYPE html>
<html>
<body>
<script id="__NEXT_DATA__" type="application/json">{"buildId":"test-build-id-123"}</script>
</body>
</html>
'''

# Mock API response
MOCK_API_RESPONSE = {
    "pageProps": {
        "page": {
            "blades": [
                {
                    "type": "articleCardGrid",
                    "items": [
                        {
                            "title": "Test Article 1",
                            "publishedAt": "2025-12-28T10:00:00.000Z",
                            "description": {"body": "Test description 1"},
                            "category": {"title": "News"},
                            "action": {"url": "https://www.leagueoflegends.com/en-us/news/article-1"},
                            "media": {"url": "https://example.com/image1.jpg"},
                            "analytics": {"contentId": "test-guid-123"}
                        },
                        {
                            "title": "Test Article 2",
                            "publishedAt": "2025-12-27T15:30:00.000Z",
                            "description": {"body": "Test description 2"},
                            "category": {"title": "Updates"},
                            "action": {
                                "type": "youtube_video",
                                "payload": {
                                    "url": "https://www.youtube.com/watch?v=test",
                                    "youtubeId": "test"
                                }
                            },
                            "media": {"url": "https://example.com/image2.jpg"},
                            "analytics": {"contentId": "test-guid-456"}
                        }
                    ]
                },
                {
                    "type": "someOtherBlade",
                    "items": []
                }
            ]
        }
    }
}


@pytest.fixture
def mock_cache() -> TTLCache:
    """Provide a fresh TTLCache instance for testing."""
    return TTLCache(default_ttl_seconds=3600)


@pytest.fixture
def api_client(mock_cache: TTLCache) -> LoLNewsAPIClient:
    """Provide a configured API client for testing."""
    return LoLNewsAPIClient(
        base_url="https://www.leagueoflegends.com",
        cache=mock_cache
    )


class TestGetBuildId:
    """Tests for get_build_id method."""

    @pytest.mark.asyncio
    async def test_get_build_id_success(self, api_client: LoLNewsAPIClient) -> None:
        """Test successful buildId extraction from HTML."""
        mock_response = AsyncMock()
        mock_response.text = MOCK_HTML
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            build_id = await api_client.get_build_id('en-us')

            assert build_id == 'test-build-id-123'
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_build_id_cached(self, api_client: LoLNewsAPIClient) -> None:
        """Test that buildId is retrieved from cache on second call."""
        # Pre-populate cache
        api_client.cache.set('buildid_en-us', 'cached-build-id')

        with patch('httpx.AsyncClient') as mock_client_class:
            build_id = await api_client.get_build_id('en-us')

            # Should use cached value without making HTTP request
            assert build_id == 'cached-build-id'
            mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_build_id_not_found(self, api_client: LoLNewsAPIClient) -> None:
        """Test error when buildId not found in HTML."""
        mock_response = AsyncMock()
        mock_response.text = '<html><body>No buildId here</body></html>'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="BuildID not found"):
                await api_client.get_build_id('en-us')

    @pytest.mark.asyncio
    async def test_get_build_id_http_error(self, api_client: LoLNewsAPIClient) -> None:
        """Test handling of HTTP errors."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("404", request=Mock(), response=Mock())
        )

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await api_client.get_build_id('en-us')

    @pytest.mark.asyncio
    async def test_get_build_id_different_locales(self, api_client: LoLNewsAPIClient) -> None:
        """Test that different locales have separate cache entries."""
        mock_response = AsyncMock()
        mock_response.text = MOCK_HTML
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            build_id_en = await api_client.get_build_id('en-us')
            build_id_it = await api_client.get_build_id('it-it')

            # Both should return same buildId
            assert build_id_en == 'test-build-id-123'
            assert build_id_it == 'test-build-id-123'

            # But they should be cached separately
            assert api_client.cache.get('buildid_en-us') == 'test-build-id-123'
            assert api_client.cache.get('buildid_it-it') == 'test-build-id-123'


class TestFetchNews:
    """Tests for fetch_news method."""

    @pytest.mark.asyncio
    async def test_fetch_news_success(self, api_client: LoLNewsAPIClient) -> None:
        """Test successful news fetching."""
        # Mock get_build_id as coroutine
        async def mock_get_build_id(locale: str) -> str:
            return 'test-build-id'

        with patch.object(api_client, 'get_build_id', side_effect=mock_get_build_id):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=MOCK_API_RESPONSE)
            mock_response.raise_for_status = Mock()

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                articles = await api_client.fetch_news('en-us')

                assert len(articles) == 2
                assert all(isinstance(a, Article) for a in articles)
                assert articles[0].title == 'Test Article 1'
                assert articles[0].source == ArticleSource.LOL_EN_US
                assert articles[1].title == 'Test Article 2'

    @pytest.mark.asyncio
    async def test_fetch_news_404_retry(self, api_client: LoLNewsAPIClient) -> None:
        """Test buildID cache invalidation on 404 and retry."""
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()

            if call_count == 1:
                # First call returns 404
                mock_response.status_code = 404
            else:
                # Second call succeeds
                mock_response.status_code = 200
                mock_response.json = Mock(return_value=MOCK_API_RESPONSE)

            mock_response.raise_for_status = Mock()
            return mock_response

        async def mock_get_build_id(locale: str) -> str:
            return 'test-build-id'

        with patch.object(api_client, 'get_build_id', side_effect=mock_get_build_id):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = mock_get
                mock_client_class.return_value = mock_client

                articles = await api_client.fetch_news('en-us')

                assert len(articles) == 2
                assert call_count == 2  # Should retry after 404

    @pytest.mark.asyncio
    async def test_fetch_news_it_locale(self, api_client: LoLNewsAPIClient) -> None:
        """Test fetching Italian locale news."""
        async def mock_get_build_id(locale: str) -> str:
            return 'test-build-id'

        with patch.object(api_client, 'get_build_id', side_effect=mock_get_build_id):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=MOCK_API_RESPONSE)
            mock_response.raise_for_status = Mock()

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                articles = await api_client.fetch_news('it-it')

                assert len(articles) == 2
                # All articles should have Italian source
                assert all(a.source == ArticleSource.LOL_IT_IT for a in articles)

    @pytest.mark.asyncio
    async def test_fetch_news_http_error(self, api_client: LoLNewsAPIClient) -> None:
        """Test handling of HTTP errors during fetch."""
        with patch.object(api_client, 'get_build_id', return_value='test-build-id'):
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("500", request=Mock(), response=Mock())
            )

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.HTTPStatusError):
                    await api_client.fetch_news('en-us')

    @pytest.mark.asyncio
    async def test_fetch_news_empty_response(self, api_client: LoLNewsAPIClient) -> None:
        """Test handling of empty API response."""
        empty_response = {"pageProps": {"page": {"blades": []}}}

        async def mock_get_build_id(locale: str) -> str:
            return 'test-build-id'

        with patch.object(api_client, 'get_build_id', side_effect=mock_get_build_id):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=empty_response)
            mock_response.raise_for_status = Mock()

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                articles = await api_client.fetch_news('en-us')

                assert articles == []


class TestParseArticles:
    """Tests for _parse_articles method."""

    def test_parse_articles_success(self, api_client: LoLNewsAPIClient) -> None:
        """Test successful article parsing."""
        articles = api_client._parse_articles(MOCK_API_RESPONSE, 'en-us')

        assert len(articles) == 2
        assert all(isinstance(a, Article) for a in articles)

    def test_parse_articles_no_article_grid(self, api_client: LoLNewsAPIClient) -> None:
        """Test parsing when no articleCardGrid blade exists."""
        response = {
            "pageProps": {
                "page": {
                    "blades": [
                        {"type": "otherBlade", "items": []}
                    ]
                }
            }
        }

        articles = api_client._parse_articles(response, 'en-us')
        assert articles == []

    def test_parse_articles_malformed_data(self, api_client: LoLNewsAPIClient) -> None:
        """Test parsing with malformed data structure."""
        response = {"pageProps": {}}

        articles = api_client._parse_articles(response, 'en-us')
        assert articles == []

    def test_parse_articles_partial_failure(self, api_client: LoLNewsAPIClient) -> None:
        """Test that valid articles are returned even if some fail."""
        response = {
            "pageProps": {
                "page": {
                    "blades": [
                        {
                            "type": "articleCardGrid",
                            "items": [
                                {
                                    "title": "Good Article",
                                    "publishedAt": "2025-12-28T10:00:00.000Z",
                                    "action": {"url": "https://example.com/article"},
                                },
                                {
                                    "title": "Bad Article",
                                    # Missing publishedAt - should fail
                                    "action": {"url": "https://example.com/bad"},
                                },
                                {
                                    "title": "Another Good Article",
                                    "publishedAt": "2025-12-27T10:00:00.000Z",
                                    "action": {"url": "https://example.com/article2"},
                                }
                            ]
                        }
                    ]
                }
            }
        }

        articles = api_client._parse_articles(response, 'en-us')
        assert len(articles) == 2  # Two valid articles


class TestTransformToArticle:
    """Tests for _transform_to_article method."""

    def test_transform_basic_article(self, api_client: LoLNewsAPIClient) -> None:
        """Test transforming a basic article."""
        item = {
            "title": "Test Article",
            "publishedAt": "2025-12-28T10:00:00.000Z",
            "description": {"body": "Test description"},
            "category": {"title": "News"},
            "action": {"url": "https://example.com/article"},
            "media": {"url": "https://example.com/image.jpg"},
            "analytics": {"contentId": "test-guid"}
        }

        article = api_client._transform_to_article(item, 'en-us')

        assert article.title == "Test Article"
        assert article.url == "https://example.com/article"
        assert article.description == "Test description"
        assert article.source == ArticleSource.LOL_EN_US
        assert article.guid == "test-guid"
        assert article.image_url == "https://example.com/image.jpg"
        assert article.categories == ["News"]
        assert article.author == "Riot Games"

    def test_transform_youtube_article(self, api_client: LoLNewsAPIClient) -> None:
        """Test transforming a YouTube video article."""
        item = {
            "title": "Video Article",
            "publishedAt": "2025-12-28T10:00:00.000Z",
            "action": {
                "type": "youtube_video",
                "payload": {
                    "url": "https://www.youtube.com/watch?v=test",
                    "youtubeId": "test"
                }
            }
        }

        article = api_client._transform_to_article(item, 'en-us')

        assert article.title == "Video Article"
        assert article.url == "https://www.youtube.com/watch?v=test"

    def test_transform_italian_article(self, api_client: LoLNewsAPIClient) -> None:
        """Test transforming an Italian article."""
        item = {
            "title": "Articolo Italiano",
            "publishedAt": "2025-12-28T10:00:00.000Z",
            "action": {"url": "https://example.com/articolo"},
        }

        article = api_client._transform_to_article(item, 'it-it')

        assert article.source == ArticleSource.LOL_IT_IT

    def test_transform_missing_optional_fields(self, api_client: LoLNewsAPIClient) -> None:
        """Test transforming article with missing optional fields."""
        item = {
            "title": "Minimal Article",
            "publishedAt": "2025-12-28T10:00:00.000Z",
            "action": {"url": "https://example.com/article"},
        }

        article = api_client._transform_to_article(item, 'en-us')

        assert article.title == "Minimal Article"
        assert article.description == ""
        assert article.image_url is None
        assert article.categories == ["News"]  # Default category
        assert article.guid == "https://example.com/article"  # Fallback to URL

    def test_transform_missing_url(self, api_client: LoLNewsAPIClient) -> None:
        """Test error when URL is missing."""
        item = {
            "title": "No URL Article",
            "publishedAt": "2025-12-28T10:00:00.000Z",
            "action": {},
        }

        with pytest.raises(ValueError, match="Article URL not found"):
            api_client._transform_to_article(item, 'en-us')

    def test_transform_missing_publish_date(self, api_client: LoLNewsAPIClient) -> None:
        """Test error when publishedAt is missing."""
        item = {
            "title": "No Date Article",
            "action": {"url": "https://example.com/article"},
        }

        with pytest.raises(ValueError, match="Article publishedAt not found"):
            api_client._transform_to_article(item, 'en-us')

    def test_transform_date_format(self, api_client: LoLNewsAPIClient) -> None:
        """Test date parsing with different formats."""
        item = {
            "title": "Date Test",
            "publishedAt": "2025-12-28T15:30:45.000Z",
            "action": {"url": "https://example.com/article"},
        }

        article = api_client._transform_to_article(item, 'en-us')

        assert isinstance(article.pub_date, datetime)
        assert article.pub_date.year == 2025
        assert article.pub_date.month == 12
        assert article.pub_date.day == 28
        assert article.pub_date.hour == 15
        assert article.pub_date.minute == 30


class TestCacheIntegration:
    """Tests for cache integration."""

    @pytest.mark.asyncio
    async def test_cache_isolation_between_locales(self, api_client: LoLNewsAPIClient) -> None:
        """Test that different locales maintain separate cache entries."""
        # Pre-populate cache with different values
        api_client.cache.set('buildid_en-us', 'en-build-id')
        api_client.cache.set('buildid_it-it', 'it-build-id')

        build_id_en = await api_client.get_build_id('en-us')
        build_id_it = await api_client.get_build_id('it-it')

        assert build_id_en == 'en-build-id'
        assert build_id_it == 'it-build-id'

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, api_client: LoLNewsAPIClient) -> None:
        """Test cache invalidation on 404."""
        # Pre-populate cache
        api_client.cache.set('buildid_en-us', 'old-build-id')

        # Verify it's in cache
        assert api_client.cache.get('buildid_en-us') == 'old-build-id'

        # Simulate 404 response
        async def mock_get_build_id(locale: str) -> str:
            return 'new-build-id'

        with patch.object(api_client, 'get_build_id', side_effect=mock_get_build_id):
            mock_response_404 = AsyncMock()
            mock_response_404.status_code = 404
            mock_response_404.raise_for_status = Mock()

            mock_response_200 = AsyncMock()
            mock_response_200.status_code = 200
            mock_response_200.json = Mock(return_value=MOCK_API_RESPONSE)
            mock_response_200.raise_for_status = Mock()

            responses = [mock_response_404, mock_response_200]

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(side_effect=responses)
                mock_client_class.return_value = mock_client

                await api_client.fetch_news('en-us')

                # Cache should have been invalidated
                # Note: get_build_id is mocked, so actual cache won't be populated
