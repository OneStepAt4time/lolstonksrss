"""
Unit tests for HTML scraper module.

Tests the HTMLScraper class including:
- HTML fetching with BeautifulSoup parsing
- Article extraction from structured HTML
- CSS selector-based field extraction
- URL conversion to absolute paths
- Error handling for HTTP errors
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
from bs4 import BeautifulSoup, Tag

from src.scrapers.base import ScrapingConfig, ScrapingDifficulty
from src.scrapers.html import HTMLScraper

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def html_config() -> ScrapingConfig:
    """Create a test HTML scraping config."""
    return ScrapingConfig(
        source_id="dexerto",  # Known source with HTML scraping support
        base_url="https://dexerto.com",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=1.0,
    )


@pytest.fixture
def sample_html_content() -> str:
    """Create sample HTML content with articles."""
    return """
    <html>
        <body>
            <article class="post">
                <h2><a href="https://dexerto.com/article1">Test Article 1</a></h2>
                <p class="excerpt">This is the first article description.</p>
                <img src="https://dexerto.com/image1.jpg" />
                <time datetime="2025-01-01T12:00:00Z">Jan 1, 2025</time>
            </article>
            <article class="post">
                <h2><a href="https://dexerto.com/article2">Test Article 2</a></h2>
                <p class="excerpt">This is the second article description.</p>
                <img src="https://dexerto.com/image2.jpg" />
                <time datetime="2025-01-02T12:00:00Z">Jan 2, 2025</time>
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_article_element() -> Tag:
    """Create a sample article element as BeautifulSoup Tag."""
    html = """
    <article class="post">
        <h2><a href="https://dexerto.com/article1">Test Article 1</a></h2>
        <p class="excerpt">This is the first article description.</p>
        <img src="https://dexerto.com/image1.jpg" />
        <time datetime="2025-01-01T12:00:00Z">Jan 1, 2025</time>
    </article>
    """
    return BeautifulSoup(html, "html.parser").find("article")


# =============================================================================
# HTML Scraper Initialization Tests
# =============================================================================


class TestHTMLScraperInit:
    """Tests for HTMLScraper initialization."""

    def test_init_with_config(self, html_config: ScrapingConfig) -> None:
        """Test creating HTMLScraper with config."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        assert scraper.config == html_config
        assert scraper.locale == "en-us"

    def test_init_with_different_locale(self, html_config: ScrapingConfig) -> None:
        """Test creating HTMLScraper with different locale."""
        scraper = HTMLScraper(config=html_config, locale="it-it")
        assert scraper.locale == "it-it"


# =============================================================================
# Get Selectors Tests
# =============================================================================


class TestGetSelectors:
    """Tests for _get_selectors method."""

    def test_get_selectors_known_source(self, html_config: ScrapingConfig) -> None:
        """Test getting selectors for known source."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
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
            source_id="unknown-source",
            base_url="https://example.com",
            difficulty=ScrapingDifficulty.MEDIUM,
        )
        scraper = HTMLScraper(config=config, locale="en-us")
        selectors = scraper._get_selectors()
        # Should return default selectors
        assert "article" in selectors
        assert "title" in selectors


# =============================================================================
# Extract Title Tests
# =============================================================================


