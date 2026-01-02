"""
Selenium scraper for JavaScript-heavy and dynamic content sites.

This module implements a scraper for sites that require JavaScript execution
to render content, such as Single Page Applications (SPAs) and sites with
heavy client-side rendering. Selenium scrapers are classified as "HARD" difficulty.

Note: Selenium requires Chrome/Chromium to be installed on the system.
"""

import logging
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.models import Article
from src.scrapers.base import BaseScraper, ScrapingConfig

logger = logging.getLogger(__name__)


class SeleniumScraper(BaseScraper):
    """
    Scraper for sites requiring JavaScript execution.

    This scraper uses Selenium WebDriver to control a headless Chrome browser,
    allowing it to scrape sites that require JavaScript for content rendering.

    Selenium scrapers are the most complex because:
    - Require browser driver installation and configuration
    - Slower than HTTP-based scraping
    - Higher resource usage (memory/CPU)
    - More prone to breaking with browser updates
    - May need to handle dynamic content loading

    Example sources:
        - Social media sites (Twitter/X, Reddit)
        - YouTube channels
        - Sites with infinite scroll
        - Sites with heavy anti-scraping measures

    Note:
        This scraper requires Chrome or Chromium to be installed.
        For Docker deployments, ensure ChromeDriver is available.
    """

    # CSS selectors for sources requiring Selenium
    SELECTORS: dict[str, dict[str, str]] = {
        "twitter": {
            "article": 'article[data-testid="tweet"]',
            "title": "div[lang]",
            "url": 'a[href*="/status/"]',
            "description": "div[lang]",
            "image": "img",
            "date": "time",
        },
        "reddit": {
            "article": "div[data-testid='post-container']",
            "title": "h3, a[data-click-id='body']",
            "url": "a[data-click-id='comments']",
            "description": "div[data-testid='post-content']",
            "image": "img",
            "date": "time",
        },
        "youtube": {
            "article": "ytd-grid-video-renderer, ytd-video-renderer",
            "title": "#video-title",
            "url": "a#video-title",
            "description": "#description-text",
            "image": "img",
            "date": "#metadata-line span",
        },
        "discord": {
            "article": ".message, .container",
            "title": ".header, .username",
            "url": "a[href]",
            "description": ".message-content",
            "image": "img",
            "date": ".timestamp",
        },
        "u-gg": {
            "article": "article, .news-item, .article-card",
            "title": "h2, h3, .title, a[class*='title']",
            "url": "a[href]",
            "description": ".excerpt, .summary, .description, p",
            "image": "img[src], img[data-src]",
            "date": "time, .date, .timestamp, [datetime]",
        },
        "lolesports": {
            "article": "article, .news-item, .article-card, .story-card",
            "title": "h2, h3, .title, a[class*='title']",
            "url": "a[href]",
            "description": ".excerpt, .summary, .description, p",
            "image": "img[src], img[data-src]",
            "date": "time, .date, .timestamp, [datetime]",
        },
    }

    def __init__(self, config: ScrapingConfig, locale: str = "en-us") -> None:
        """
        Initialize the Selenium scraper.

        Args:
            config: Scraping configuration
            locale: Locale code for articles
        """
        super().__init__(config, locale)
        self._driver: webdriver.Chrome | None = None
        self._driver_initialized = False

    async def fetch_articles(self) -> list[Article]:
        """
        Fetch and parse articles using Selenium WebDriver.

        Launches a headless browser, navigates to the URL, waits for
        content to load, and extracts articles using CSS selectors.

        Returns:
            List of Article objects parsed from the page

        Raises:
            WebDriverException: If browser initialization fails
            TimeoutException: If page loading times out
            Exception: For other scraping errors
        """
        url = self.config.get_feed_url(self.locale)
        logger.info(f"Fetching with Selenium from {url}")

        try:
            # Initialize driver
            await self._init_driver()
            assert self._driver is not None  # Driver initialized

            # Navigate to URL
            self._driver.get(url)

            # Wait for page to load
            await self._wait_for_page_load()

            # Get page HTML
            assert self._driver is not None  # Driver still valid
            html = self._driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Get selectors for this source
            selectors = self._get_selectors()

            # Find all article elements
            article_selector = selectors["article"]
            article_elements = soup.select(article_selector)

            if not article_elements:
                logger.warning(
                    f"No article elements found with selector '{article_selector}' "
                    f"for {self.config.source_id}"
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
                        f"Failed to parse article element from {self.config.source_id}: {e}"
                    )
                    continue

            logger.info(f"Fetched {len(articles)} articles from {self.config.source_id}")
            return articles

        except TimeoutException as e:
            logger.error(f"Timeout waiting for page load: {e}")
            raise
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching articles from {self.config.source_id}: {e}")
            raise
        finally:
            await self._cleanup_driver()

    async def parse_article(self, element: Any) -> Article | None:
        """
        Parse a single HTML element into an Article object.

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

    async def _init_driver(self) -> None:
        """
        Initialize the Selenium WebDriver.

        Configures Chrome with headless mode and appropriate options
        for server environments.

        Raises:
            WebDriverException: If driver initialization fails
        """
        if self._driver_initialized and self._driver:
            return

        logger.debug("Initializing Selenium WebDriver")

        options = ChromeOptions()

        # Headless mode
        options.add_argument("--headless=new")

        # Stability options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")

        # Performance options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")  # If site allows
        options.add_argument("--blink-settings=imagesEnabled=false")

        # User agent
        options.add_argument(f"--user-agent={self.config.get_user_agent()}")

        # Window size (some sites require minimum size)
        options.add_argument("--window-size=1920,1080")

        # Language
        options.add_argument(f"--lang={self.locale}")
        options.add_experimental_option("prefs", {"intl.accept_languages": self.locale})

        try:
            # Try to use system Chrome/Chromium
            self._driver = webdriver.Chrome(options=options)
            self._driver_initialized = True
            logger.debug("Selenium WebDriver initialized successfully")
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise WebDriverException(
                "Selenium requires Chrome/Chromium to be installed. "
                "For Docker, install chromium and chromium-driver."
            ) from e

    async def _wait_for_page_load(self, timeout: int = 10) -> None:
        """
        Wait for the page to fully load.

        Waits for either body element or configured article elements to
        be present in the DOM.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            TimeoutException: If page doesn't load within timeout
        """
        if not self._driver:
            raise WebDriverException("Driver not initialized")

        selectors = self._get_selectors()
        wait = WebDriverWait(self._driver, timeout)

        try:
            # Wait for article elements to appear
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors["article"])))
            logger.debug("Page loaded: article elements found")
        except TimeoutException:
            # Fall back to waiting for body
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                logger.debug("Page loaded: body element found")
            except TimeoutException:
                logger.warning("Page load timeout, proceeding anyway")
                # Don't raise - let caller handle empty results

        # Additional wait for dynamic content
        time.sleep(1)

    async def _cleanup_driver(self) -> None:
        """Cleanup and close the WebDriver."""
        if self._driver:
            try:
                self._driver.quit()
                logger.debug("WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self._driver = None
                self._driver_initialized = False

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
            "article": "article, .post, .news-item, .item",
            "title": "h2 a, h3 a, h2, h3, .title",
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
        link_elem = element.select_one(selector)
        if link_elem and link_elem.get("href"):
            return str(link_elem["href"])

        if element.name == "a" and element.get("href"):
            return str(element["href"])

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

        if date_elem.get("datetime"):
            return self._parse_date(str(date_elem["datetime"]))

        if date_elem.name == "time" and date_elem.get("datetime"):
            return self._parse_date(str(date_elem["datetime"]))

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

        if img_elem.get("src"):
            return str(img_elem["src"])

        if img_elem.get("data-src"):
            return str(img_elem["data-src"])

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

        if urlparse(url).scheme in ("http", "https"):
            return url

        return urljoin(self.config.base_url, url)

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit - cleanup driver."""
        await super().__aexit__(exc_type, exc_val, exc_tb)
        await self._cleanup_driver()

    async def close(self) -> None:
        """Close resources including WebDriver."""
        await super().close()
        await self._cleanup_driver()
