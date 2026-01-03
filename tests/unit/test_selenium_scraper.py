"""
Unit tests for Selenium scraper module.

Tests the SeleniumScraper class including:
- WebDriver initialization (mocked)
- Article extraction from JavaScript-rendered pages
- CSS selector-based field extraction
- URL conversion to absolute paths
- Error handling for WebDriver and timeout exceptions
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup, Tag
from selenium.common.exceptions import TimeoutException

from src.scrapers.base import ScrapingConfig, ScrapingDifficulty
from src.scrapers.selenium import SeleniumScraper

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def selenium_config() -> ScrapingConfig:
    """Create a test Selenium scraping config."""
    return ScrapingConfig(
        source_id="lolesports",  # Known source with Selenium scraping
        base_url="https://lolesports.com",
        difficulty=ScrapingDifficulty.HARD,
        rate_limit_seconds=1.0,
    )


@pytest.fixture
def sample_selenium_html() -> str:
    """Create sample HTML content from JavaScript-rendered page."""
    return """
    <html>
        <body>
            <article class="news-item">
                <h2><a href="https://lolesports.com/news/article1">Test Article 1</a></h2>
                <p class="excerpt">First article description.</p>
                <img src="https://lolesports.com/img1.jpg" />
                <time datetime="2025-01-01T12:00:00Z">Jan 1</time>
            </article>
            <article class="news-item">
                <h2><a href="https://lolesports.com/news/article2">Test Article 2</a></h2>
                <p class="excerpt">Second article description.</p>
                <img src="https://lolesports.com/img2.jpg" />
                <time datetime="2025-01-02T12:00:00Z">Jan 2</time>
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_article_element() -> Tag:
    """Create a sample article element as BeautifulSoup Tag."""
    html = """
    <article class="news-item">
        <h2><a href="https://lolesports.com/news/article1">Test Article 1</a></h2>
        <p class="excerpt">First article description.</p>
        <img src="https://lolesports.com/img1.jpg" />
        <time datetime="2025-01-01T12:00:00Z">Jan 1</time>
    </article>
    """
    return BeautifulSoup(html, "html.parser").find("article")


# =============================================================================
# Selenium Scraper Initialization Tests
# =============================================================================


class TestSeleniumScraperInit:
    """Tests for SeleniumScraper initialization."""

    def test_init_with_config(self, selenium_config: ScrapingConfig) -> None:
        """Test creating SeleniumScraper with config."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        assert scraper.config == selenium_config
        assert scraper.locale == "en-us"
        assert scraper._driver is None
        assert not scraper._driver_initialized

    def test_init_with_different_locale(self, selenium_config: ScrapingConfig) -> None:
        """Test creating SeleniumScraper with different locale."""
        scraper = SeleniumScraper(config=selenium_config, locale="ko-kr")
        assert scraper.locale == "ko-kr"


# =============================================================================
# Get Selectors Tests
# =============================================================================


class TestGetSelectors:
    """Tests for _get_selectors method."""

    def test_get_selectors_known_source(self, selenium_config: ScrapingConfig) -> None:
        """Test getting selectors for known source."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        selectors = scraper._get_selectors()
        assert "article" in selectors
        assert "title" in selectors
        assert "url" in selectors
        assert "description" in selectors
        assert "image" in selectors
        assert "date" in selectors

    def test_get_selectors_unknown_source(self) -> None:
        """Test getting default selectors for unknown source."""
        config = ScrapingConfig(
            source_id="unknown-selenium-source",
            base_url="https://example.com",
            difficulty=ScrapingDifficulty.HARD,
        )
        scraper = SeleniumScraper(config=config, locale="en-us")
        selectors = scraper._get_selectors()
        # Should return default selectors
        assert "article" in selectors
        assert "title" in selectors


# =============================================================================
# Extract Title Tests
# =============================================================================


