"""Complete End-to-End Test Suite for LoL Stonks RSS"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import pytest

from src.api_client import LoLNewsAPIClient
from src.database import ArticleRepository
from src.models import Article, ArticleSource
from src.rss.feed_service import FeedService
from src.services.scheduler import NewsScheduler


@pytest.fixture
async def temp_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "test.db")
        repo = ArticleRepository(db_path)
        await repo.initialize()
        yield repo
        await repo.close()


@pytest.fixture
def sample_articles():
    base_date = datetime(2025, 12, 29, 10, 0, 0)
    return [
        Article(
            title=f"Test Article {i}",
            url=f"https://example.com/article-{i}",
            pub_date=base_date - timedelta(hours=i),
            guid=f"test-guid-{i}",
            source=ArticleSource.LOL_EN_US if i % 2 == 0 else ArticleSource.LOL_IT_IT,
            description=f"Test description {i}",
            categories=["News", "Test"] if i % 2 == 0 else ["Patch Notes"],
        )
        for i in range(1, 21)
    ]


@pytest.fixture
async def populated_db(temp_db, sample_articles):
    await temp_db.save_many(sample_articles)
    return temp_db


# ============================================================================
# SMOKE TESTS
# ============================================================================


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_database_initialization(temp_db):
    assert Path(temp_db.db_path).exists()
    articles = await temp_db.get_latest(limit=10)
    assert isinstance(articles, list)
    count = await temp_db.count()
    assert count == 0


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_rss_generation(temp_db):
    feed_service = FeedService(temp_db, cache_ttl=300)
    feed_xml = await feed_service.get_main_feed("http://test/feed.xml", limit=10)
    feed = feedparser.parse(feed_xml)
    assert feed.version == "rss20"
    assert feed.feed.title is not None


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_article_save(temp_db):
    article = Article(
        title="Smoke Test Article",
        url="https://example.com/smoke",
        pub_date=datetime.utcnow(),
        guid="smoke-test-guid",
        source=ArticleSource.LOL_EN_US,
        description="Smoke test description",
    )
    result = await temp_db.save(article)
    assert result is True
    retrieved = await temp_db.get_by_guid("smoke-test-guid")
    assert retrieved is not None
    assert retrieved.title == "Smoke Test Article"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_cache_behavior(populated_db):
    feed_service = FeedService(populated_db, cache_ttl=300)
    feed1 = await feed_service.get_main_feed("http://test/feed.xml", limit=10)
    assert feed1 is not None
    feed2 = await feed_service.get_main_feed("http://test/feed.xml", limit=10)
    assert feed2 is not None
    assert feed1 == feed2


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_scheduler_creation(temp_db):
    scheduler = NewsScheduler(temp_db, interval_minutes=1)
    scheduler.start()
    assert scheduler.is_running is True
    scheduler.stop()
    assert scheduler.is_running is False


# ============================================================================
# COMPLETE WORKFLOW TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_news_workflow(temp_db):
    client = LoLNewsAPIClient()
    try:
        articles = await client.fetch_news("en-us")
        assert len(articles) > 0
    except Exception as e:
        pytest.skip(f"API fetch failed: {e}")

    new_count = 0
    for article in articles[:10]:
        if await temp_db.save(article):
            new_count += 1
    assert new_count > 0

    feed_service = FeedService(temp_db, cache_ttl=300)
    feed_xml = await feed_service.get_main_feed("http://test/feed.xml", limit=20)
    feed = feedparser.parse(feed_xml)
    assert feed.version == "rss20"
    assert len(feed.entries) > 0


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_multi_locale_workflow():
    client_en = LoLNewsAPIClient()
    client_it = LoLNewsAPIClient()
    try:
        articles_en = await client_en.fetch_news("en-us")
        articles_it = await client_it.fetch_news("it-it")
    except Exception as e:
        pytest.skip(f"API fetch failed: {e}")

    assert len(articles_en) > 0
    assert len(articles_it) > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multi_source_feed_generation(populated_db):
    feed_service = FeedService(populated_db, cache_ttl=300)
    main_feed = feedparser.parse(await feed_service.get_main_feed("http://test/feed.xml"))
    _en_feed = feedparser.parse(
        await feed_service.get_feed_by_source(ArticleSource.LOL_EN_US, "http://test/feed/en-us.xml")
    )
    _it_feed = feedparser.parse(
        await feed_service.get_feed_by_source(ArticleSource.LOL_IT_IT, "http://test/feed/it-it.xml")
    )
    assert len(main_feed.entries) > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scheduler_manual_trigger(temp_db):
    scheduler = NewsScheduler(temp_db, interval_minutes=30)
    scheduler.start()
    try:
        stats = await scheduler.trigger_update_now()
        assert "sources" in stats
        assert "total_fetched" in stats
        assert "total_new" in stats
    finally:
        scheduler.stop()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_invalidation_workflow(populated_db):
    feed_service = FeedService(populated_db, cache_ttl=300)
    _feed1 = await feed_service.get_main_feed("http://test/feed.xml")
    feed_service.invalidate_cache()
    feed2 = await feed_service.get_main_feed("http://test/feed.xml")
    assert feed2 is not None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_duplicate_guid_handling(populated_db):
    articles = await populated_db.get_latest(limit=1)
    assert len(articles) > 0
    result = await populated_db.save(articles[0])
    assert result is False


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_empty_feed_generation(temp_db):
    feed_service = FeedService(temp_db, cache_ttl=300)
    feed_xml = await feed_service.get_main_feed("http://test/feed.xml")
    feed = feedparser.parse(feed_xml)
    assert feed.version == "rss20"
    assert len(feed.entries) == 0


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.asyncio
async def test_rss_20_compliance(populated_db):
    feed_service = FeedService(populated_db, cache_ttl=300)
    feed_xml = await feed_service.get_main_feed("http://test/feed.xml")
    feed = feedparser.parse(feed_xml)
    assert feed.version == "rss20"
    assert hasattr(feed.feed, "title")
    assert hasattr(feed.feed, "link")
    assert hasattr(feed.feed, "description")


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.asyncio
async def test_guid_uniqueness(populated_db):
    feed_service = FeedService(populated_db, cache_ttl=300)
    feed_xml = await feed_service.get_main_feed("http://test/feed.xml")
    feed = feedparser.parse(feed_xml)
    guids = [entry.id for entry in feed.entries if entry.id]
    unique_guids = set(guids)
    assert len(guids) == len(unique_guids)


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
async def test_feed_generation_performance(populated_db):
    import time

    feed_service = FeedService(populated_db, cache_ttl=300)
    start = time.perf_counter()
    await feed_service.get_main_feed("http://test/feed.xml")
    uncached_time = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    await feed_service.get_main_feed("http://test/feed.xml")
    cached_time = (time.perf_counter() - start) * 1000
    print(f"Uncached: {uncached_time:.2f}ms, Cached: {cached_time:.2f}ms")
    assert uncached_time < 1000
    assert cached_time < 200
