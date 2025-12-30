"""Performance Test Suite"""
import time
from datetime import datetime

import pytest

from src.database import ArticleRepository
from src.models import Article, ArticleSource
from src.rss.feed_service import FeedService


@pytest.mark.performance
@pytest.mark.asyncio
async def test_feed_generation_performance(tmp_path):
    repo = ArticleRepository(str(tmp_path / "test.db"))
    await repo.initialize()
    try:
        articles = [
            Article(
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                pub_date=datetime.utcnow(),
                guid=f"guid-{i}",
                source=ArticleSource.LOL_EN_US,
                description=f"Description {i}",
                categories=["News"],
            )
            for i in range(50)
        ]
        await repo.save_many(articles)
        service = FeedService(repo, cache_ttl=300)
        await service.get_main_feed("http://test/feed.xml", limit=50)
        start = time.perf_counter()
        await service.get_main_feed("http://test/feed.xml", limit=50)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"Cached feed: {elapsed:.2f}ms")
        assert elapsed < 200
    finally:
        await repo.close()


@pytest.mark.performance
@pytest.mark.asyncio
async def test_database_query_performance(tmp_path):
    repo = ArticleRepository(str(tmp_path / "test.db"))
    await repo.initialize()
    try:
        articles = [
            Article(
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                pub_date=datetime.utcnow(),
                guid=f"guid-{i}",
                source=ArticleSource.LOL_EN_US,
                description=f"Description {i}",
                categories=["News"],
            )
            for i in range(200)
        ]
        await repo.save_many(articles)
        times = []
        for _ in range(10):
            start = time.perf_counter()
            result = await repo.get_latest(limit=50)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            assert len(result) == 50
        avg_query = sum(times) / len(times)
        print(f"Avg query: {avg_query:.2f}ms")
        assert avg_query < 50
    finally:
        await repo.close()
