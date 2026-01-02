"""
Base scraper interface and configuration for all news source scrapers.

This module defines the abstract base class that all scrapers must implement,
along with configuration dataclasses and difficulty enums. The base scraper
provides common functionality like HTTP client management, rate limiting,
and user agent handling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from src.models import Article, ArticleSource
from src.utils.circuit_breaker import (
    CircuitBreakerConfig,
    get_circuit_breaker_registry,
)

logger = logging.getLogger(__name__)


class ScrapingDifficulty(str, Enum):
    """
    Classification of scraping difficulty for news sources.

    Attributes:
        EASY: Sources with structured RSS feeds or simple HTML parsing
        MEDIUM: Sources with dynamic content requiring additional processing
        HARD: Sources requiring JavaScript execution or anti-scraping measures
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(frozen=True)
class ScrapingConfig:
    """
    Configuration for a news source scraper.

    Attributes:
        source_id: Unique identifier for the source (e.g., "dexerto", "inven")
        base_url: Base URL for the source
        difficulty: Scraping difficulty level
        rate_limit_seconds: Minimum delay between requests to this source
        timeout_seconds: HTTP request timeout in seconds
        user_agent: Custom user agent string (uses default if None)
        rss_feed_url: Optional RSS feed URL if different from base
        requires_selenium: Whether this source requires Selenium for scraping
        requires_playwright: Whether this source requires Playwright for scraping
    """

    source_id: str
    base_url: str
    difficulty: ScrapingDifficulty
    rate_limit_seconds: float = 1.0
    timeout_seconds: int = 30
    user_agent: str | None = None
    rss_feed_url: str | None = None
    requires_selenium: bool = False
    requires_playwright: bool = False

    def get_feed_url(self, locale: str = "en-us") -> str:
        """
        Get the full feed URL for this source.

        Args:
            locale: Locale code for localized feed URLs

        Returns:
            Full URL to fetch articles from
        """
        if self.rss_feed_url:
            return self.rss_feed_url
        return self.base_url

    def get_user_agent(self) -> str:
        """
        Get the user agent string for requests.

        Returns:
            User agent string to use in HTTP headers
        """
        if self.user_agent:
            return self.user_agent
        return self._default_user_agent()

    @staticmethod
    def _default_user_agent() -> str:
        """
        Get the default user agent string.

        Returns:
            Default user agent identifying this as a legitimate RSS aggregator
        """
        return (
            "Mozilla/5.0 (compatible; LoLStonksRSS/1.0; "
            "+https://github.com/OneStepAt4time/lolstonksrss)"
        )