class TestExtractTitle:
    """Tests for _extract_title method."""

    def test_extract_title_from_link(self, html_config: ScrapingConfig) -> None:
        """Test extracting title from anchor tag within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<article><h2><a href="/article">Test Title</a></h2></article>'
        element = BeautifulSoup(html, "html.parser").article
        title = scraper._extract_title(element, "h2 a")
        assert title == "Test Title"

    def test_extract_title_direct_text(self, html_config: ScrapingConfig) -> None:
        """Test extracting title directly from heading within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><h2>Test Title</h2></article>"
        element = BeautifulSoup(html, "html.parser").article
        title = scraper._extract_title(element, "h2")
        assert title == "Test Title"

    def test_extract_title_missing(self, html_config: ScrapingConfig) -> None:
        """Test extracting missing title returns empty string."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><div>No title here</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        title = scraper._extract_title(element, "h2 a")
        assert title == ""


# =============================================================================
# Extract URL Tests
# =============================================================================


class TestExtractURL:
    """Tests for _extract_url method."""

    def test_extract_url_from_anchor(self, html_config: ScrapingConfig) -> None:
        """Test extracting URL from anchor tag."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<a href="/article">Link</a>'
        element = BeautifulSoup(html, "html.parser").a
        url = scraper._extract_url(element, "a[href]")
        assert url == "/article"

    def test_extract_url_from_element(self, html_config: ScrapingConfig) -> None:
        """Test extracting URL when element itself is anchor."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<a href="/article">Link</a>'
        element = BeautifulSoup(html, "html.parser").a
        url = scraper._extract_url(element, "a")
        assert url == "/article"

    def test_extract_url_nested_anchor(self, html_config: ScrapingConfig) -> None:
        """Test extracting URL from nested anchor."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<div><a href="/article">Link</a></div>'
        element = BeautifulSoup(html, "html.parser").div
        url = scraper._extract_url(element, "a[href]")
        assert url == "/article"

    def test_extract_url_missing(self, html_config: ScrapingConfig) -> None:
        """Test extracting missing URL returns empty string."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<div>No link here</div>"
        element = BeautifulSoup(html, "html.parser").div
        url = scraper._extract_url(element, "a[href]")
        assert url == ""


# =============================================================================
# Extract Description Tests
# =============================================================================


class TestExtractDescription:
    """Tests for _extract_description method."""

    def test_extract_description_from_paragraph(self, html_config: ScrapingConfig) -> None:
        """Test extracting description from paragraph within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<article><p class="excerpt">This is a description.</p></article>'
        element = BeautifulSoup(html, "html.parser").article
        desc = scraper._extract_description(element, ".excerpt")
        assert desc == "This is a description."

    def test_extract_description_missing(self, html_config: ScrapingConfig) -> None:
        """Test extracting missing description returns empty string."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><div>No description</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        desc = scraper._extract_description(element, ".excerpt")
        assert desc == ""

    def test_extract_description_none_selector(self, html_config: ScrapingConfig) -> None:
        """Test extracting description with None selector."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><div>Content</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        desc = scraper._extract_description(element, None)
        assert desc == ""


# =============================================================================
# Extract Date Tests
# =============================================================================


class TestExtractDate:
    """Tests for _extract_date method."""

    def test_extract_date_from_datetime_attr(self, html_config: ScrapingConfig) -> None:
        """Test extracting date from datetime attribute within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<article><time datetime="2025-01-01T12:00:00Z">Jan 1, 2025</time></article>'
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, "time")
        assert date is not None
        assert isinstance(date, datetime)

    def test_extract_date_from_text(self, html_config: ScrapingConfig) -> None:
        """Test extracting date from text content within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<article><span class="date">2025-01-01 12:00:00</span></article>'
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, ".date")
        assert date is not None

    def test_extract_date_missing(self, html_config: ScrapingConfig) -> None:
        """Test extracting missing date returns None."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><div>No date</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, ".date")
        assert date is None

    def test_extract_date_none_selector(self, html_config: ScrapingConfig) -> None:
        """Test extracting date with None selector."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><div>Content</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        date = scraper._extract_date(element, None)
        assert date is None


# =============================================================================
# Extract Image Tests
# =============================================================================


