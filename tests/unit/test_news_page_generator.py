"""
Unit tests for the news page generator.

Tests the HTML news page generation functionality including template
rendering, article formatting, and file generation.
"""

import re
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scripts.generate_news_page import (
    extract_unique_values,
    fetch_articles,
    generate_news_page,
)
from src.models import Article, ArticleSource


class TestExtractUniqueValues:
    """Test extraction of unique sources and categories."""

    def test_extract_from_empty_list(self) -> None:
        """Test extraction from empty article list."""
        sources, categories = extract_unique_values([])
        assert sources == []
        assert categories == []

    def test_extract_from_single_article(self) -> None:
        """Test extraction from single article."""
        articles = [
            {
                "source": "lol-en-us",
                "categories": ["Champions", "Media"],
            }
        ]
        sources, categories = extract_unique_values(articles)
        assert sources == ["lol-en-us"]
        assert set(categories) == {"Champions", "Media"}

    def test_extract_from_multiple_articles(self) -> None:
        """Test extraction with duplicate sources and categories."""
        articles = [
            {"source": "lol-en-us", "categories": ["Champions", "Media"]},
            {"source": "lol-it-it", "categories": ["Media", "Esports"]},
            {"source": "lol-en-us", "categories": ["Champions"]},
        ]
        sources, categories = extract_unique_values(articles)
        assert set(sources) == {"lol-en-us", "lol-it-it"}
        assert set(categories) == {"Champions", "Media", "Esports"}

    def test_extract_with_string_categories(self) -> None:
        """Test extraction when categories are comma-separated strings."""
        articles = [
            {"source": "lol-en-us", "categories": "Champions,Media,Esports"},
        ]
        sources, categories = extract_unique_values(articles)
        assert sources == ["lol-en-us"]
        assert set(categories) == {"Champions", "Media", "Esports"}

    def test_extract_with_missing_fields(self) -> None:
        """Test extraction with missing source or categories."""
        articles = [
            {"source": "lol-en-us"},  # No categories
            {"categories": ["Media"]},  # No source
        ]
        sources, categories = extract_unique_values(articles)
        assert sources == ["lol-en-us"]
        assert categories == ["Media"]


class TestFetchArticles:
    """Test article fetching and formatting."""

    @pytest.mark.asyncio
    async def test_fetch_articles_empty_database(self) -> None:
        """Test fetching from empty database."""
        mock_repo = AsyncMock()
        mock_repo.get_latest.return_value = []

        articles = await fetch_articles(mock_repo, 10)

        assert articles == []
        mock_repo.get_latest.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_fetch_articles_formats_dates(self) -> None:
        """Test that publication dates are formatted correctly."""
        # Create mock article
        article = Article(
            title="Test Article",
            url="https://example.com/article",
            pub_date=datetime(2024, 1, 15, 14, 30, 0),
            guid="test-guid-123",
            source=ArticleSource.LOL_EN_US,
            description="Test description",
            categories=["Champions", "Media"],
        )

        mock_repo = AsyncMock()
        mock_repo.get_latest.return_value = [article]

        articles = await fetch_articles(mock_repo, 10)

        assert len(articles) == 1
        assert "pub_date_formatted" in articles[0]
        assert "January 15, 2024" in articles[0]["pub_date_formatted"]

    @pytest.mark.asyncio
    async def test_fetch_articles_converts_categories_string(self) -> None:
        """Test that category strings are converted to lists."""
        article = Article(
            title="Test Article",
            url="https://example.com/article",
            pub_date=datetime.utcnow(),
            guid="test-guid-123",
            source=ArticleSource.LOL_EN_US,
            categories=["Champions", "Media"],
        )

        mock_repo = AsyncMock()
        mock_repo.get_latest.return_value = [article]

        articles = await fetch_articles(mock_repo, 10)

        assert len(articles) == 1
        assert isinstance(articles[0]["categories"], list)
        assert set(articles[0]["categories"]) == {"Champions", "Media"}


