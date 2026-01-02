"""
End-to-End Test Suite
"""
from datetime import datetime

import feedparser
import pytest

from src.database import ArticleRepository
from src.models import Article, ArticleSource
from src.rss.feed_service import FeedService


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_workflow_memory_database(tmp_path):
    repo = ArticleRepository(str(tmp_path / "test.db"))
    await repo.initialize()
    try:
        articles = [
            Article(
                title=f"Test Article {_i}",
                url=f"https://example.com/article-{_i}",
                pub_date=datetime.utcnow(),
                guid=f"test-guid-{_i}",
                source=ArticleSource.create("lol", "en-us"),
                description=f"Test description {_i}",
                content=f"<p>Test content {_i}</p>",
                image_url=f"https://example.com/image-{_i}.jpg",
                author="Test Author",
                categories=["News", "Test"],
            )
            for _i in range(10)
        ]
        saved_count = await repo.save_many(articles)
        assert saved_count == 10
        feed_service = FeedService(repo, cache_ttl=300)
        feed_xml = await feed_service.get_main_feed("http://test/feed.xml", limit=10)
        feed = feedparser.parse(feed_xml)
        assert feed.version == "rss20"
        assert len(feed.entries) == 10
        assert feed.feed.title
        for _i, entry in enumerate(feed.entries):
            assert entry.title
            assert entry.link
            assert entry.id
    finally:
        await repo.close()


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multi_source_workflow(tmp_path):
    repo = ArticleRepository(str(tmp_path / "test.db"))
    await repo.initialize()
    try:
        articles = [
            Article(
                title="English Article",
                url="https://example.com/en",
                pub_date=datetime.utcnow(),
                guid="en-guid",
                source=ArticleSource.create("lol", "en-us"),
                description="English",
                categories=["News"],
            ),
            Article(
                title="Italian Article",
                url="https://example.com/it",
                pub_date=datetime.utcnow(),
                guid="it-guid",
                source=ArticleSource.create("lol", "it-it"),
                description="Italian",
                categories=["News"],
            ),
        ]
        await repo.save_many(articles)
        feed_service = FeedService(repo)
        en_feed = feedparser.parse(
            await feed_service.get_feed_by_source(
                ArticleSource.create("lol", "en-us"), "http://test/feed.xml"
            )
        )
        assert len(en_feed.entries) == 1
        main_feed = feedparser.parse(await feed_service.get_main_feed("http://test/feed.xml"))
        assert len(main_feed.entries) == 2
    finally:
        await repo.close()
