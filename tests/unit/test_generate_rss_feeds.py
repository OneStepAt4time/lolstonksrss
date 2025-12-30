"""
Unit tests for the RSS feeds generator script.

Tests the RSS feed generation functionality for GitHub Pages deployment,
including feed generation, validation, and command-line argument parsing.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.generate_rss_feeds import (
    FEED_CONFIGS,
    create_feed_generators,
    generate_feeds,
    parse_arguments,
    validate_feeds,
)
from src.models import Article, ArticleSource


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles for testing."""
    return [
        Article(
            title="New Champion Release: Briar",
            url="https://www.leagueoflegends.com/news/champion-briar",
            pub_date=datetime(2025, 12, 28, 10, 0, 0, tzinfo=timezone.utc),
            guid="article-champion-briar",
            source=ArticleSource.LOL_EN_US,
            description="A new champion is coming to the Rift",
            content="<p>Full article content about the new champion Briar</p>",
            image_url="https://images.contentstack.io/champion.jpg",
            author="Riot Games",
            categories=["Champions", "News"],
        ),
        Article(
            title="Patch Notes 14.1",
            url="https://www.leagueoflegends.com/news/patch-14-1",
            pub_date=datetime(2025, 12, 27, 15, 30, 0, tzinfo=timezone.utc),
            guid="article-patch-14-1",
            source=ArticleSource.LOL_EN_US,
            description="Latest patch notes for Season 2025",
            categories=["Patches", "Game Updates"],
        ),
        Article(
            title="Arcane Season 2 Announced",
            url="https://www.leagueoflegends.com/news/arcane-season-2",
            pub_date=datetime(2025, 12, 26, 8, 0, 0, tzinfo=timezone.utc),
            guid="article-arcane-s2",
            source=ArticleSource.LOL_IT_IT,
            description="Arcane returns with a new season",
            content="<p>The Emmy-award winning series returns</p>",
            image_url="https://images.contentstack.io/arcane.jpg",
            author="Riot Games",
            categories=["Esports", "Entertainment"],
        ),
    ]


class TestCreateFeedGenerators:
    """Test feed generator creation."""

    def test_creates_english_generator(self) -> None:
        """Test that English generator is created with correct config."""
        generators = create_feed_generators()

        assert "en" in generators
        en_generator = generators["en"]
        assert en_generator.feed_title == "League of Legends News"
        assert en_generator.language == "en"
        assert "leagueoflegends.com/news" in en_generator.feed_link

    def test_creates_italian_generator(self) -> None:
        """Test that Italian generator is created with correct config."""
        generators = create_feed_generators()

        assert "it" in generators
        it_generator = generators["it"]
        assert it_generator.feed_title == "Notizie League of Legends"
        assert it_generator.language == "it"
        assert "leagueoflegends.com/it-it/news" in it_generator.feed_link

    def test_creates_multiple_generators(self) -> None:
        """Test that multiple generators are created."""
        generators = create_feed_generators()

        assert len(generators) >= 2
        assert "en" in generators
        assert "it" in generators


