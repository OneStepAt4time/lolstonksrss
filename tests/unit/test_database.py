"""
Tests for database repository.

This module tests the ArticleRepository class, including database
initialization, CRUD operations, and querying with multi-source,
multi-locale support.
"""

from datetime import datetime

import pytest

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
    source = ArticleSource.create("lol", "en-us")
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28, 10, 0, 0),
        guid="test-123",
        source=source,
        description="Test description",
    )

    result = await temp_db.save(article)
    assert result is True

    # Verify it was saved
    count = await temp_db.count()
    assert count == 1


@pytest.mark.asyncio
async def test_save_duplicate_article(temp_db):
    """Test that duplicate articles are not saved."""
    source = ArticleSource.create("lol", "en-us")
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28),
        guid="test-123",
        source=source,
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
    source = ArticleSource.create("lol", "en-us")
    articles = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/article-{i}",
            pub_date=datetime(2025, 12, 28, 10, i, 0),
            guid=f"test-{i}",
            source=source,
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
    source = ArticleSource.create("lol", "en-us")
    articles = [
        Article(
            title="Article 1",
            url="https://example.com/1",
            pub_date=datetime(2025, 12, 28),
            guid="test-1",
            source=source,
        ),
        Article(
            title="Article 2",
            url="https://example.com/2",
            pub_date=datetime(2025, 12, 28),
            guid="test-2",
            source=source,
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
            source=source,
        )
    )

    count2 = await temp_db.save_many(articles)
    assert count2 == 1  # Only the new one

    total = await temp_db.count()
    assert total == 3


@pytest.mark.asyncio
async def test_get_by_guid(temp_db):
    """Test retrieving article by GUID."""
    source = ArticleSource.create("lol", "en-us")
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28),
        guid="test-123",
        source=source,
        description="Test description",
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
    source = ArticleSource.create("lol", "en-us")
    # Create articles with different dates
    articles = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/article-{i}",
            pub_date=datetime(2025, 12, 20 + i),  # Different dates
            guid=f"test-{i}",
            source=source,
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
    source_en = ArticleSource.create("lol", "en-us")
    source_it = ArticleSource.create("lol", "it-it")

    # Create articles from different sources
    articles = [
        Article(
            title="EN Article 1",
            url="https://example.com/en-1",
            pub_date=datetime(2025, 12, 25),
            guid="en-1",
            source=source_en,
        ),
        Article(
            title="IT Article 1",
            url="https://example.com/it-1",
            pub_date=datetime(2025, 12, 26),
            guid="it-1",
            source=source_it,
        ),
        Article(
            title="EN Article 2",
            url="https://example.com/en-2",
            pub_date=datetime(2025, 12, 27),
            guid="en-2",
            source=source_en,
        ),
    ]

    await temp_db.save_many(articles)

    # Get only EN-US articles (new format: "lol:en-us")
    en_articles = await temp_db.get_latest(limit=10, source="lol:en-us")
    assert len(en_articles) == 2
    assert all(str(a.source) == "lol:en-us" for a in en_articles)

    # Get only IT-IT articles
    it_articles = await temp_db.get_latest(limit=10, source="lol:it-it")
    assert len(it_articles) == 1
    assert str(it_articles[0].source) == "lol:it-it"


@pytest.mark.asyncio
async def test_get_latest_by_locale(temp_db):
    """Test retrieving latest articles for a specific locale."""
    source_en = ArticleSource.create("lol", "en-us")
    source_it = ArticleSource.create("lol", "it-it")

    articles = [
        Article(
            title="EN Article 1",
            url="https://example.com/en-1",
            pub_date=datetime(2025, 12, 25),
            guid="en-1",
            source=source_en,
        ),
        Article(
            title="IT Article 1",
            url="https://example.com/it-1",
            pub_date=datetime(2025, 12, 26),
            guid="it-1",
            source=source_it,
        ),
        Article(
            title="EN Article 2",
            url="https://example.com/en-2",
            pub_date=datetime(2025, 12, 27),
            guid="en-2",
            source=source_en,
        ),
    ]

    await temp_db.save_many(articles)

    # Get only EN-US articles
    en_articles = await temp_db.get_latest_by_locale("en-us")
    assert len(en_articles) == 2
    assert all(a.locale == "en-us" for a in en_articles)

    # Get only IT-IT articles
    it_articles = await temp_db.get_latest_by_locale("it-it")
    assert len(it_articles) == 1
    assert it_articles[0].locale == "it-it"


