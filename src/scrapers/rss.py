"""
RSS scraper for sites with structured RSS/Atom feeds.

This module implements a scraper for sites that provide RSS or Atom feeds.
It uses the feedparser library to parse feeds and extract article information.
RSS scrapers are classified as "EASY" difficulty sources.
"""

import logging
from datetime import datetime
from typing import Any

import feedparser
import httpx

from src.models import Article
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RSSScraper(BaseScraper):
    """
    Scraper for sites providing RSS or Atom feeds.

    This scraper handles structured RSS/Atom feeds using the feedparser library.
    It extracts article metadata including title, description, publication date,
    author, categories, and images from feed entries.

    RSS feeds are the easiest to scrape as they provide structured data in
    a standard format. Most major news sites and blogs provide RSS feeds.

    Example sources:
        - Dexerto (community news hub)
        - Dot Esports (esports news)
        - Upcomer (gaming news)
        - Various regional sites
    """

    async def fetch_articles(self) -> list[Article]:
        """
        Fetch and parse articles from an RSS feed.

        Downloads the RSS feed from the configured URL, parses it using
        feedparser, and converts entries to Article objects.
        Uses circuit breaker for resilience.

        Returns:
            List of Article objects parsed from the feed

        Raises:
            httpx.HTTPStatusError: If feed request fails
            Exception: If feed parsing fails
        """
        feed_url = self.config.get_feed_url(self.locale)
        logger.info(f"[{self.config.source_id}:{self.locale}] Fetching RSS feed from {feed_url}")

        # Wrap the fetch operation with circuit breaker
        async def _fetch_feed() -> bytes:
            await self._respect_rate_limit()
            response = await self.client.get(feed_url)
            response.raise_for_status()
            return response.content

        try:
            # Fetch feed content with circuit breaker protection
            response_content = await self._circuit_breaker.call(_fetch_feed)

            # Parse RSS feed
            feed = feedparser.parse(response_content)

            if feed.bozo:
                logger.warning(
                    f"Feed parsing warning for {self.config.source_id}: {feed.bozo_exception}"
                )

            # Extract articles from feed entries
            articles = []
            max_entries = 100  # Limit to avoid overwhelming

            for entry in feed.entries[:max_entries]:
                try:
                    article = await self.parse_article(entry)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(
                        f"[{self.config.source_id}:{self.locale}] Failed to parse entry: {e}"
                    )
                    continue

            logger.info(f"[{self.config.source_id}:{self.locale}] Fetched {len(articles)} articles")
            return articles

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[{self.config.source_id}:{self.locale}] HTTP error "
                f"{e.response.status_code} fetching feed: {e}"
            )
            raise
        except Exception as e:
            logger.error(
                f"[{self.config.source_id}:{self.locale}] Error fetching articles: {e}",
                exc_info=True,
            )
            raise

    async def parse_article(self, element: Any) -> Article | None:
        """
        Parse a single RSS feed entry into an Article object.

        Extracts all available metadata from the feed entry including:
        - Title (required)
        - URL/link (required)
        - Description/summary
        - Publication date
        - Author
        - Categories/tags
        - Enclosure (featured image)
        - Content (full article HTML)

        Args:
            element: Feedparser entry object

        Returns:
            Article object if parsing succeeds, None if required fields missing
        """
        if not element:
            return None

        # Extract required fields
        title = self._extract_title(element)
        url = self._extract_url(element)

        if not title or not url:
            logger.debug("Skipping entry: missing title or URL")
            return None

        # Extract optional fields
        description = self._extract_description(element)
        pub_date = self._extract_pub_date(element)
        author = self._extract_author(element)
        categories = self._extract_categories(element)
        image_url = self._extract_image(element)
        content = self._extract_content(element)

        # Create and return Article
        return self._create_article(
            title=title,
            url=url,
            pub_date=pub_date,
            description=description,
            image_url=image_url,
            author=author,
            categories=categories,
            content=content,
        )

    def _extract_title(self, entry: Any) -> str:
        """
        Extract title from feed entry.

        Args:
            entry: Feedparser entry object

        Returns:
            Title string or empty string if not found
        """
        return str(entry.get("title", "").strip())

    def _extract_url(self, entry: Any) -> str:
        """
        Extract URL from feed entry.

        Handles multiple URL field names used by different feed formats.

        Args:
            entry: Feedparser entry object

        Returns:
            URL string or empty string if not found
        """
        # Try standard link field
        if "link" in entry:
            return str(entry["link"])

        # Try id field (sometimes contains URL)
        if "id" in entry and str(entry["id"]).startswith("http"):
            return str(entry["id"])

        # Try links array (Atom format)
        if "links" in entry:
            for link in entry["links"]:
                if link.get("rel") == "alternate" or link.get("type") == "text/html":
                    return str(link.get("href", ""))

        return ""

    def _extract_description(self, entry: Any) -> str:
        """
        Extract description/summary from feed entry.

        Args:
            entry: Feedparser entry object

        Returns:
            Description string, cleaned of HTML tags
        """
        # Try description field
        if "description" in entry:
            return self._clean_html(entry["description"])

        # Try summary field
        if "summary" in entry:
            return self._clean_html(entry["summary"])

        # Try subtitle
        if "subtitle" in entry:
            return self._clean_html(entry["subtitle"])

        return ""

    def _extract_pub_date(self, entry: Any) -> datetime | None:
        """
        Extract publication date from feed entry.

        Args:
            entry: Feedparser entry object

        Returns:
            Datetime object or None if date cannot be parsed
        """
        # Try various date field names
        date_fields = ["published", "updated", "created", "pubDate"]

        for field in date_fields:
            if field in entry:
                parsed = self._parse_date(entry[field])
                if parsed:
                    return parsed

        # Try timestamp_parsed (feedparser's parsed timestamp)
        if "published_parsed" in entry and entry["published_parsed"]:
            try:
                return datetime(*entry["published_parsed"][:6])
            except (TypeError, ValueError):
                pass

        return None

    def _extract_author(self, entry: Any) -> str:
        """
        Extract author from feed entry.

        Args:
            entry: Feedparser entry object

        Returns:
            Author name or empty string
        """
        # Try author field
        if "author" in entry:
            author = entry["author"]
            if isinstance(author, str):
                return author
            if isinstance(author, dict) and "name" in author:
                return author["name"]  # type: ignore

        # Try author_detail
        if "author_detail" in entry and entry["author_detail"]:
            return entry["author_detail"].get("name", "")  # type: ignore

        return ""

    def _extract_categories(self, entry: Any) -> list[str]:
        """
        Extract categories/tags from feed entry.

        Args:
            entry: Feedparser entry object

        Returns:
            List of category strings
        """
        categories = []

        # Try tags field
        if "tags" in entry:
            for tag in entry["tags"]:
                if isinstance(tag, str):
                    categories.append(tag)
                elif isinstance(tag, dict):
                    term = tag.get("term") or tag.get("label")
                    if term:
                        categories.append(term)

        # Try category field
        if "category" in entry:
            category = entry["category"]
            if isinstance(category, str):
                categories.append(category)
            elif isinstance(category, list):
                categories.extend(category)

        return categories

    def _extract_image(self, entry: Any) -> str | None:
        """
        Extract featured image URL from feed entry.

        Checks for image enclosures, media:content tags, and img tags.

        Args:
            entry: Feedparser entry object

        Returns:
            Image URL string or None if not found
        """
        # Try enclosures (RSS media enclosures)
        if "enclosures" in entry:
            for enclosure in entry["enclosures"]:
                if str(enclosure.get("type", "")).startswith("image/"):
                    return str(enclosure.get("href", ""))

        # Try media_content (Media RSS extension)
        if "media_content" in entry:
            for media in entry["media_content"]:
                if media.get("medium") == "image":
                    return str(media.get("url", ""))

        # Try image from content/description
        description = self._extract_description(entry)
        if description:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(description, "html.parser")
            img = soup.find("img")
            if img and img.get("src"):
                return str(img["src"])

        return None

    def _extract_content(self, entry: Any) -> str:
        """
        Extract full content from feed entry.

        Args:
            entry: Feedparser entry object

        Returns:
            Full content HTML or empty string
        """
        # Try content field
        if "content" in entry:
            content_list = entry["content"]
            if content_list and isinstance(content_list, list):
                # content is often a list of dicts with 'value' key
                return str(content_list[0].get("value", ""))

        # Try summary if content not available
        if "summary" in entry:
            return str(entry["summary"])

        # Try description
        if "description" in entry:
            return str(entry["description"])

        return ""

    @staticmethod
    def _clean_html(html: str) -> str:
        """
        Clean HTML by removing tags but preserving text.

        Args:
            html: HTML string

        Returns:
            Plain text with HTML tags removed
        """
        if not html:
            return ""

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ", strip=True)