class TestGenerateFeeds:
    """Test the generate_feeds async function."""

    @pytest.mark.asyncio
    async def test_generate_feeds_creates_all_feeds(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test that all configured feeds are generated."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            # Setup mocks
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            # Generate feeds
            feeds = await generate_feeds(output_dir=tmp_path, limit=100)

            # Verify all feeds were generated
            assert len(feeds) == 3
            assert (tmp_path / "feed.xml").exists()
            assert (tmp_path / "feed" / "en-us.xml").exists()
            assert (tmp_path / "feed" / "it-it.xml").exists()

    @pytest.mark.asyncio
    async def test_generate_feeds_respects_limit(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test that article limit is passed to repository."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            await generate_feeds(output_dir=tmp_path, limit=50)

            # Verify limit was passed to get_latest calls
            # Each feed config calls get_latest, so check total calls
            assert mock_repo.get_latest.call_count == len(FEED_CONFIGS)
            # Check at least one call used the limit
            calls = mock_repo.get_latest.call_args_list
            assert any(call.kwargs.get("limit") == 50 for call in calls)

    @pytest.mark.asyncio
    async def test_generate_feeds_with_custom_base_url(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test feed generation with custom base URL."""
        custom_url = "https://custom.example.com"

        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            feeds = await generate_feeds(output_dir=tmp_path, limit=100, base_url=custom_url)

            # Check that feeds contain the custom URL
            feed_content = (tmp_path / "feed.xml").read_text(encoding="utf-8")
            assert custom_url in feed_content

    @pytest.mark.asyncio
    async def test_generate_feeds_filters_by_source(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test that language-specific feeds filter by source."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            await generate_feeds(output_dir=tmp_path, limit=100)

            # Verify source-specific calls were made
            calls = mock_repo.get_latest.call_args_list
            # Check that some calls included source parameter
            source_calls = [call for call in calls if "source" in call.kwargs]
            assert len(source_calls) > 0

    @pytest.mark.asyncio
    async def test_generate_feeds_creates_subdirectories(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test that feed subdirectories are created."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            await generate_feeds(output_dir=tmp_path, limit=100)

            # Verify feed subdirectory was created
            assert (tmp_path / "feed").exists()
            assert (tmp_path / "feed").is_dir()

    @pytest.mark.asyncio
    async def test_generate_feeds_returns_file_sizes(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test that generate_feeds returns dictionary with file sizes."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            feeds = await generate_feeds(output_dir=tmp_path, limit=100)

            # Check return value structure
            assert isinstance(feeds, dict)
            assert len(feeds) > 0

            # Each entry should map path to size
            for path, size in feeds.items():
                assert isinstance(path, str)
                assert isinstance(size, int)
                assert size > 0

    @pytest.mark.asyncio
    async def test_generate_feeds_with_empty_database(self, tmp_path: Path) -> None:
        """Test feed generation when database is empty."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = []

            # Should not raise error even with empty database
            feeds = await generate_feeds(output_dir=tmp_path, limit=100)

            # Feeds should still be created (empty but valid)
            assert len(feeds) == 3
            assert (tmp_path / "feed.xml").exists()

    @pytest.mark.asyncio
    async def test_generate_feeds_handles_database_error(self, tmp_path: Path) -> None:
        """Test error handling when database query fails."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.side_effect = Exception("Database connection failed")

            # Should raise exception
            with pytest.raises(Exception, match="Database connection failed"):
                await generate_feeds(output_dir=tmp_path, limit=100)

    @pytest.mark.asyncio
    async def test_generate_feeds_handles_directory_creation_error(
        self, sample_articles: list[Article]
    ) -> None:
        """Test error handling when output directory cannot be created."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            # Try to create feed in invalid location (empty string causes issues)
            with pytest.raises(OSError):
                # Use a path that will fail on mkdir
                with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
                    await generate_feeds(output_dir="/invalid/path", limit=100)

    @pytest.mark.asyncio
    async def test_generate_feeds_closes_repository(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test that repository is properly closed after generation."""
        with patch("scripts.generate_rss_feeds.get_settings") as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            await generate_feeds(output_dir=tmp_path, limit=100)

            # Verify repository was closed
            mock_repo.close.assert_called_once()


class TestValidateFeeds:
    """Test the validate_feeds function."""

    def test_validate_feeds_with_valid_feeds(self, tmp_path: Path) -> None:
        """Test validation of properly formatted RSS feeds."""
        # Create valid RSS feeds
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <link>https://example.com</link>
        <description>Test Description</description>
    </channel>
</rss>"""

        feed_path = tmp_path / "test.xml"
        feed_path.write_text(feed_xml, encoding="utf-8")

        feeds = {str(feed_path): feed_path.stat().st_size}
        result = validate_feeds(feeds)

        assert result is True

    def test_validate_feeds_with_missing_file(self) -> None:
        """Test validation when feed file doesn't exist."""
        feeds = {"/nonexistent/feed.xml": 1000}
        result = validate_feeds(feeds)

        assert result is False

    def test_validate_feeds_with_empty_file(self, tmp_path: Path) -> None:
        """Test validation of empty feed file."""
        feed_path = tmp_path / "empty.xml"
        feed_path.write_text("", encoding="utf-8")

        feeds = {str(feed_path): 0}
        result = validate_feeds(feeds)

        assert result is False

    def test_validate_feeds_missing_rss_tag(self, tmp_path: Path) -> None:
        """Test validation when RSS tag is missing."""
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<channel>
    <title>Invalid Feed</title>
</channel>"""

        feed_path = tmp_path / "invalid.xml"
        feed_path.write_text(feed_xml, encoding="utf-8")

        feeds = {str(feed_path): feed_path.stat().st_size}
        result = validate_feeds(feeds)

        assert result is False

    def test_validate_feeds_missing_channel_tag(self, tmp_path: Path) -> None:
        """Test validation when channel tag is missing."""
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <title>No Channel</title>
</rss>"""

        feed_path = tmp_path / "no_channel.xml"
        feed_path.write_text(feed_xml, encoding="utf-8")

        feeds = {str(feed_path): feed_path.stat().st_size}
        result = validate_feeds(feeds)

        assert result is False

    def test_validate_feeds_multiple_feeds(self, tmp_path: Path) -> None:
        """Test validation of multiple feeds."""
        # Create multiple valid feeds
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
    </channel>
</rss>"""

        feeds = {}
        for i in range(3):
            feed_path = tmp_path / f"feed{i}.xml"
            feed_path.write_text(feed_xml, encoding="utf-8")
            feeds[str(feed_path)] = feed_path.stat().st_size

        result = validate_feeds(feeds)
        assert result is True

    def test_validate_feeds_mixed_valid_invalid(self, tmp_path: Path) -> None:
        """Test validation with mix of valid and invalid feeds."""
        # Create one valid feed
        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Valid Feed</title>
    </channel>
</rss>"""

        # Create one invalid feed (no RSS tag)
        invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
<channel>
    <title>Invalid Feed</title>
</channel>"""

        valid_path = tmp_path / "valid.xml"
        valid_path.write_text(valid_xml, encoding="utf-8")

        invalid_path = tmp_path / "invalid.xml"
        invalid_path.write_text(invalid_xml, encoding="utf-8")

        feeds = {
            str(valid_path): valid_path.stat().st_size,
            str(invalid_path): invalid_path.stat().st_size,
        }

        result = validate_feeds(feeds)
        assert result is False


class TestParseArguments:
    """Test command-line argument parsing."""

    def test_parse_arguments_defaults(self) -> None:
        """Test that default arguments are set correctly."""
        with patch("sys.argv", ["generate_rss_feeds.py"]):
            args = parse_arguments()

            assert args.output == "_site"
            assert args.limit == 50
            assert args.base_url is None
            assert args.no_validate is False
            assert args.verbose is False

    def test_parse_arguments_custom_output(self) -> None:
        """Test parsing custom output directory."""
        with patch("sys.argv", ["generate_rss_feeds.py", "--output", "custom_dir"]):
            args = parse_arguments()

            assert args.output == "custom_dir"

    def test_parse_arguments_short_output(self) -> None:
        """Test parsing output with short flag."""
        with patch("sys.argv", ["generate_rss_feeds.py", "-o", "short_dir"]):
            args = parse_arguments()

            assert args.output == "short_dir"

    def test_parse_arguments_custom_limit(self) -> None:
        """Test parsing custom article limit."""
        with patch("sys.argv", ["generate_rss_feeds.py", "--limit", "100"]):
            args = parse_arguments()

            assert args.limit == 100

    def test_parse_arguments_short_limit(self) -> None:
        """Test parsing limit with short flag."""
        with patch("sys.argv", ["generate_rss_feeds.py", "-l", "200"]):
            args = parse_arguments()

            assert args.limit == 200

    def test_parse_arguments_custom_base_url(self) -> None:
        """Test parsing custom base URL."""
        with patch("sys.argv", ["generate_rss_feeds.py", "--base-url", "https://example.com"]):
            args = parse_arguments()

            assert args.base_url == "https://example.com"

    def test_parse_arguments_short_base_url(self) -> None:
        """Test parsing base URL with short flag."""
        with patch("sys.argv", ["generate_rss_feeds.py", "-b", "https://test.com"]):
            args = parse_arguments()

            assert args.base_url == "https://test.com"

    def test_parse_arguments_no_validate_flag(self) -> None:
        """Test parsing no-validate flag."""
        with patch("sys.argv", ["generate_rss_feeds.py", "--no-validate"]):
            args = parse_arguments()

            assert args.no_validate is True

    def test_parse_arguments_verbose_flag(self) -> None:
        """Test parsing verbose flag."""
        with patch("sys.argv", ["generate_rss_feeds.py", "--verbose"]):
            args = parse_arguments()

            assert args.verbose is True

    def test_parse_arguments_short_verbose_flag(self) -> None:
        """Test parsing verbose flag with short version."""
        with patch("sys.argv", ["generate_rss_feeds.py", "-v"]):
            args = parse_arguments()

            assert args.verbose is True

    def test_parse_arguments_combined_flags(self) -> None:
        """Test parsing multiple arguments together."""
        with patch(
            "sys.argv",
            [
                "generate_rss_feeds.py",
                "-o",
                "public",
                "-l",
                "150",
                "-b",
                "https://example.com",
                "--no-validate",
                "-v",
            ],
        ):
            args = parse_arguments()

            assert args.output == "public"
            assert args.limit == 150
            assert args.base_url == "https://example.com"
            assert args.no_validate is True
            assert args.verbose is True


class TestMainFunction:
    """Test the main entry point and error handling."""

    def test_main_with_invalid_limit_too_low(self, tmp_path: Path) -> None:
        """Test that main exits with error when limit is too low."""
        with patch("sys.argv", ["generate_rss_feeds.py", "--limit", "0"]), patch(
            "sys.exit"
        ) as mock_exit:
            from scripts.generate_rss_feeds import main

            main()

            # Should exit with error code
            mock_exit.assert_called_with(1)

    def test_main_caps_limit_at_500(self, sample_articles: list[Article]) -> None:
        """Test that main caps limit at 500 articles."""
        # Use a directory within project root to avoid relative_to issues
        output_dir = "_site/test_output"
        with patch("sys.argv", ["generate_rss_feeds.py", "--limit", "1000", "-o", output_dir]), patch(
            "scripts.generate_rss_feeds.get_settings"
        ) as mock_settings, patch("scripts.generate_rss_feeds.ArticleRepository") as mock_repo_class:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            from scripts.generate_rss_feeds import main

            try:
                main()
            except SystemExit:
                # main() calls sys.exit(0) on success, which is expected
                pass

            # Verify limit was capped at 500
            calls = mock_repo.get_latest.call_args_list
            for call in calls:
                limit = call.kwargs.get("limit", 50)
                assert limit <= 500

    def test_main_with_invalid_output_directory(self) -> None:
        """Test main exits when output directory cannot be created."""
        with patch("sys.argv", ["generate_rss_feeds.py", "-o", "/invalid/path"]), patch(
            "pathlib.Path.mkdir", side_effect=OSError("Permission denied")
        ), patch("sys.exit") as mock_exit:
            from scripts.generate_rss_feeds import main

            main()

            # Should exit with error code - first call is the one we care about
            assert mock_exit.called
            assert mock_exit.call_args_list[0][0][0] == 1

    def test_main_keyboard_interrupt(self, tmp_path: Path) -> None:
        """Test main handles keyboard interrupt gracefully."""
        with patch("sys.argv", ["generate_rss_feeds.py", "-o", str(tmp_path)]), patch(
            "scripts.generate_rss_feeds.asyncio.run", side_effect=KeyboardInterrupt()
        ), patch("sys.exit") as mock_exit:
            from scripts.generate_rss_feeds import main

            main()

            # Should exit with code 1
            mock_exit.assert_called_with(1)

    def test_main_validation_failure(
        self, tmp_path: Path, sample_articles: list[Article]
    ) -> None:
        """Test main exits when feed validation fails."""
        with patch("sys.argv", ["generate_rss_feeds.py", "-o", str(tmp_path)]), patch(
            "scripts.generate_rss_feeds.get_settings"
        ) as mock_settings, patch(
            "scripts.generate_rss_feeds.ArticleRepository"
        ) as mock_repo_class, patch(
            "scripts.generate_rss_feeds.validate_feeds", return_value=False
        ), patch(
            "sys.exit"
        ) as mock_exit:
            mock_settings.return_value.database_path = "test.db"
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_latest.return_value = sample_articles

            from scripts.generate_rss_feeds import main

            main()

            # Should exit with code 1 due to validation failure
            mock_exit.assert_called_with(1)