class TestExtractTitle:
    """Tests for _extract_title method."""

    def test_extract_title_from_heading(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting title from heading within article."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><h2>Test Title</h2></article>"
        element = BeautifulSoup(html, "html.parser").article
        title = scraper._extract_title(element, "h2")
        assert title == "Test Title"

    def test_extract_title_from_anchor(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting title from anchor within article."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><h2><a href="/news">Test Title</a></h2></article>'
        element = BeautifulSoup(html, "html.parser").article
        title = scraper._extract_title(element, "h2 a")
        assert title == "Test Title"

    def test_extract_title_missing(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting missing title returns empty string."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>No title</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        title = scraper._extract_title(element, "h2")
        assert title == ""


# =============================================================================
# Extract URL Tests
# =============================================================================


class TestExtractURL:
    """Tests for _extract_url method."""

    def test_extract_url_from_anchor(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting URL from anchor within article."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><a href="/news/article">Link</a></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_url(element, "a[href]")
        assert url == "/news/article"

    def test_extract_url_from_nested_anchor(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting URL from nested anchor."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><h2><a href="/article">Title</a></h2></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_url(element, "a[href]")
        assert url == "/article"

    def test_extract_url_missing(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting missing URL returns empty string."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>No link</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_url(element, "a[href]")
        assert url == ""


# =============================================================================
# Extract Description Tests
# =============================================================================


class TestExtractDescription:
    """Tests for _extract_description method."""

    def test_extract_description_from_paragraph(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting description from paragraph."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><p class="excerpt">Test description</p></article>'
        element = BeautifulSoup(html, "html.parser").article
        desc = scraper._extract_description(element, ".excerpt")
        assert desc == "Test description"

    def test_extract_description_missing(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting missing description returns empty string."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>No description</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        desc = scraper._extract_description(element, ".excerpt")
        assert desc == ""

    def test_extract_description_none_selector(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting description with None selector."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>Content</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        desc = scraper._extract_description(element, None)
        assert desc == ""


# =============================================================================
# Extract Date Tests
# =============================================================================


class TestExtractDate:
    """Tests for _extract_date method."""

    def test_extract_date_from_datetime_attr(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting date from datetime attribute."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><time datetime="2025-01-01T12:00:00Z">Jan 1</time></article>'
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, "time")
        assert date is not None
        assert isinstance(date, datetime)

    def test_extract_date_from_text(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting date from text content."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><span class="date">2025-01-01</span></article>'
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, ".date")
        assert date is not None

    def test_extract_date_missing(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting missing date returns None."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>No date</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, ".date")
        assert date is None

    def test_extract_date_none_selector(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting date with None selector."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>Content</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, None)
        assert date is None


# =============================================================================
# Extract Image Tests
# =============================================================================


class TestExtractImage:
    """Tests for _extract_image method."""

    def test_extract_image_from_src(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting image URL from src attribute."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><img src="https://example.com/img.jpg" /></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "img")
        assert url == "https://example.com/img.jpg"

    def test_extract_image_from_data_src(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting image URL from data-src attribute."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><img data-src="https://example.com/img.jpg" /></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "img")
        assert url == "https://example.com/img.jpg"

    def test_extract_image_from_style(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting image URL from background-image style."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = '<article><div style="background-image: url(https://example.com/bg.jpg);"></div></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "div")
        assert url == "https://example.com/bg.jpg"

    def test_extract_image_missing(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting missing image returns None."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>No image</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "div")
        assert url is None

    def test_extract_image_none_selector(self, selenium_config: ScrapingConfig) -> None:
        """Test extracting image with None selector."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><div>Content</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, None)
        assert url is None


# =============================================================================
# Make Absolute URL Tests
# =============================================================================


class TestMakeAbsolute:
    """Tests for _make_absolute method."""

    def test_make_absolute_already_absolute(self, selenium_config: ScrapingConfig) -> None:
        """Test URL that's already absolute."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        url = "https://example.com/article"
        assert scraper._make_absolute(url) == url

    def test_make_absolute_relative(self, selenium_config: ScrapingConfig) -> None:
        """Test converting relative URL to absolute."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        url = "/news/article"
        absolute = scraper._make_absolute(url)
        assert absolute == "https://lolesports.com/news/article"

    def test_make_absolute_empty(self, selenium_config: ScrapingConfig) -> None:
        """Test empty URL returns empty string."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        assert scraper._make_absolute("") == ""


# =============================================================================
# Parse Article Tests
# =============================================================================


class TestParseArticle:
    """Tests for parse_article method."""

    @pytest.mark.asyncio
    async def test_parse_article_success(
        self, selenium_config: ScrapingConfig, sample_article_element: Tag
    ) -> None:
        """Test successful article parsing."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        article = await scraper.parse_article(sample_article_element)

        assert article is not None
        assert article.title == "Test Article 1"
        assert "article1" in article.url
        assert article.description == "First article description."

    @pytest.mark.asyncio
    async def test_parse_article_missing_title(self, selenium_config: ScrapingConfig) -> None:
        """Test parsing element without title returns None."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        html = "<article><p>No title</p></article>"
        element = BeautifulSoup(html, "html.parser").article
        article = await scraper.parse_article(element)
        assert article is None

    @pytest.mark.asyncio
    async def test_parse_article_none_element(self, selenium_config: ScrapingConfig) -> None:
        """Test parsing None element returns None."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        article = await scraper.parse_article(None)
        assert article is None

    @pytest.mark.asyncio
    async def test_parse_article_non_tag_element(self, selenium_config: ScrapingConfig) -> None:
        """Test parsing non-Tag element returns None."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        article = await scraper.parse_article("not a tag")
        assert article is None


# =============================================================================
# Fetch Articles Tests
# =============================================================================


class TestFetchArticles:
    """Tests for fetch_articles method."""

    @pytest.mark.asyncio
    async def test_fetch_articles_success(
        self, selenium_config: ScrapingConfig, sample_selenium_html: str
    ) -> None:
        """Test successful article fetching from JavaScript-rendered page."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")

        # Mock the driver and methods
        mock_driver = MagicMock()
        mock_driver.page_source = sample_selenium_html

        # Mock _init_driver to set up our mock driver
        async def mock_init_driver() -> None:
            scraper._driver = mock_driver
            scraper._driver_initialized = True

        # Mock _wait_for_page_load
        async def mock_wait() -> None:
            pass

        # Mock _cleanup_driver
        async def mock_cleanup() -> None:
            scraper._driver = None
            scraper._driver_initialized = False

        with patch.object(scraper, "_init_driver", mock_init_driver):
            with patch.object(scraper, "_wait_for_page_load", mock_wait):
                with patch.object(scraper, "_cleanup_driver", mock_cleanup):
                    articles = await scraper.fetch_articles()

        assert len(articles) == 2
        assert articles[0].title == "Test Article 1"
        assert articles[1].title == "Test Article 2"

    @pytest.mark.asyncio
    async def test_fetch_articles_no_articles(self, selenium_config: ScrapingConfig) -> None:
        """Test handling HTML with no articles."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body><p>No articles</p></body></html>"

        async def mock_init_driver() -> None:
            scraper._driver = mock_driver
            scraper._driver_initialized = True

        async def mock_wait() -> None:
            pass

        async def mock_cleanup() -> None:
            scraper._driver = None
            scraper._driver_initialized = False

        with patch.object(scraper, "_init_driver", mock_init_driver):
            with patch.object(scraper, "_wait_for_page_load", mock_wait):
                with patch.object(scraper, "_cleanup_driver", mock_cleanup):
                    articles = await scraper.fetch_articles()

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_fetch_articles_timeout(self, selenium_config: ScrapingConfig) -> None:
        """Test handling timeout during page load."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")

        async def mock_init_driver() -> None:
            scraper._driver = MagicMock()
            scraper._driver_initialized = True

        async def mock_wait() -> None:
            raise TimeoutException("Page load timeout")

        async def mock_cleanup() -> None:
            scraper._driver = None
            scraper._driver_initialized = False

        with patch.object(scraper, "_init_driver", mock_init_driver):
            with patch.object(scraper, "_wait_for_page_load", mock_wait):
                with patch.object(scraper, "_cleanup_driver", mock_cleanup):
                    with pytest.raises(TimeoutException):
                        await scraper.fetch_articles()


# =============================================================================
# Cleanup Driver Tests
# =============================================================================


class TestCleanupDriver:
    """Tests for _cleanup_driver method."""

    @pytest.mark.asyncio
    async def test_cleanup_driver_closes_driver(self, selenium_config: ScrapingConfig) -> None:
        """Test that cleanup closes and nulls the driver."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")

        # Set up a mock driver
        mock_driver = MagicMock()
        scraper._driver = mock_driver
        scraper._driver_initialized = True

        await scraper._cleanup_driver()

        assert scraper._driver is None
        assert not scraper._driver_initialized
        mock_driver.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_driver_no_driver(self, selenium_config: ScrapingConfig) -> None:
        """Test cleanup when no driver exists."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")
        scraper._driver = None
        scraper._driver_initialized = False

        # Should not raise
        await scraper._cleanup_driver()

        assert scraper._driver is None


# =============================================================================
# Close Tests
# =============================================================================


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_calls_cleanup(self, selenium_config: ScrapingConfig) -> None:
        """Test that close calls cleanup_driver."""
        scraper = SeleniumScraper(config=selenium_config, locale="en-us")

        mock_driver = MagicMock()
        scraper._driver = mock_driver
        scraper._driver_initialized = True

        await scraper.close()

        assert scraper._driver is None
        assert not scraper._driver_initialized
