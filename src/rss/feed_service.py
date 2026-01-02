"""
RSS feed service with caching support.

This module provides the FeedService class which manages RSS feed generation
with intelligent caching to reduce database load and improve performance.

Also provides FeedServiceV2 with dynamic generator registry for multi-locale
RSS feeds supporting all 20 Riot locales.
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

        # Initialize generators for different languages using locale-based settings
        self.generator_en = RSSFeedGenerator(
            language="en",
            feed_title=settings.feed_titles.get("en-us", "League of Legends News"),
            feed_description=settings.feed_descriptions.get(
                "en-us", "Latest League of Legends news and updates"
            ),
        )
        self.generator_it = RSSFeedGenerator(
            language="it",
            feed_title=settings.feed_titles.get("it-it", "Notizie League of Legends"),
            feed_description=settings.feed_descriptions.get(
                "it-it", "Ultime notizie e aggiornamenti di League of Legends"
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
        cache_key = f"feed_source_{str(source)}_{limit}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached feed for {str(source)}")
            return str(cached)

        # Fetch articles for specific source
        articles = await self.repository.get_latest(limit=limit, source=str(source))

        # Choose generator based on source language
        generator = self.generator_it if source.locale == "it-it" else self.generator_en

        # Generate feed
        feed_xml = generator.generate_feed_by_source(articles, source, feed_url)

        # Cache the result
        self.cache.set(cache_key, feed_xml)

        logger.info(f"Generated feed for {str(source)} with {len(articles)} articles")

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


class FeedServiceV2:
    """
    RSS feed service with dynamic generator registry for multi-locale feeds.

    Supports all 20 Riot locales with per-locale feed generators that use
    localized titles and descriptions. Provides methods for fetching feeds
    by locale, source, and category with intelligent caching.

    Attributes:
        repository: Article repository for database access
        cache: TTLCache instance for feed caching
        generators: Dictionary mapping locale codes to RSSFeedGenerator instances
        supported_locales: List of supported locale codes
    """

    def __init__(
        self, repository: ArticleRepository, cache_ttl: int = 300  # 5 minutes default
    ) -> None:
        """
        Initialize feed service V2 with dynamic generator registry.

        Args:
            repository: Article repository instance
            cache_ttl: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self.repository = repository
        self.cache = TTLCache(default_ttl_seconds=cache_ttl)
        self.supported_locales = settings.supported_locales

        # Dynamic generator registry
        self.generators: dict[str, RSSFeedGenerator] = {}

        # Initialize generators for all supported locales
        self._init_generators()

        logger.info(f"FeedServiceV2 initialized with {len(self.generators)} locale generators")

    def _init_generators(self) -> None:
        """
        Initialize RSS feed generators for all supported locales.

        Creates an RSSFeedGenerator for each locale with localized titles
        and descriptions from settings. Extracts language code from locale
        for RSS language specification.
        """
        for locale in self.supported_locales:
            # Get localized title and description, with fallback
            title = settings.feed_titles.get(locale, "League of Legends News")
            description = settings.feed_descriptions.get(
                locale, f"Latest League of Legends news ({locale})"
            )

            # Extract language code from locale (e.g., "en-us" -> "en")
            language = locale.split("-")[0]

            # Create feed URL for this locale
            feed_link = f"{settings.base_url}/rss/{locale}.xml"

            self.generators[locale] = RSSFeedGenerator(
                feed_title=title,
                feed_link=feed_link,
                feed_description=description,
                language=language,
            )

        logger.info(f"Initialized generators for locales: {list(self.generators.keys())}")

    def _get_generator(self, locale: str) -> RSSFeedGenerator:
        """
        Get the RSS feed generator for a specific locale.

        Args:
            locale: Locale code (e.g., "en-us", "it-it")

        Returns:
            RSSFeedGenerator instance for the locale

        Raises:
            ValueError: If locale is not supported
        """
        if locale not in self.generators:
            raise ValueError(
                f"Unsupported locale: {locale}. "
                f"Supported locales: {list(self.generators.keys())}"
            )
        return self.generators[locale]

    async def get_feed_by_locale(self, locale: str, limit: int = 50) -> str:
        """
        Get RSS feed XML for a specific locale.

        Fetches the latest articles for the given locale and generates
        a localized RSS feed. Results are cached for performance.

        Args:
            locale: Locale code (e.g., "en-us", "it-it")
            limit: Maximum number of articles to include

        Returns:
            RSS 2.0 XML string with locale-specific feed

        Raises:
            ValueError: If locale is not supported
        """
        # Validate locale
        generator = self._get_generator(locale)

        cache_key = f"feed_v2_locale_{locale}_{limit}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached feed for locale {locale}")
            return str(cached)

        # Fetch articles from database for this locale
        articles = await self.repository.get_latest_by_locale(locale=locale, limit=limit)

        # Generate feed URL
        feed_url = f"{settings.base_url}/rss/{locale}.xml"

        # Generate feed
        feed_xml = generator.generate_feed(articles, feed_url)

        # Cache the result
        self.cache.set(cache_key, feed_xml)

        logger.info(f"Generated feed for locale {locale} with {len(articles)} articles")

        return feed_xml

    async def get_feed_by_source_and_locale(
        self, source_id: str, locale: str, limit: int = 50
    ) -> str:
        """
        Get RSS feed for a specific source and locale.

        Filters articles by source ID and locale, generating a localized
        RSS feed for that specific source.

        Args:
            source_id: Source identifier (e.g., "lol", "u-gg")
            locale: Locale code (e.g., "en-us", "it-it")
            limit: Maximum number of articles to include

        Returns:
            RSS 2.0 XML string with source and locale filtered feed

        Raises:
            ValueError: If locale is not supported
        """
        # Validate locale
        generator = self._get_generator(locale)

        cache_key = f"feed_v2_source_{source_id}_{locale}_{limit}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached feed for source {source_id}, locale {locale}")
            return str(cached)

        # Fetch articles by locale first
        articles = await self.repository.get_latest_by_locale(locale=locale, limit=limit)

        # Filter by source pattern (source LIKE 'source_id:%')
        filtered_articles = [
            a for a in articles if a.source.source_id == source_id and a.source.locale == locale
        ]

        # Generate feed URL
        feed_url = f"{settings.base_url}/rss/{source_id}/{locale}.xml"

        # Create source for title modification
        source = ArticleSource.create(source_id, locale)

        # Generate feed with source-specific title
        feed_xml = generator.generate_feed_by_source(filtered_articles, source, feed_url)

        # Cache the result
        self.cache.set(cache_key, feed_xml)

        logger.info(
            f"Generated feed for source {source_id}, locale {locale} "
            f"with {len(filtered_articles)} articles"
        )

        return feed_xml

    async def get_feed_by_category_and_locale(
        self, category: str, locale: str, limit: int = 50
    ) -> str:
        """
        Get RSS feed for a specific category and locale.

        Filters articles by category and locale, generating a localized
        RSS feed for that specific category.

        Args:
            category: Category name to filter by (e.g., "official_riot", "analytics")
            locale: Locale code (e.g., "en-us", "it-it")
            limit: Maximum number of articles to include

        Returns:
            RSS 2.0 XML string with category and locale filtered feed

        Raises:
            ValueError: If locale is not supported
        """
        # Validate locale
        generator = self._get_generator(locale)

        cache_key = f"feed_v2_category_{category}_{locale}_{limit}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached feed for category {category}, locale {locale}")
            return str(cached)

        # Fetch articles by locale and category
        articles = await self.repository.get_latest_by_locale(
            locale=locale, source_category=category, limit=limit
        )

        # Generate feed URL
        feed_url = f"{settings.base_url}/rss/{category}/{locale}.xml"

        # Generate feed with category-specific title
        # Use generate_feed_by_source_category() since DB already filtered by source_category
        feed_xml = generator.generate_feed_by_source_category(articles, category, feed_url)

        # Cache the result
        self.cache.set(cache_key, feed_xml)

        logger.info(
            f"Generated feed for category {category}, locale {locale} "
            f"with {len(articles)} articles"
        )

        return feed_xml

    async def get_available_locales(self) -> list[str]:
        """
        Get list of available locales that have articles.

        Returns:
            List of locale codes that have at least one article
        """
        return await self.repository.get_locales()

    def get_supported_locales(self) -> list[str]:
        """
        Get list of all supported locales.

        Returns:
            List of all locale codes that can be requested
        """
        if isinstance(self.supported_locales, list):
            return self.supported_locales
        # Handle case where supported_locales might be parsed from string
        return list(self.supported_locales) if self.supported_locales else []

    def invalidate_cache(self) -> None:
        """
        Invalidate all feed caches.

        Clears all cached feeds. Should be called after updating
        articles in the database to ensure feeds reflect the latest data.
        """
        self.cache.clear()
        logger.info("FeedServiceV2 cache invalidated")
