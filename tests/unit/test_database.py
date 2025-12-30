"""
Tests for database repository.

This module tests the ArticleRepository class, including database
initialization, CRUD operations, and querying.
"""

import pytest
import os
from datetime import datetime
from pathlib import Path
from src.database import ArticleRepository
from src.models import Article, ArticleSource


@pytest.fixture
async def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_articles.db"
    repo = ArticleRepository(str(db_path))
    await repo.initialize()
    return repo


@pytest.mark.asyncio
async def test_database_initialization(tmp_path):
    """Test that database is initialized correctly."""
    db_path = tmp_path / "test.db"
    repo = ArticleRepository(str(db_path))
    await repo.initialize()

    # Check that database file was created
    assert db_path.exists()

    # Check that we can perform basic operations
    count = await repo.count()
    assert count == 0


@pytest.mark.asyncio
async def test_save_article(temp_db):
    """Test saving a single article."""
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28, 10, 0, 0),
        guid="test-123",
        source=ArticleSource.LOL_EN_US,
        description="Test description"
    )

    result = await temp_db.save(article)
    assert result is True

    # Verify it was saved
    count = await temp_db.count()
    assert count == 1


@pytest.mark.asyncio
async def test_save_duplicate_article(temp_db):
    """Test that duplicate articles are not saved."""
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28),
        guid="test-123",
        source=ArticleSource.LOL_EN_US
    )

    # Save first time
    result1 = await temp_db.save(article)
    assert result1 is True

    # Try to save again (duplicate GUID)
    result2 = await temp_db.save(article)
    assert result2 is False

    # Should still only have 1 article
    count = await temp_db.count()
    assert count == 1


@pytest.mark.asyncio
async def test_save_many_articles(temp_db):
    """Test saving multiple articles."""
    articles = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/article-{i}",
            pub_date=datetime(2025, 12, 28, 10, i, 0),
            guid=f"test-{i}",
            source=ArticleSource.LOL_EN_US
        )
        for i in range(5)
    ]

    count = await temp_db.save_many(articles)
    assert count == 5

    total = await temp_db.count()
    assert total == 5


@pytest.mark.asyncio
async def test_save_many_with_duplicates(temp_db):
    """Test that save_many correctly handles duplicates."""
    articles = [
        Article(
            title="Article 1",
            url="https://example.com/1",
            pub_date=datetime(2025, 12, 28),
            guid="test-1",
            source=ArticleSource.LOL_EN_US
        ),
        Article(
            title="Article 2",
            url="https://example.com/2",
            pub_date=datetime(2025, 12, 28),
            guid="test-2",
            source=ArticleSource.LOL_EN_US
        ),
    ]

    # Save first batch
    count1 = await temp_db.save_many(articles)
    assert count1 == 2

    # Try to save same articles again plus one new
    articles.append(
        Article(
            title="Article 3",
            url="https://example.com/3",
            pub_date=datetime(2025, 12, 28),
            guid="test-3",
            source=ArticleSource.LOL_EN_US
        )
    )

    count2 = await temp_db.save_many(articles)
    assert count2 == 1  # Only the new one

    total = await temp_db.count()
    assert total == 3


@pytest.mark.asyncio
async def test_get_by_guid(temp_db):
    """Test retrieving article by GUID."""
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28),
        guid="test-123",
        source=ArticleSource.LOL_EN_US,
        description="Test description"
    )

    await temp_db.save(article)

    # Retrieve by GUID
    retrieved = await temp_db.get_by_guid("test-123")
    assert retrieved is not None
    assert retrieved.title == "Test Article"
    assert retrieved.guid == "test-123"
    assert retrieved.description == "Test description"


@pytest.mark.asyncio
async def test_get_by_guid_not_found(temp_db):
    """Test that get_by_guid returns None for non-existent GUID."""
    result = await temp_db.get_by_guid("non-existent")
    assert result is None


@pytest.mark.asyncio
async def test_get_latest(temp_db):
    """Test retrieving latest articles."""
    # Create articles with different dates
    articles = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/article-{i}",
            pub_date=datetime(2025, 12, 20 + i),  # Different dates
            guid=f"test-{i}",
            source=ArticleSource.LOL_EN_US
        )
        for i in range(5)
    ]

    await temp_db.save_many(articles)

    # Get latest 3 articles
    latest = await temp_db.get_latest(limit=3)
    assert len(latest) == 3

    # Should be ordered by pub_date DESC (newest first)
    assert latest[0].pub_date > latest[1].pub_date
    assert latest[1].pub_date > latest[2].pub_date


@pytest.mark.asyncio
async def test_get_latest_with_source_filter(temp_db):
    """Test retrieving latest articles filtered by source."""
    # Create articles from different sources
    articles = [
        Article(
            title="EN Article 1",
            url="https://example.com/en-1",
            pub_date=datetime(2025, 12, 25),
            guid="en-1",
            source=ArticleSource.LOL_EN_US
        ),
        Article(
            title="IT Article 1",
            url="https://example.com/it-1",
            pub_date=datetime(2025, 12, 26),
            guid="it-1",
            source=ArticleSource.LOL_IT_IT
        ),
        Article(
            title="EN Article 2",
            url="https://example.com/en-2",
            pub_date=datetime(2025, 12, 27),
            guid="en-2",
            source=ArticleSource.LOL_EN_US
        ),
    ]

    await temp_db.save_many(articles)

    # Get only EN-US articles
    en_articles = await temp_db.get_latest(limit=10, source="lol-en-us")
    assert len(en_articles) == 2
    assert all(a.source == ArticleSource.LOL_EN_US for a in en_articles)

    # Get only IT-IT articles
    it_articles = await temp_db.get_latest(limit=10, source="lol-it-it")
    assert len(it_articles) == 1
    assert it_articles[0].source == ArticleSource.LOL_IT_IT