class BaseScraper(ABC):
    """
    Abstract base class for all news source scrapers.

    All scrapers must implement the fetch_articles and parse_article methods.
    The base class provides common functionality for HTTP requests, HTML
    fetching, and error handling.

    Scrapers are designed to be locale-aware and return Article objects
    with proper source categorization and canonical URL deduplication.
    """

    def __init__(self, config: ScrapingConfig, locale: str = "en-us") -> None:
        """
        Initialize the scraper with configuration and locale.

        Args:
            config: Scraping configuration for this source
            locale: Locale code for articles (e.g., "en-us", "ko-kr")
        """
        self.config = config
        self.locale = locale
        self._last_fetch_time: float = 0
        self._client: httpx.AsyncClient | None = None

        # Get circuit breaker for this source
        registry = get_circuit_breaker_registry()
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=900.0,  # 15 minutes
            retry_attempts=3,
        )
        self._circuit_breaker = registry.get(config.source_id, config=cb_config)

    @property
    def client(self) -> httpx.AsyncClient:
        """
        Get or create the HTTP client for this scraper.

        Returns:
            Async HTTP client with configured timeout and user agent

        Raises:
            RuntimeError: If client is accessed outside of async context
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                headers={
                    "User-Agent": self.config.get_user_agent(),
                    "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": f"{self.locale},en-US;q=0.7,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                },
                follow_redirects=True,
            )
        return self._client

    @abstractmethod
    async def fetch_articles(self) -> list[Article]:
        """
        Fetch articles from the configured source.

        This method must be implemented by each scraper type. It should
        return a list of Article objects with all required fields populated,
        including locale, source_category, and canonical_url.

        Returns:
            List of Article objects fetched from the source

        Raises:
            httpx.HTTPStatusError: If HTTP request fails
            Exception: For other scraping errors
        """
        pass

    @abstractmethod
    async def parse_article(self, element: Any) -> Article | None:
        """
        Parse a single article element into an Article object.

        This method must be implemented by each scraper type. The element
        type depends on the scraper (RSS entry, HTML element, etc.).

        Args:
            element: Raw article element to parse

        Returns:
            Article object if parsing succeeds, None otherwise
        """
        pass

    async def _fetch_html(self, url: str) -> str:
        """
        Fetch HTML content from a URL with rate limiting.

        This method respects the configured rate limit by checking the
        last fetch time and sleeping if necessary.

        Args:
            url: URL to fetch HTML from

        Returns:
            Raw HTML content as string

        Raises:
            httpx.HTTPStatusError: If HTTP request fails with non-2xx status
            httpx.TimeoutException: If request times out
        """
        await self._respect_rate_limit()
        response = await self.client.get(url)
        response.raise_for_status()
        self._last_fetch_time = asyncio.get_event_loop().time()
        return response.text

    async def _fetch_json(self, url: str) -> dict[str, Any]:
        """
        Fetch JSON content from a URL with rate limiting.

        Args:
            url: URL to fetch JSON from

        Returns:
            Parsed JSON as dictionary

        Raises:
            httpx.HTTPStatusError: If HTTP request fails
            ValueError: If response is not valid JSON
        """
        await self._respect_rate_limit()
        response = await self.client.get(url)
        response.raise_for_status()
        self._last_fetch_time = asyncio.get_event_loop().time()
        return response.json()  # type: ignore[no-any-return]

    async def _respect_rate_limit(self) -> None:
        """
        Sleep if necessary to respect the configured rate limit.

        Calculates the time since the last request and sleeps if it's
        less than the configured rate_limit_seconds.
        """
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_fetch_time
        if time_since_last < self.config.rate_limit_seconds:
            sleep_time = self.config.rate_limit_seconds - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {self.config.source_id}")
            await asyncio.sleep(sleep_time)

    def _create_article(
        self,
        title: str,
        url: str,
        pub_date: datetime | None,
        description: str = "",
        image_url: str | None = None,
        author: str = "",
        categories: list[str] | None = None,
        content: str = "",
    ) -> Article:
        """
        Create an Article object with standard metadata.

        Helper method to create Article objects with consistent metadata
        including source, locale, and canonical URL.

        Args:
            title: Article title
            url: Article URL
            pub_date: Publication date (None if unknown)
            description: Article description/summary
            image_url: URL to featured image
            author: Article author
            categories: List of category tags
            content: Full article content

        Returns:
            Article object with all metadata populated
        """
        # Generate GUID from URL (canonical deduplication)
        guid = self._generate_guid(url)

        # Create source with proper locale
        source = ArticleSource.create(self.config.source_id, self.locale)

        return Article(
            title=title,
            url=url,
            pub_date=pub_date or datetime.utcnow(),
            guid=guid,
            source=source,
            description=description,
            content=content,
            image_url=image_url,
            author=author or source.name,
            categories=categories or [],
            locale=self.locale,
            source_category=source.category.value,
            canonical_url=url,
        )

    @staticmethod
    def _generate_guid(url: str) -> str:
        """
        Generate a GUID from an article URL.

        Creates a consistent GUID from the URL for deduplication.
        Uses SHA256 hash for collision resistance.

        Args:
            url: Article URL

        Returns:
            Hexadecimal GUID string
        """
        import hashlib

        return hashlib.sha256(url.encode()).hexdigest()

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """
        Parse a date string into a datetime object.

        Attempts multiple common date formats. Returns None if parsing fails.

        Args:
            date_str: Date string to parse

        Returns:
            Datetime object if parsing succeeds, None otherwise
        """
        if not date_str:
            return None

        from email.utils import parsedate_to_datetime

        try:
            # Try RFC 2822 format first (common in RSS)
            return parsedate_to_datetime(date_str)
        except (TypeError, ValueError):
            pass

        # Try ISO 8601 format
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Failed to parse date: {date_str}")
        return None

    async def __aenter__(self) -> "BaseScraper":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit - close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"{self.__class__.__name__}({self.config.source_id!r}, {self.locale!r})"
