"""
Simple RSS Feed Generation Test - Debug Version

Run with: uv run pytest tmp/test_feed_generation_simple.py -vv -s
"""

from datetime import datetime, timezone
from pathlib import Path

import feedparser
import pytest

from src.database import ArticleRepository
from src.models import Article, ArticleSource
from src.rss.feed_service import FeedServiceV2


@pytest.fixture
async def test_db():
    """Create test database with sample data."""
    db_path = "data/test_simple.db"
    repo = ArticleRepository(db_path)
    await repo.initialize()

    # Clean up
    await repo.execute("DELETE FROM articles")

    # Add test articles
    articles = [
        Article(
            title="Patch 14.1 Notes",
            url="https://www.leagueoflegends.com/en-us/news/patch-14-1/",
            pub_date=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            guid="lol-en-us-patch-14-1",
            source=ArticleSource.create("lol", "en-us"),
            description="Balance changes",
            categories=["Patch Notes"],
            locale="en-us",
            source_category="official_riot",
        ),
        Article(
            title="Note Patch 14.1 IT",
            url="https://www.leagueoflegends.com/it-it/news/patch-14-1/",
            pub_date=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            guid="lol-it-it-patch-14-1",
            source=ArticleSource.create("lol", "it-it"),
            description="Cambiamenti",
            categories=["Patch Notes"],
            locale="it-it",
            source_category="official_riot",
        ),
    ]

    count = await repo.save_many(articles)
    print(f"\n[SETUP] Saved {count} articles to database")

    yield repo

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_basic_feed_generation(test_db):
    """Test basic feed generation."""
    print("\n[TEST] Testing basic feed generation...")

    # Check database state
    all_articles = await test_db.fetch_all("SELECT * FROM articles")
    print(f"[DB] Total articles in database: {len(all_articles)}")

    for row in all_articles:
        print(f"  - {row[1][:30]} | locale={row[12]} | category={row[13]}")

    # Create service
    service = FeedServiceV2(test_db, cache_ttl=300)
    print(f"[SERVICE] Supported locales: {service.get_supported_locales()}")
    print(f"[SERVICE] Generators: {list(service.generators.keys())}")

    # Test en-us feed
    print("\n[FEED] Generating en-us feed...")
    feed_xml = await service.get_feed_by_locale("en-us", limit=50)
    feed = feedparser.parse(feed_xml)

    print(f"[FEED] Title: {feed.feed.title}")
    print(f"[FEED] Language: {feed.feed.language}")
    print(f"[FEED] Entries: {len(feed.entries)}")

    for entry in feed.entries:
        print(f"  - {entry.title}")

    # Assertions
    assert len(feed.entries) >= 1, "Should have at least 1 entry"
    assert feed.feed.language == "en"


@pytest.mark.asyncio
async def test_category_feed(test_db):
    """Test category filtering."""
    print("\n[TEST] Testing category filtering...")

    service = FeedServiceV2(test_db, cache_ttl=300)

    # Query database directly to see what we get
    articles = await test_db.get_latest_by_locale(
        locale="en-us", source_category="official_riot", limit=50
    )
    print(f"[DB] Found {len(articles)} articles for en-us + official_riot")
    for a in articles:
        print(f"  - {a.title} | category={a.source_category}")

    # Generate feed
    print("\n[FEED] Generating category feed...")
    feed_xml = await service.get_feed_by_category_and_locale("official_riot", "en-us", limit=50)
    feed = feedparser.parse(feed_xml)

    print(f"[FEED] Title: {feed.feed.title}")
    print(f"[FEED] Entries: {len(feed.entries)}")

    # This should pass since we have 1 official_riot article
    assert len(feed.entries) >= 1, f"Expected at least 1 entry, got {len(feed.entries)}"


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-s"])
