"""
HTML scraper for sites with structured HTML content.

This module implements a scraper for sites that provide structured HTML
but no RSS feed. It uses BeautifulSoup for HTML parsing and CSS selectors
for article extraction. HTML scrapers are classified as "MEDIUM" difficulty.
"""

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from src.models import Article
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class HTMLScraper(BaseScraper):
    """
    Scraper for sites with structured HTML content.

    This scraper handles sites that provide article listings in structured
    HTML format but don't offer RSS feeds. It uses CSS selectors configured
    per source to extract article links and metadata.

    HTML scrapers are more complex than RSS scrapers because:
    - HTML structure varies widely between sites
    - Pagination may need to be handled
    - JavaScript may be required for some content
    - Anti-scraping measures may be present

    Example sources:
        - Dot Esports (esports section)
        - Esports.gg (team news)
        - GGRecon (gaming news)
        - PC Gamer (PC gaming news)
        - Various regional sites
    """

    # CSS selectors for common sources
    # Maps source_id to CSS selectors for article elements
    SELECTORS: dict[str, dict[str, str]] = {
        "dexerto": {
            "article": "article.post",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt, p",
            "image": "img[src]",
            "date": "time, .date",
        },
        "dotesports": {
            "article": "article, .post-item",
            "title": "h2 a, h3 a, .post-title a",
            "url": "a[href]",
            "description": ".excerpt, .post-excerpt",
            "image": "img[src]",
            "date": "time, .post-date",
        },
        "esportsgg": {
            "article": ".article-card, .news-item",
            "title": "h2, h3, .title",
            "url": "a[href]",
            "description": ".excerpt, .summary",
            "image": "img[src]",
            "date": "time, .date",
        },
        "ggrecon": {
            "article": "article, .card",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "nme": {
            "article": "article",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt, p",
            "image": "img[src]",
            "date": "time",
        },
        "pcgamesn": {
            "article": "article",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "thegamer": {
            "article": "article",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "upcomer": {
            "article": "article, .post",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "inven": {
            "article": ".articleList, .news-item",
            "title": "a.title",
            "url": "a[href]",
            "description": ".summary",
            "image": "img[src]",
            "date": ".date, time",
        },
        "opgg": {
            "article": ".news-item, .article",
            "title": "a.title, h3",
            "url": "a[href]",
            "description": ".summary",
            "image": "img[src]",
            "date": "time",
        },
        "3djuegos": {
            "article": "article",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "earlygame": {
            "article": "article",
            "title": "h2 a, h3 a",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "mobalytics": {
            "article": ".blog-post, .article",
            "title": "h2, h3, .title",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "ugg": {
            "article": ".article, .news-item",
            "title": "h2, h3",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "blitz-gg": {
            "article": ".article",
            "title": "h2, h3",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "porofessor": {
            "article": ".article",
            "title": "h2, h3",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "bunnymuffins": {
            "article": ".post, article",
            "title": "h2, h3",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
        "tftactics": {
            "article": ".article, .news",
            "title": "h2, h3",
            "url": "a[href]",
            "description": ".excerpt",
            "image": "img[src]",
            "date": "time",
        },
    }

    async def fetch_articles(self) -> list[Article]:
        """
        Fetch and parse articles from structured HTML.

        Downloads the HTML page, parses it with BeautifulSoup, and extracts
        articles using CSS selectors configured for the source.

        Returns:
            List of Article objects parsed from the HTML

        Raises:
            httpx.HTTPStatusError: If HTTP request fails
            Exception: If HTML parsing fails
        """
        url = self.config.get_feed_url(self.locale)
        logger.info(f"[{self.config.source_id}:{self.locale}] Fetching HTML from {url}")

        try:
            html = await self._fetch_html(url)
            soup = BeautifulSoup(html, "html.parser")

            # Get selectors for this source
            selectors = self._get_selectors()

            # Find all article elements
            article_selector = selectors["article"]
            article_elements = soup.select(article_selector)

            if not article_elements:
                logger.warning(
                    f"[{self.config.source_id}:{self.locale}] No article elements found "
                    f"with selector '{article_selector}'"
                )
                return []

            # Parse each article element
            articles = []
            max_articles = 50  # Limit to avoid overwhelming

            for element in article_elements[:max_articles]:
                try:
                    article = await self.parse_article(element)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(
                        f"[{self.config.source_id}:{self.locale}] Failed to parse article element: {e}"
                    )
                    continue

            logger.info(f"[{self.config.source_id}:{self.locale}] Fetched {len(articles)} articles")
            return articles

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[{self.config.source_id}:{self.locale}] HTTP error "
                f"{e.response.status_code} fetching HTML: {e}"
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
        Parse a single HTML element into an Article object.

        Extracts article metadata using CSS selectors configured for the source.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            Article object if parsing succeeds, None if required fields missing
        """
        if not element or not isinstance(element, Tag):
            return None

        selectors = self._get_selectors()

        # Extract required fields
        title = self._extract_title(element, selectors["title"])
        url = self._extract_url(element, selectors["url"])

        if not title or not url:
            logger.debug("Skipping element: missing title or URL")
            return None

        # Make URL absolute
        url = self._make_absolute(url)

        # Extract optional fields
        description = self._extract_description(element, selectors.get("description"))
        pub_date = self._extract_date(element, selectors.get("date"))
        image_url = self._extract_image(element, selectors.get("image"))

        if image_url:
            image_url = self._make_absolute(image_url)

        # Create and return Article
        return self._create_article(
            title=title,
            url=url,
            pub_date=pub_date,
            description=description,
            image_url=image_url,
        )

    def _get_selectors(self) -> dict[str, str]:
        """
        Get CSS selectors for the current source.

        Returns configured selectors for the source, or defaults if not found.

        Returns:
            Dictionary mapping field names to CSS selectors
        """
        # Get source-specific selectors
        if self.config.source_id in self.SELECTORS:
            return self.SELECTORS[self.config.source_id]

        # Return default selectors
        return {
            "article": "article, .post, .news-item",
            "title": "h2 a, h3 a, h2, h3",
            "url": "a[href]",
            "description": ".excerpt, .summary, p",
            "image": "img",
            "date": "time, .date, .time",
        }

    def _extract_title(self, element: Tag, selector: str) -> str:
        """
        Extract title from element using CSS selector.

        Args:
            element: BeautifulSoup Tag element
            selector: CSS selector for title

        Returns:
            Title string or empty string if not found
        """
        title_elem = element.select_one(selector)
        if title_elem:
            # Prefer text content, then href text for links
            if title_elem.name == "a":
                return title_elem.get_text(strip=True)
            return title_elem.get_text(strip=True)

        return ""

    def _extract_url(self, element: Tag, selector: str) -> str:
        """
        Extract URL from element using CSS selector.

        Args:
            element: BeautifulSoup Tag element
            selector: CSS selector for URL

        Returns:
            URL string or empty string if not found
        """
        # Try to find link element
        link_elem = element.select_one(selector)
        if link_elem and link_elem.get("href"):
            return str(link_elem["href"])

        # Try element itself if it's a link
        if element.name == "a" and element.get("href"):
            return str(element["href"])

        # Try to find first link within element
        link_elem = element.find("a")
        if link_elem and link_elem.get("href"):
            return str(link_elem["href"])

        return ""

    def _extract_description(self, element: Tag, selector: str | None) -> str:
        """
        Extract description from element using CSS selector.

        Args:
            element: BeautifulSoup Tag element
            selector: CSS selector for description

        Returns:
            Description string or empty string if not found
        """
        if not selector:
            return ""

        desc_elem = element.select_one(selector)
        if desc_elem:
            return str(desc_elem.get_text(strip=True))

        return ""

    def _extract_date(self, element: Tag, selector: str | None) -> datetime | None:
        """
        Extract publication date from element using CSS selector.

        Args:
            element: BeautifulSoup Tag element
            selector: CSS selector for date

        Returns:
            Datetime object or None if date cannot be parsed
        """
        if not selector:
            return None

        date_elem = element.select_one(selector)
        if not date_elem:
            return None

        # Try datetime attribute
        if date_elem.get("datetime"):
            return self._parse_date(str(date_elem["datetime"]))

        # Try time datetime
        if date_elem.name == "time" and date_elem.get("datetime"):
            return self._parse_date(str(date_elem["datetime"]))

        # Try text content
        date_text = date_elem.get_text(strip=True)
        if date_text:
            return self._parse_date(str(date_text))

        return None

    def _extract_image(self, element: Tag, selector: str | None) -> str | None:
        """
        Extract image URL from element using CSS selector.

        Args:
            element: BeautifulSoup Tag element
            selector: CSS selector for image

        Returns:
            Image URL string or None if not found
        """
        if not selector:
            return None

        img_elem = element.select_one(selector)
        if not img_elem:
            return None

        # Try src attribute
        if img_elem.get("src"):
            return str(img_elem["src"])

        # Try data-src (lazy loading)
        if img_elem.get("data-src"):
            return str(img_elem["data-src"])

        # Try background-image style
        style = img_elem.get("style", "")
        if isinstance(style, str) and "background-image" in style:
            import re

            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if match:
                return match.group(1)

        return None

    def _make_absolute(self, url: str) -> str:
        """
        Convert relative URL to absolute URL.

        Args:
            url: Relative or absolute URL

        Returns:
            Absolute URL string
        """
        if not url:
            return ""

        # Already absolute
        if urlparse(url).scheme in ("http", "https"):
            return url

        # Make absolute using base URL
        return urljoin(self.config.base_url, url)

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean text by normalizing whitespace.

        Args:
            text: Text to clean

        Returns:
            Cleaned text with normalized whitespace
        """
        if not text:
            return ""
        return " ".join(text.split())
