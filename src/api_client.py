"""
API client for fetching League of Legends news.

This module provides an async HTTP client for fetching news from the
official League of Legends Next.js API endpoints.
"""

import logging
import re
from datetime import datetime
from typing import Any

import httpx

from src.config import get_settings
from src.models import Article, ArticleSource
from src.utils.cache import TTLCache

logger = logging.getLogger(__name__)
settings = get_settings()


class LoLNewsAPIClient:
    """
    Async client for League of Legends news API.

    This client handles fetching news from the LoL Next.js JSON API,
    including build ID discovery and article parsing.
    """

    def __init__(self, base_url: str | None = None, cache: TTLCache | None = None) -> None:
        """
        Initialize the API client.

        Args:
            base_url: Base URL for LoL website (defaults to settings)
            cache: Optional TTLCache instance for caching build IDs
        """
        self.base_url = base_url or settings.lol_news_base_url
        self.cache = cache or TTLCache(default_ttl_seconds=settings.build_id_cache_seconds)

    async def get_build_id(self, locale: str = "en-us") -> str:
        """
        Extract Next.js buildId from HTML.
        Uses cache (24h TTL by default) to avoid repeated requests.

        Args:
            locale: Locale code (e.g., "en-us", "it-it")

        Returns:
            Build ID string

        Raises:
            ValueError: If buildId not found in HTML
            httpx.HTTPError: If HTTP request fails
        """
        cache_key = f"buildid_{locale}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug(f"Using cached buildId for {locale}: {cached}")
            return cached

        # Fetch HTML page
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            url = f"{self.base_url}/{locale}/news/"
            logger.info(f"Fetching buildId from: {url}")
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

        # Extract buildId using regex
        match = re.search(r'"buildId":"([^"]+)"', response.text)
        if not match:
            raise ValueError(f"BuildID not found in HTML for locale {locale}")

        build_id = match.group(1)

        # Cache it with TTL
        self.cache.set(cache_key, build_id)
        logger.info(f"Extracted buildId for {locale}: {build_id}")

        return build_id

    async def fetch_news(self, locale: str = "en-us") -> list[Article]:
        """
        Fetch news articles for a specific locale.

        API URL pattern: /_next/data/{BUILD_ID}/{locale}/news.json

        Args:
            locale: Locale code (e.g., "en-us", "it-it")

        Returns:
            List of Article instances

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            # Get buildID (from cache or fetch new)
            build_id = await self.get_build_id(locale)

            # Construct API URL
            api_url = f"{self.base_url}/_next/data/{build_id}/{locale}/news.json"

            # Fetch JSON data
            async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
                logger.info(f"Fetching news from: {api_url}")
                response = await client.get(api_url, follow_redirects=True)

                # If 404, buildID might be stale - invalidate cache and retry once
                if response.status_code == 404:
                    logger.warning(f"API returned 404, invalidating buildID cache for {locale}")
                    cache_key = f"buildid_{locale}"
                    self.cache.delete(cache_key)  # Delete from cache

                    # Retry with fresh buildID
                    build_id = await self.get_build_id(locale)
                    api_url = f"{self.base_url}/_next/data/{build_id}/{locale}/news.json"
                    logger.info(f"Retrying with fresh buildId: {api_url}")
                    response = await client.get(api_url, follow_redirects=True)

                response.raise_for_status()
                data = response.json()

            # Parse articles from response
            articles = self._parse_articles(data, locale)
            logger.info(f"Successfully fetched {len(articles)} articles for {locale}")

            return articles

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching news for {locale}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching news for {locale}: {e}")
            return []

    def _parse_articles(self, data: dict[str, Any], locale: str) -> list[Article]:
        """
        Parse API response and extract articles.

        Response structure: data['pageProps']['page']['blades'] -> find type='articleCardGrid'

        Args:
            data: JSON response from API
            locale: Locale code for source attribution

        Returns:
            List of Article instances
        """
        try:
            blades = data.get("pageProps", {}).get("page", {}).get("blades", [])

            # Find articleCardGrid blade
            article_blade = next((b for b in blades if b.get("type") == "articleCardGrid"), None)

            if not article_blade:
                logger.warning(f"No articleCardGrid found for {locale}")
                return []

            items = article_blade.get("items", [])
            articles = []

            for item in items:
                try:
                    article = self._transform_to_article(item, locale)
                    articles.append(article)
                except Exception as e:
                    logger.error(
                        f"Error transforming article: {e}, item: {item.get('title', 'N/A')}"
                    )
                    continue

            return articles

        except Exception as e:
            logger.error(f"Error parsing articles: {e}")
            return []

    def _transform_to_article(self, item: dict[str, Any], locale: str) -> Article:
        """
        Transform API item to Article object.

        Args:
            item: Raw article item from API
            locale: Locale code for source attribution

        Returns:
            Article instance

        Raises:
            ValueError: If required fields are missing
        """
        # Extract URL from action
        action = item.get("action", {})
        url = action.get("url") or action.get("payload", {}).get("url", "")

        if not url:
            raise ValueError("Article URL not found in item")

        # Parse published date
        pub_date_str = item.get("publishedAt", "")
        if not pub_date_str:
            raise ValueError("Article publishedAt not found in item")

        pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))

        # Map locale to ArticleSource
        source = ArticleSource.LOL_EN_US if locale == "en-us" else ArticleSource.LOL_IT_IT

        # Extract description
        description_obj = item.get("description", {})
        description = description_obj.get("body", "") if isinstance(description_obj, dict) else ""

        # Extract category
        category_obj = item.get("category", {})
        category = category_obj.get("title", "News") if isinstance(category_obj, dict) else "News"

        # Extract GUID from analytics or fallback to URL
        analytics = item.get("analytics", {})
        guid = analytics.get("contentId", url) if isinstance(analytics, dict) else url

        # Extract image URL
        media = item.get("media", {})
        image_url = media.get("url") if isinstance(media, dict) else None

        # Create Article instance
        article = Article(
            title=item.get("title", "No Title"),
            url=url,
            pub_date=pub_date,
            guid=guid,
            source=source,
            description=description,
            content="",  # Full content not available from API
            image_url=image_url,
            author="Riot Games",
            categories=[category],
        )

        return article
