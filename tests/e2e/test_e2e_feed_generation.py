"""
End-to-End RSS Feed Generation Tests

This module runs comprehensive tests on RSS feed generation for both
FeedService (legacy) and FeedServiceV2 (new multi-locale).

Tests cover:
- Feed generation for all supported locales
- Feed validation with feedparser
- Locale-specific metadata validation
- Source and category filtering
- RSS 2.0 compliance
"""

from datetime import datetime, timezone
from pathlib import Path

import feedparser
import pytest

from src.config import get_settings
from src.database import ArticleRepository
from src.models import Article, ArticleSource
from src.rss.feed_service import FeedService, FeedServiceV2


# Test fixtures
@pytest.fixture
async def db_repository() -> ArticleRepository:
    """Create test database repository with sample data."""
    # Use test database
    db_path = "data/test_articles_e2e.db"
    repo = ArticleRepository(db_path)
    await repo.initialize()

    # Clean up any existing data
    await repo.execute("DELETE FROM articles")

    # Create test articles for multiple locales
    test_articles = [
        # English articles
        Article(
            title="Patch 14.1 Notes",
            url="https://www.leagueoflegends.com/en-us/news/game-updates/patch-14-1-notes/",
            pub_date=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            guid="lol-en-us-patch-14-1",
            source=ArticleSource.create("lol", "en-us"),
            description="Balance changes and new features",
            content="<p>Detailed patch notes...</p>",
            image_url="https://lol.com/image1.jpg",
            author="Riot Games",
            categories=["Patch Notes", "Balance"],
            locale="en-us",
            source_category="official_riot",
        ),
        Article(
            title="New Champion: Ao Shin",
            url="https://www.leagueoflegends.com/en-us/news/champions/new-champion-ao-shin/",
            pub_date=datetime(2024, 1, 12, 14, 30, 0, tzinfo=timezone.utc),
            guid="lol-en-us-champion-ao-shin",
            source=ArticleSource.create("lol", "en-us"),
            description="The storm dragon arrives",
            content="<p>Champion reveal...</p>",
            image_url="https://lol.com/image2.jpg",
            author="Riot Games",
            categories=["Champions", "New Release"],
            locale="en-us",
            source_category="official_riot",
        ),
        Article(
            title="Esports Finals Preview",
            url="https://lolesports.com/en-us/news/worlds-2024-finals-preview",
            pub_date=datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
            guid="esports-en-us-finals-preview",
            source=ArticleSource.create("lolesports", "en-us"),
            description="Championship match analysis",
            content="<p>Tournament preview...</p>",
            image_url="https://lolesports.com/image3.jpg",
            author="LoL Esports",
            categories=["Esports", "Worlds"],
            locale="en-us",
            source_category="esports",
        ),
        # Italian articles
        Article(
            title="Note della Patch 14.1",
            url="https://www.leagueoflegends.com/it-it/news/aggiornamenti-di-gioco/note-patch-14-1/",
            pub_date=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            guid="lol-it-it-patch-14-1",
            source=ArticleSource.create("lol", "it-it"),
            description="Cambiamenti di equilibrio e nuove funzionalità",
            content="<p>Note dettagliate della patch...</p>",
            image_url="https://lol.com/it-image1.jpg",
            author="Riot Games",
            categories=["Note della Patch", "Bilanciamento"],
            locale="it-it",
            source_category="official_riot",
        ),
        Article(
            title="Nuovo Campione: Ao Shin",
            url="https://www.leagueoflegends.com/it-it/news/campioni/nuovo-campione-ao-shin/",
            pub_date=datetime(2024, 1, 12, 14, 30, 0, tzinfo=timezone.utc),
            guid="lol-it-it-champion-ao-shin",
            source=ArticleSource.create("lol", "it-it"),
            description="Il drago delle tempeste arriva",
            content="<p>Rivelazione del campione...</p>",
            image_url="https://lol.com/it-image2.jpg",
            author="Riot Games",
            categories=["Campioni", "Nuova Uscita"],
            locale="it-it",
            source_category="official_riot",
        ),
        # Spanish articles
        Article(
            title="Notas del parche 14.1",
            url="https://www.leagueoflegends.com/es-es/news/actualizaciones-del-juego/notas-parche-14-1/",
            pub_date=datetime(2024, 1, 10, 11, 0, 0, tzinfo=timezone.utc),
            guid="lol-es-es-patch-14-1",
            source=ArticleSource.create("lol", "es-es"),
            description="Cambios de equilibrio y nuevas características",
            content="<p>Notas del parche detalladas...</p>",
            image_url="https://lol.com/es-image1.jpg",
            author="Riot Games",
            categories=["Notas del Parche", "Equilibrio"],
            locale="es-es",
            source_category="official_riot",
        ),
        # Analytics source (English)
        Article(
            title="Tier List Patch 14.1",
            url="https://u.gg/lor/champions/tier-list",
            pub_date=datetime(2024, 1, 11, 8, 0, 0, tzinfo=timezone.utc),
            guid="u-gg-en-us-tier-list",
            source=ArticleSource.create("u-gg", "en-us"),
            description="Best champions for current patch",
            content="<p>Tier list analysis...</p>",
            image_url="https://u.gg/image1.jpg",
            author="U.GG Team",
            categories=["Tier List", "Meta"],
            locale="en-us",
            source_category="analytics",
        ),
    ]

    # Save all articles
    await repo.save_many(test_articles)

    yield repo

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestFeedServiceV2:
    """Test suite for FeedServiceV2 (multi-locale support)."""

    @pytest.mark.asyncio
    async def test_initialization(self, db_repository: ArticleRepository) -> None:
        """Test FeedServiceV2 initialization with all locales."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        settings = get_settings()
        supported_locales = settings.supported_locales

        # Should have generators for all supported locales
        assert len(service.generators) == len(supported_locales)
        assert set(service.generators.keys()) == set(supported_locales)

        # Check generator for specific locales
        assert "en-us" in service.generators
        assert "it-it" in service.generators
        assert "es-es" in service.generators

    @pytest.mark.asyncio
    async def test_get_feed_by_locale_en_us(self, db_repository: ArticleRepository) -> None:
        """Test feed generation for en-us locale."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("en-us", limit=50)

        # Verify XML structure
        assert "<?xml" in feed_xml
        assert "<rss" in feed_xml
        assert 'version="2.0"' in feed_xml

        # Parse with feedparser
        feed = feedparser.parse(feed_xml)

        # Verify feed metadata
        assert feed.feed.title == "League of Legends News"
        assert "Latest League of Legends news and updates" in feed.feed.description
        assert feed.feed.language == "en"

        # Verify articles
        assert len(feed.entries) >= 3  # At least 3 English articles

        # Check specific article fields
        entry = feed.entries[0]
        assert hasattr(entry, "title")
        assert hasattr(entry, "link")
        assert hasattr(entry, "guid")
        assert hasattr(entry, "published")
        assert hasattr(entry, "description")

    @pytest.mark.asyncio
    async def test_get_feed_by_locale_it_it(self, db_repository: ArticleRepository) -> None:
        """Test feed generation for it-it locale."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("it-it", limit=50)

        # Parse with feedparser
        feed = feedparser.parse(feed_xml)

        # Verify Italian metadata
        assert feed.feed.title == "Notizie League of Legends"
        assert "Ultime notizie e aggiornamenti di League of Legends" in feed.feed.description
        assert feed.feed.language == "it"

        # Should have Italian articles
        assert len(feed.entries) >= 2

        # Verify articles are in Italian
        for entry in feed.entries:
            assert entry.title  # Should have title
            # Articles should be from it-it locale
            assert "it-it" in entry.link or "it-it" in entry.guid

    @pytest.mark.asyncio
    async def test_get_feed_by_source_and_locale(self, db_repository: ArticleRepository) -> None:
        """Test feed generation by source and locale."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        # Test lol source with en-us locale
        feed_xml = await service.get_feed_by_source_and_locale("lol", "en-us", limit=50)

        feed = feedparser.parse(feed_xml)

        # Should filter by source
        assert "lol" in feed.feed.title.lower() or "league" in feed.feed.title.lower()
        assert feed.feed.language == "en"

        # All entries should be from lol source
        for entry in feed.entries:
            # Check that entries are from the correct source
            assert "lol" in entry.link.lower() or "leagueoflegends" in entry.link.lower()

    @pytest.mark.asyncio
    async def test_get_feed_by_category_and_locale(self, db_repository: ArticleRepository) -> None:
        """Test feed generation by category and locale."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        # Test official_riot category with en-us locale
        feed_xml = await service.get_feed_by_category_and_locale("official_riot", "en-us", limit=50)

        feed = feedparser.parse(feed_xml)

        # Should include category in title
        assert "official_riot" in feed.feed.title.lower()
        assert feed.feed.language == "en"

        # Verify feed structure
        assert len(feed.entries) >= 2  # At least 2 official_riot articles

    @pytest.mark.asyncio
    async def test_multiple_locales_have_correct_metadata(
        self, db_repository: ArticleRepository
    ) -> None:
        """Test that multiple locales have correct localized metadata."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        settings = get_settings()

        # Test a few key locales
        test_locales = ["en-us", "it-it", "es-es", "pt-br", "de-de"]

        for locale in test_locales:
            feed_xml = await service.get_feed_by_locale(locale, limit=10)
            feed = feedparser.parse(feed_xml)

            # Verify title matches settings
            expected_title = settings.feed_titles.get(locale, "League of Legends News")
            assert feed.feed.title == expected_title, f"Title mismatch for {locale}"

            # Verify description matches settings
            expected_desc = settings.feed_descriptions.get(locale, "Latest League of Legends news")
            assert expected_desc in feed.feed.description, f"Description mismatch for {locale}"

            # Verify language code
            expected_lang = locale.split("-")[0]  # Extract language code
            assert feed.feed.language == expected_lang, f"Language mismatch for {locale}"

    @pytest.mark.asyncio
    async def test_feed_caching_per_locale(self, db_repository: ArticleRepository) -> None:
        """Test that feeds are cached correctly per locale."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        # First call
        feed1 = await service.get_feed_by_locale("en-us", limit=50)

        # Second call (should use cache)
        feed2 = await service.get_feed_by_locale("en-us", limit=50)

        # Should be identical
        assert feed1 == feed2

        # Different locale should not use cache
        feed3 = await service.get_feed_by_locale("it-it", limit=50)
        assert feed3 != feed1

    @pytest.mark.asyncio
    async def test_unsupported_locale_raises_error(self, db_repository: ArticleRepository) -> None:
        """Test that requesting unsupported locale raises ValueError."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        with pytest.raises(ValueError, match="Unsupported locale"):
            await service.get_feed_by_locale("xx-yy", limit=50)

    @pytest.mark.asyncio
    async def test_get_available_locales(self, db_repository: ArticleRepository) -> None:
        """Test getting list of available locales."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        available_locales = await service.get_available_locales()

        # Should include locales we inserted
        assert "en-us" in available_locales
        assert "it-it" in available_locales
        assert "es-es" in available_locales

    @pytest.mark.asyncio
    async def test_get_supported_locales(self, db_repository: ArticleRepository) -> None:
        """Test getting list of all supported locales."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        supported_locales = service.get_supported_locales()

        settings = get_settings()
        assert len(supported_locales) == len(settings.supported_locales)
        assert set(supported_locales) == set(settings.supported_locales)

    @pytest.mark.asyncio
    async def test_rss_field_mapping(self, db_repository: ArticleRepository) -> None:
        """Test that article fields are correctly mapped to RSS elements."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("en-us", limit=50)
        feed = feedparser.parse(feed_xml)

        # Find a known article
        entry = next((e for e in feed.entries if "Patch 14.1" in e.title), None)
        assert entry is not None

        # Verify RSS field mapping
        assert entry.title  # title
        assert entry.link  # url
        assert entry.guid  # guid
        assert entry.published  # pub_date
        assert entry.description  # description
        assert entry.get("content")  # content:encoded

        # Verify author
        # feedgen produces "email (name)" format
        assert "Riot Games" in entry.get("author", "") or "noreply@riotgames.com" in entry.get(
            "author", ""
        )

        # Verify categories
        assert hasattr(entry, "tags")
        tag_terms = [tag["term"] for tag in entry.tags]
        assert "Patch Notes" in tag_terms
        assert "Balance" in tag_terms

        # Verify enclosure (image)
        assert hasattr(entry, "enclosures")
        assert len(entry.enclosures) > 0
        assert entry.enclosures[0].get("type") == "image/jpeg"

    @pytest.mark.asyncio
    async def test_xml_escaping(self, db_repository: ArticleRepository) -> None:
        """Test that special characters are properly escaped in XML."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        # Add article with special characters
        article = Article(
            title='Test & Review: <Champion\'s> "New" Skin',
            url="https://example.com/test-special-chars",
            pub_date=datetime.now(timezone.utc),
            guid="test-special-chars",
            source=ArticleSource.create("lol", "en-us"),
            description='Description with <tags> & "quotes"',
            locale="en-us",
        )
        await db_repository.save(article)

        feed_xml = await service.get_feed_by_locale("en-us", limit=100)

        # Should not contain unescaped special characters
        # (XML parser would fail if they were present)
        feed = feedparser.parse(feed_xml)

        # Find the article
        entry = next((e for e in feed.entries if "Test & Review" in e.title), None)
        assert entry is not None
        assert "&lt;Champion's&gt;" in entry.title or "<Champion's>" in entry.title

    @pytest.mark.asyncio
    async def test_feed_validity_all_supported_locales(
        self, db_repository: ArticleRepository
    ) -> None:
        """Test that all supported locales generate valid RSS feeds."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        settings = get_settings()
        validation_errors = []

        for locale in settings.supported_locales:
            try:
                feed_xml = await service.get_feed_by_locale(locale, limit=10)
                feed = feedparser.parse(feed_xml)

                # Basic validation
                if not feed.feed.get("title"):
                    validation_errors.append(f"{locale}: Missing feed title")
                if not feed.feed.get("description"):
                    validation_errors.append(f"{locale}: Missing feed description")
                if not feed.feed.get("language"):
                    validation_errors.append(f"{locale}: Missing feed language")

                # Check that it's valid RSS
                if feed.version == "":
                    validation_errors.append(f"{locale}: Not valid RSS format")

            except Exception as e:
                validation_errors.append(f"{locale}: {str(e)}")

        # Report all errors
        if validation_errors:
            pytest.fail("Feed validation errors:\n" + "\n".join(validation_errors))


class TestFeedServiceLegacy:
    """Test suite for legacy FeedService."""

    @pytest.mark.asyncio
    async def test_get_main_feed(self, db_repository: ArticleRepository) -> None:
        """Test legacy get_main_feed method."""
        service = FeedService(db_repository, cache_ttl=300)

        feed_xml = await service.get_main_feed("http://localhost:8000/feed.xml", limit=50)

        # Verify XML structure
        assert "<?xml" in feed_xml
        assert "<rss" in feed_xml

        # Parse with feedparser
        feed = feedparser.parse(feed_xml)
        assert len(feed.entries) >= 3

    @pytest.mark.asyncio
    async def test_get_feed_by_source(self, db_repository: ArticleRepository) -> None:
        """Test legacy get_feed_by_source method."""
        service = FeedService(db_repository, cache_ttl=300)

        source = ArticleSource.create("lol", "en-us")
        feed_xml = await service.get_feed_by_source(
            source, "http://localhost:8000/feed/en-us.xml", limit=50
        )

        feed = feedparser.parse(feed_xml)
        assert "lol" in feed.feed.title.lower() or "league" in feed.feed.title.lower()

    @pytest.mark.asyncio
    async def test_get_feed_by_category(self, db_repository: ArticleRepository) -> None:
        """Test legacy get_feed_by_category method."""
        service = FeedService(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_category(
            "Patch Notes", "http://localhost:8000/feed/patch-notes.xml", limit=50
        )

        feed = feedparser.parse(feed_xml)
        assert "Patch Notes" in feed.feed.title

    @pytest.mark.asyncio
    async def test_legacy_service_uses_correct_language(
        self, db_repository: ArticleRepository
    ) -> None:
        """Test that legacy service uses correct language per source."""
        service = FeedService(db_repository, cache_ttl=300)

        # Test Italian source
        it_source = ArticleSource.create("lol", "it-it")
        feed_xml = await service.get_feed_by_source(
            it_source, "http://localhost:8000/feed/it-it.xml", limit=50
        )

        feed = feedparser.parse(feed_xml)
        assert feed.feed.language == "it"


class TestRSSCompliance:
    """Test RSS 2.0 compliance for generated feeds."""

    @pytest.mark.asyncio
    async def test_required_channel_elements(self, db_repository: ArticleRepository) -> None:
        """Test that all required RSS channel elements are present."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("en-us", limit=50)
        feed = feedparser.parse(feed_xml)

        # Required elements
        assert feed.feed.get("title"), "Missing required channel element: title"
        assert feed.feed.get("link"), "Missing required channel element: link"
        assert feed.feed.get("description"), "Missing required channel element: description"

    @pytest.mark.asyncio
    async def test_required_item_elements(self, db_repository: ArticleRepository) -> None:
        """Test that all required RSS item elements are present."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("en-us", limit=50)
        feed = feedparser.parse(feed_xml)

        for entry in feed.entries:
            # Required elements
            assert hasattr(entry, "title") or hasattr(
                entry, "description"
            ), f"Entry missing title or description: {entry.get('id', 'unknown')}"
            assert hasattr(entry, "link"), f"Entry missing link: {entry.get('id', 'unknown')}"

    @pytest.mark.asyncio
    async def test_optional_channel_elements(self, db_repository: ArticleRepository) -> None:
        """Test that optional RSS channel elements are included."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("en-us", limit=50)
        feed = feedparser.parse(feed_xml)

        # Recommended optional elements
        assert feed.feed.get("language"), "Missing recommended element: language"
        assert feed.feed.get("lastBuildDate") or feed.feed.get(
            "updated"
        ), "Missing recommended element: lastBuildDate or updated"

    @pytest.mark.asyncio
    async def test_guid_is_permalink(self, db_repository: ArticleRepository) -> None:
        """Test that GUID entries have proper permalink attribute."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("en-us", limit=50)
        feed = feedparser.parse(feed_xml)

        for entry in feed.entries:
            assert hasattr(entry, "guid"), f"Entry missing GUID: {entry.get('link', 'unknown')}"
            # GUID should be a permalink (matches article URL or is unique)
            assert entry.guid, f"Empty GUID for entry: {entry.get('link', 'unknown')}"

    @pytest.mark.asyncio
    async def test_pub_date_format(self, db_repository: ArticleRepository) -> None:
        """Test that publication dates are in RFC 822 format."""
        service = FeedServiceV2(db_repository, cache_ttl=300)

        feed_xml = await service.get_feed_by_locale("en-us", limit=50)
        feed = feedparser.parse(feed_xml)

        for entry in feed.entries:
            assert hasattr(
                entry, "published"
            ), f"Entry missing published date: {entry.get('title', 'unknown')}"
            # feedparser should parse the date successfully
            assert entry.published_parsed, f"Invalid date format for: {entry.title}"


def print_test_results() -> None:
    """Print test execution summary."""
    print("\n" + "=" * 80)
    print("RSS FEED GENERATION - END-TO-END TEST RESULTS")
    print("=" * 80 + "\n")

    print("Test Categories:")
    print("  1. FeedServiceV2 (New Multi-Locale)")
    print("     - Initialization with all locales")
    print("     - Feed generation by locale (en-us, it-it)")
    print("     - Feed generation by source and locale")
    print("     - Feed generation by category and locale")
    print("     - Locale-specific metadata validation")
    print("     - Caching behavior")
    print("     - Error handling for unsupported locales")
    print("     - Available vs. supported locales")
    print("     - RSS field mapping")
    print("     - XML escaping")
    print("     - Validity across all supported locales")
    print()
    print("  2. FeedService (Legacy)")
    print("     - Main feed generation")
    print("     - Source-filtered feeds")
    print("     - Category-filtered feeds")
    print("     - Language selection")
    print()
    print("  3. RSS 2.0 Compliance")
    print("     - Required channel elements")
    print("     - Required item elements")
    print("     - Optional elements")
    print("     - GUID format")
    print("     - Publication date format (RFC 822)")
    print()
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print_test_results()
