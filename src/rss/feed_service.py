"""
RSS feed service with caching support.

This module provides the FeedService class which manages RSS feed generation
with intelligent caching to reduce database load and improve performance.
"""

import logging

from src.config import get_settings
from src.database import ArticleRepository
from src.models import ArticleSource
from src.rss.generator import RSSFeedGenerator
from src.utils.cache import TTLCache

logger = logging.getLogger(__name__)
settings = get_settings()


class FeedService:
    """
    RSS feed service with caching.

    Provides cached RSS feeds with configurable TTL. Manages multiple
    generators for different languages and handles feed filtering by
    source and category.

    Attributes:
        repository: Article repository for database access
        cache: TTLCache instance for feed caching
        generator_en: English language feed generator
        generator_it: Italian language feed generator
    """

    def __init__(
        self, repository: ArticleRepository, cache_ttl: int = 300  # 5 minutes default
    ) -> None:
        """
        Initialize feed service.

        Args:
            repository: Article repository instance
            cache_ttl: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self.repository = repository
        self.cache = TTLCache(default_ttl_seconds=cache_ttl)

        # Initialize generators for different languages
        self.generator_en = RSSFeedGenerator(
            language="en",
            feed_title=getattr(settings, "feed_title_en", "League of Legends News"),
            feed_description=getattr(
                settings, "feed_description_en", "Latest League of Legends news and updates"
            ),
        )
        self.generator_it = RSSFeedGenerator(
            language="it",
            feed_title=getattr(settings, "feed_title_it", "Notizie League of Legends"),
            feed_description=getattr(
                settings,
                "feed_description_it",
                "Ultime notizie e aggiornamenti di League of Legends",
            ),
        )

    async def get_main_feed(self, feed_url: str, limit: int = 50) -> str:
        """
        Get main RSS feed (all sources, all categories).

        Fetches the latest articles from all sources and generates
        a combined RSS feed. Results are cached for performance.

        Args:
            feed_url: Self URL for the feed (for rel='self' link)
            limit: Maximum number of articles to include

        Returns:
            RSS 2.0 XML string
        """
        cache_key = f"feed_main_{limit}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached main feed")
            return str(cached)

        # Fetch articles from database
        articles = await self.repository.get_latest(limit=limit)

        # Generate feed (use EN generator for mixed content)
        feed_xml = self.generator_en.generate_feed(articles, feed_url)

        # Cache the result
        self.cache.set(cache_key, feed_xml)

        logger.info(f"Generated main feed with {len(articles)} articles")

        return feed_xml

    async def get_feed_by_source(
        self, source: ArticleSource, feed_url: str, limit: int = 50
    ) -> str:
        """
        Get RSS feed filtered by source.

        Fetches articles from a specific source and generates a language-
        specific RSS feed. Uses the appropriate generator based on source.

        Args:
            source: Article source to filter by
            feed_url: Self URL for the feed
            limit: Maximum number of articles to include

        Returns:
            RSS 2.0 XML string with source-filtered articles
        """
        cache_key = f"feed_source_{source.value}_{limit}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached feed for {source.value}")
            return str(cached)

        # Fetch articles for specific source
        articles = await self.repository.get_latest(limit=limit, source=source.value)

        # Choose generator based on source language
        generator = self.generator_it if source == ArticleSource.LOL_IT_IT else self.generator_en

        # Generate feed
        feed_xml = generator.generate_feed_by_source(articles, source, feed_url)

        # Cache the result
        self.cache.set(cache_key, feed_xml)

        logger.info(f"Generated feed for {source.value} with {len(articles)} articles")

        return feed_xml

    async def get_feed_by_category(self, category: str, feed_url: str, limit: int = 50) -> str:
        """
        Get RSS feed filtered by category.

        Fetches articles containing the specified category and generates
        a topic-specific RSS feed.

        Args:
            category: Category name to filter by
            feed_url: Self URL for the feed
            limit: Maximum number of articles to include

        Returns:
            RSS 2.0 XML string with category-filtered articles
        """
        cache_key = f"feed_category_{category}_{limit}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached feed for category {category}")
            return str(cached)

        # Fetch more articles than needed since we filter by category
        # This ensures we have enough articles after filtering
        articles = await self.repository.get_latest(limit=limit * 2)

        # Generate feed with category filter
        feed_xml = self.generator_en.generate_feed_by_category(articles, category, feed_url)

        # Cache the result
        self.cache.set(cache_key, feed_xml)

        # Log the actual count after filtering
        filtered_count = len([a for a in articles if category in a.categories])
        logger.info(f"Generated feed for category {category} with {filtered_count} articles")

        return feed_xml

    def invalidate_cache(self) -> None:
        """
        Invalidate all feed caches.

        Clears all cached feeds. Should be called after updating
        articles in the database to ensure feeds reflect the latest data.
        """
        self.cache.clear()
        logger.info("Feed cache invalidated")