class TestGenerateNewsPage:
    """Test the complete news page generation."""

    @pytest.mark.asyncio
    async def test_generate_creates_html_file(self, tmp_path: Path) -> None:
        """Test that HTML file is created successfully."""
        output_file = tmp_path / "test_news.html"

        # Mock the repository and settings
        with patch("scripts.generate_news_page.get_settings") as mock_settings, patch(
            "scripts.generate_news_page.ArticleRepository"
        ) as mock_repo_class:
            # Setup mock settings
            mock_settings.return_value.database_path = "test.db"

            # Setup mock repository
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # Create test article
            article = Article(
                title="Test Article",
                url="https://example.com/test",
                pub_date=datetime.utcnow(),
                guid="test-123",
                source=ArticleSource.LOL_EN_US,
                description="Test description",
                categories=["Champions"],
            )

            mock_repo.get_latest.return_value = [article]

            # Generate page
            await generate_news_page(str(output_file), limit=50)

            # Verify file was created
            assert output_file.exists()
            assert output_file.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_generate_with_no_articles(self, tmp_path: Path) -> None:
        """Test generation when database is empty."""
        output_file = tmp_path / "empty_news.html"

        with patch("scripts.generate_news_page.get_settings") as mock_settings, patch(
            "scripts.generate_news_page.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = []

            # Should not raise error even with no articles
            await generate_news_page(str(output_file), limit=50)

            assert output_file.exists()

    @pytest.mark.asyncio
    async def test_generate_respects_limit(self, tmp_path: Path) -> None:
        """Test that article limit is respected."""
        output_file = tmp_path / "limited_news.html"

        with patch("scripts.generate_news_page.get_settings") as mock_settings, patch(
            "scripts.generate_news_page.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = []

            await generate_news_page(str(output_file), limit=25)

            # Verify limit was passed to repository
            mock_repo.get_latest.assert_called_once_with(limit=25)

    @pytest.mark.asyncio
    async def test_generate_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that parent directories are created if they don't exist."""
        output_file = tmp_path / "nested" / "dir" / "news.html"

        with patch("scripts.generate_news_page.get_settings") as mock_settings, patch(
            "scripts.generate_news_page.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = []

            await generate_news_page(str(output_file), limit=50)

            assert output_file.exists()
            assert output_file.parent.exists()

    @pytest.mark.asyncio
    async def test_generate_contains_required_elements(self, tmp_path: Path) -> None:
        """Test that generated HTML contains required elements."""
        output_file = tmp_path / "full_news.html"

        with patch("scripts.generate_news_page.get_settings") as mock_settings, patch(
            "scripts.generate_news_page.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            article = Article(
                title="Test Article Title",
                url="https://example.com/test",
                pub_date=datetime.utcnow(),
                guid="test-123",
                source=ArticleSource.LOL_EN_US,
                description="Test description for article",
                categories=["Champions", "Media"],
            )

            mock_repo.get_latest.return_value = [article]

            await generate_news_page(str(output_file), limit=50)

            # Read and verify content
            content = output_file.read_text(encoding="utf-8")

            # Check for required HTML structure
            assert "<!DOCTYPE html>" in content
            assert "<html" in content
            assert "LoL Stonks RSS" in content
            assert "League of Legends" in content

            # Check for article content
            assert "Test Article Title" in content
            assert "https://example.com/test" in content
            assert "Test description for article" in content

            # Check for interactive elements
            assert "searchBox" in content
            assert "filterArticles" in content
            assert "toggleTheme" in content

            # Check for LoL branding colors
            assert "#C89B3C" in content  # LoL gold
            assert "#0AC8B9" in content  # LoL blue


class TestHTMLValidation:
    """Test HTML validation and structure."""

    @pytest.mark.asyncio
    async def test_html_is_valid_structure(self, tmp_path: Path) -> None:
        """Test that generated HTML has valid structure."""
        output_file = tmp_path / "valid_news.html"

        with patch("scripts.generate_news_page.get_settings") as mock_settings, patch(
            "scripts.generate_news_page.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = []

            await generate_news_page(str(output_file), limit=50)

            content = output_file.read_text(encoding="utf-8")

            # Basic HTML validation using regex to handle attributes
            # Count opening tags that may have attributes: <html>, <html lang="en">, etc.
            html_open_count = len(re.findall(r"<html[\s>]", content))
            html_close_count = len(re.findall(r"</html>", content))
            assert (
                html_open_count == html_close_count
            ), f"HTML tag mismatch: {html_open_count} opening, {html_close_count} closing"

            head_open_count = len(re.findall(r"<head[\s>]", content))
            head_close_count = len(re.findall(r"</head>", content))
            assert (
                head_open_count == head_close_count
            ), f"HEAD tag mismatch: {head_open_count} opening, {head_close_count} closing"

            body_open_count = len(re.findall(r"<body[\s>]", content))
            body_close_count = len(re.findall(r"</body>", content))
            assert (
                body_open_count == body_close_count
            ), f"BODY tag mismatch: {body_open_count} opening, {body_close_count} closing"

            # Check for meta tags
            assert '<meta charset="UTF-8">' in content
            assert '<meta name="viewport"' in content
            assert '<meta http-equiv="refresh" content="300">' in content

    @pytest.mark.asyncio
    async def test_responsive_meta_tags(self, tmp_path: Path) -> None:
        """Test that responsive design meta tags are present."""
        output_file = tmp_path / "responsive_news.html"

        with patch("scripts.generate_news_page.get_settings") as mock_settings, patch(
            "scripts.generate_news_page.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = []

            await generate_news_page(str(output_file), limit=50)

            content = output_file.read_text(encoding="utf-8")

            # Check for responsive viewport
            assert "width=device-width" in content
            assert "initial-scale=1.0" in content

            # Check for media queries
            assert "@media" in content