class TestExtractImage:
    """Tests for _extract_image method."""

    def test_extract_image_from_src(self, html_config: ScrapingConfig) -> None:
        """Test extracting image URL from src attribute within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<article><img src="https://example.com/image.jpg" /></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "img")
        assert url == "https://example.com/image.jpg"

    def test_extract_image_from_data_src(self, html_config: ScrapingConfig) -> None:
        """Test extracting image URL from data-src attribute within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<article><img data-src="https://example.com/image.jpg" /></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "img")
        assert url == "https://example.com/image.jpg"

    def test_extract_image_from_style(self, html_config: ScrapingConfig) -> None:
        """Test extracting image URL from background-image style within article."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = '<article><div style="background-image: url(https://example.com/bg.jpg);"></div></article>'
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "div")
        assert url == "https://example.com/bg.jpg"

    def test_extract_image_missing(self, html_config: ScrapingConfig) -> None:
        """Test extracting missing image returns None."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><div>No image</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, "div")
        assert url is None

    def test_extract_image_none_selector(self, html_config: ScrapingConfig) -> None:
        """Test extracting image with None selector."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><div>Content</div></article>"
        element = BeautifulSoup(html, "html.parser").article
        url = scraper._extract_image(element, None)
        assert url is None


# =============================================================================
# Make Absolute URL Tests
# =============================================================================


class TestMakeAbsolute:
    """Tests for _make_absolute method."""

    def test_make_absolute_already_absolute(self, html_config: ScrapingConfig) -> None:
        """Test URL that's already absolute."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        url = "https://example.com/article"
        assert scraper._make_absolute(url) == url

    def test_make_absolute_relative(self, html_config: ScrapingConfig) -> None:
        """Test converting relative URL to absolute."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        url = "/article"
        absolute = scraper._make_absolute(url)
        assert absolute == "https://dexerto.com/article"

    def test_make_absolute_relative_subpath(self, html_config: ScrapingConfig) -> None:
        """Test converting relative subpath URL to absolute."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        url = "news/article"
        absolute = scraper._make_absolute(url)
        assert absolute == "https://dexerto.com/news/article"

    def test_make_absolute_empty(self, html_config: ScrapingConfig) -> None:
        """Test empty URL returns empty string."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        assert scraper._make_absolute("") == ""


# =============================================================================
# Parse Article Tests
# =============================================================================


class TestParseArticle:
    """Tests for parse_article method."""

    @pytest.mark.asyncio
    async def test_parse_article_success(
        self, html_config: ScrapingConfig, sample_article_element: Tag
    ) -> None:
        """Test successful article parsing."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        article = await scraper.parse_article(sample_article_element)

        assert article is not None
        assert article.title == "Test Article 1"
        assert "article1" in article.url
        assert article.description == "This is the first article description."

    @pytest.mark.asyncio
    async def test_parse_article_missing_title(self, html_config: ScrapingConfig) -> None:
        """Test parsing element without title returns None."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        html = "<article><p>No title</p></article>"
        element = BeautifulSoup(html, "html.parser").article
        article = await scraper.parse_article(element)
        assert article is None

    @pytest.mark.asyncio
    async def test_parse_article_none_element(self, html_config: ScrapingConfig) -> None:
        """Test parsing None element returns None."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        article = await scraper.parse_article(None)
        assert article is None

    @pytest.mark.asyncio
    async def test_parse_article_non_tag_element(self, html_config: ScrapingConfig) -> None:
        """Test parsing non-Tag element returns None."""
        scraper = HTMLScraper(config=html_config, locale="en-us")
        article = await scraper.parse_article("not a tag")
        assert article is None


# =============================================================================
# Fetch Articles Tests
# =============================================================================


class TestFetchArticles:
    """Tests for fetch_articles method."""

    @pytest.mark.asyncio
    async def test_fetch_articles_success(
        self, html_config: ScrapingConfig, sample_html_content: str
    ) -> None:
        """Test successful article fetching from HTML."""
        scraper = HTMLScraper(config=html_config, locale="en-us")

        # Mock _fetch_html to return sample HTML
        async def mock_fetch_html(url: str) -> str:
            return sample_html_content

        with patch.object(scraper, "_fetch_html", mock_fetch_html):
            articles = await scraper.fetch_articles()

        assert len(articles) == 2
        assert articles[0].title == "Test Article 1"
        assert articles[1].title == "Test Article 2"

    @pytest.mark.asyncio
    async def test_fetch_articles_empty_html(self, html_config: ScrapingConfig) -> None:
        """Test handling HTML with no articles."""
        scraper = HTMLScraper(config=html_config, locale="en-us")

        async def mock_fetch_html(url: str) -> str:
            return "<html><body><p>No articles here</p></body></html>"

        with patch.object(scraper, "_fetch_html", mock_fetch_html):
            articles = await scraper.fetch_articles()

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_fetch_articles_http_error(self, html_config: ScrapingConfig) -> None:
        """Test handling HTTP error during HTML fetch."""
        scraper = HTMLScraper(config=html_config, locale="en-us")

        mock_response = MagicMock()
        mock_response.status_code = 404

        async def mock_fetch_error(url: str) -> str:
            raise httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

        with patch.object(scraper, "_fetch_html", mock_fetch_error):
            with pytest.raises(httpx.HTTPStatusError):
                await scraper.fetch_articles()


# =============================================================================
# Clean Text Tests
# =============================================================================


class TestCleanText:
    """Tests for _clean_text static method."""

    def test_clean_text_normalizes_whitespace(self) -> None:
        """Test that whitespace is normalized."""
        assert HTMLScraper._clean_text("  Multiple   spaces  ") == "Multiple spaces"

    def test_clean_text_newlines(self) -> None:
        """Test that newlines are handled."""
        result = HTMLScraper._clean_text("Line1\n\n  Line2")
        assert "Line1" in result and "Line2" in result

    def test_clean_text_empty(self) -> None:
        """Test empty string returns empty string."""
        assert HTMLScraper._clean_text("") == ""

    def test_clean_text_none(self) -> None:
        """Test None returns empty string."""
        assert HTMLScraper._clean_text(None) == ""