@pytest.mark.asyncio
async def test_get_by_locale_group(temp_db):
    """Test retrieving articles for a group of locales."""
    source_en = ArticleSource.create("lol", "en-us")
    source_it = ArticleSource.create("lol", "it-it")
    source_es = ArticleSource.create("lol", "es-es")

    articles = [
        Article(
            title="EN Article",
            url="https://example.com/en",
            pub_date=datetime(2025, 12, 25),
            guid="en",
            source=source_en,
        ),
        Article(
            title="IT Article",
            url="https://example.com/it",
            pub_date=datetime(2025, 12, 26),
            guid="it",
            source=source_it,
        ),
        Article(
            title="ES Article",
            url="https://example.com/es",
            pub_date=datetime(2025, 12, 27),
            guid="es",
            source=source_es,
        ),
    ]

    await temp_db.save_many(articles)

    # Get articles for English locales
    eu_articles = await temp_db.get_by_locale_group(["en-us", "es-es"])
    assert len(eu_articles) == 2
    locales = {a.locale for a in eu_articles}
    assert locales == {"en-us", "es-es"}


@pytest.mark.asyncio
async def test_get_by_source_category(temp_db):
    """Test retrieving articles by source category."""
    source_lol = ArticleSource.create("lol", "en-us")
    source_u_gg = ArticleSource.create("u-gg", "en-us")

    articles = [
        Article(
            title="Riot Article 1",
            url="https://example.com/riot-1",
            pub_date=datetime(2025, 12, 25),
            guid="riot-1",
            source=source_lol,
        ),
        Article(
            title="Analytics Article",
            url="https://example.com/analytics",
            pub_date=datetime(2025, 12, 26),
            guid="analytics-1",
            source=source_u_gg,
        ),
        Article(
            title="Riot Article 2",
            url="https://example.com/riot-2",
            pub_date=datetime(2025, 12, 27),
            guid="riot-2",
            source=source_lol,
        ),
    ]

    await temp_db.save_many(articles)

    # Get articles by official_riot category
    riot_articles = await temp_db.get_by_source_category("official_riot")
    assert len(riot_articles) == 2
    assert all(a.source_category == "official_riot" for a in riot_articles)

    # Get articles by analytics category
    analytics_articles = await temp_db.get_by_source_category("analytics")
    assert len(analytics_articles) == 1
    assert analytics_articles[0].source_category == "analytics"


@pytest.mark.asyncio
async def test_count_by_locale(temp_db):
    """Test counting articles filtered by locale."""
    source_en = ArticleSource.create("lol", "en-us")
    source_it = ArticleSource.create("lol", "it-it")

    articles = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/{i}",
            pub_date=datetime(2025, 12, 28),
            guid=f"test-{i}",
            source=source_en if i < 3 else source_it,
        )
        for i in range(5)
    ]

    await temp_db.save_many(articles)

    # Count all articles
    total_count = await temp_db.count()
    assert total_count == 5

    # Count only EN-US articles
    en_count = await temp_db.count(locale="en-us")
    assert en_count == 3

    # Count only IT-IT articles
    it_count = await temp_db.count(locale="it-it")
    assert it_count == 2


@pytest.mark.asyncio
async def test_get_locales(temp_db):
    """Test getting list of all locales with articles."""
    source_en = ArticleSource.create("lol", "en-us")
    source_it = ArticleSource.create("lol", "it-it")
    source_es = ArticleSource.create("lol", "es-es")

    articles = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/{i}",
            pub_date=datetime(2025, 12, 28),
            guid=f"test-{i}",
            source=source,
        )
        for i, source in enumerate([source_en, source_it, source_es])
    ]

    await temp_db.save_many(articles)

    locales = await temp_db.get_locales()
    assert set(locales) == {"en-us", "it-it", "es-es"}


@pytest.mark.asyncio
async def test_get_source_categories(temp_db):
    """Test getting list of all source categories with articles."""
    source_lol = ArticleSource.create("lol", "en-us")
    source_u_gg = ArticleSource.create("u-gg", "en-us")

    articles = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/{i}",
            pub_date=datetime(2025, 12, 28),
            guid=f"test-{i}",
            source=source,
        )
        for i, source in enumerate([source_lol, source_u_gg])
    ]

    await temp_db.save_many(articles)

    categories = await temp_db.get_source_categories()
    assert set(categories) == {"official_riot", "analytics"}


@pytest.mark.asyncio
async def test_get_by_canonical_url(temp_db):
    """Test retrieving article by canonical URL."""
    source = ArticleSource.create("lol", "en-us")
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28),
        guid="test-123",
        source=source,
        canonical_url="https://canonical.com/test",
    )

    await temp_db.save(article)

    # Retrieve by canonical URL
    retrieved = await temp_db.get_by_canonical_url("https://canonical.com/test")
    assert retrieved is not None
    assert retrieved.guid == "test-123"
    assert retrieved.canonical_url == "https://canonical.com/test"
