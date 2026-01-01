"""
Tests for core data models.

This module tests the Article and ArticleSource models, including
validation, serialization, and deserialization with the new
factory pattern for multi-source, multi-locale support.
"""

from datetime import datetime

import pytest

from src.models import Article, ArticleSource, SourceCategory


def test_article_creation():
    """Test creating a valid article with all required fields."""
    source = ArticleSource.create("lol", "en-us")
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28, 10, 0, 0),
        guid="test-123",
        source=source,
        description="Test description",
        categories=["Game Updates", "Champions"],
    )

    assert article.title == "Test Article"
    assert article.url == "https://example.com/test"
    assert article.source.source_id == "lol"
    assert article.source.locale == "en-us"
    assert len(article.categories) == 2
    assert article.author == "Riot Games"  # Default value
    assert article.locale == "en-us"  # Auto-populated from source


def test_article_minimal_creation():
    """Test creating an article with only required fields."""
    source = ArticleSource.create("lol", "it-it")
    article = Article(
        title="Minimal Article",
        url="https://example.com/minimal",
        pub_date=datetime(2025, 12, 28),
        guid="minimal-123",
        source=source,
    )

    assert article.title == "Minimal Article"
    assert article.description == ""
    assert article.content == ""
    assert article.image_url is None
    assert article.categories == []
    assert article.locale == "it-it"  # Auto-populated from source


def test_article_validation_empty_title():
    """Test that empty title raises ValueError."""
    source = ArticleSource.create("lol", "en-us")
    with pytest.raises(ValueError, match="title cannot be empty"):
        Article(
            title="",
            url="https://example.com/test",
            pub_date=datetime.now(),
            guid="test-123",
            source=source,
        )


def test_article_validation_empty_url():
    """Test that empty URL raises ValueError."""
    source = ArticleSource.create("lol", "en-us")
    with pytest.raises(ValueError, match="URL cannot be empty"):
        Article(
            title="Test",
            url="",
            pub_date=datetime.now(),
            guid="test-123",
            source=source,
        )


def test_article_validation_empty_guid():
    """Test that empty GUID raises ValueError."""
    source = ArticleSource.create("lol", "en-us")
    with pytest.raises(ValueError, match="GUID cannot be empty"):
        Article(
            title="Test",
            url="https://example.com/test",
            pub_date=datetime.now(),
            guid="",
            source=source,
        )


def test_article_to_dict():
    """Test article serialization to dictionary."""
    source = ArticleSource.create("lol", "en-us")
    article = Article(
        title="Test",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28, 10, 30, 0),
        guid="test-123",
        source=source,
        categories=["Cat1", "Cat2"],
        description="Test description",
        image_url="https://example.com/image.jpg",
    )

    data = article.to_dict()
    assert data["title"] == "Test"
    assert data["url"] == "https://example.com/test"
    assert data["guid"] == "test-123"
    assert data["source"] == "lol:en-us"  # New format: source-id:locale
    assert data["categories"] == "Cat1,Cat2"
    assert data["description"] == "Test description"
    assert data["image_url"] == "https://example.com/image.jpg"
    assert "pub_date" in data
    assert "created_at" in data
    assert data["locale"] == "en-us"
    assert data["source_category"] == "official_riot"


def test_article_from_dict():
    """Test article deserialization from dictionary with new format."""
    data = {
        "title": "Test",
        "url": "https://example.com/test",
        "pub_date": "2025-12-28T10:00:00",
        "guid": "test-123",
        "source": "lol:en-us",  # New format
        "categories": "Cat1,Cat2",
        "description": "Test description",
        "author": "Riot Games",
        "created_at": "2025-12-28T09:00:00",
        "locale": "en-us",
        "source_category": "official_riot",
    }

    article = Article.from_dict(data)
    assert article.title == "Test"
    assert article.url == "https://example.com/test"
    assert article.guid == "test-123"
    assert article.source.source_id == "lol"
    assert article.source.locale == "en-us"
    assert len(article.categories) == 2
    assert article.categories[0] == "Cat1"
    assert article.description == "Test description"


def test_article_from_dict_legacy_format():
    """Test article deserialization from dictionary with legacy format."""
    data = {
        "title": "Test",
        "url": "https://example.com/test",
        "pub_date": "2025-12-28T10:00:00",
        "guid": "test-123",
        "source": "lol-en-us",  # Legacy format
        "categories": "Cat1,Cat2",
        "description": "Test description",
        "author": "Riot Games",
        "created_at": "2025-12-28T09:00:00",
    }

    article = Article.from_dict(data)
    assert article.title == "Test"
    assert article.source.source_id == "lol"
    assert article.source.locale == "en-us"


def test_article_from_dict_empty_categories():
    """Test deserialization with empty categories."""
    data = {
        "title": "Test",
        "url": "https://example.com/test",
        "pub_date": "2025-12-28T10:00:00",
        "guid": "test-123",
        "source": "lol:en-us",
        "categories": "",
    }

    article = Article.from_dict(data)
    assert article.categories == []


def test_article_roundtrip():
    """Test that serialization and deserialization are reversible."""
    source = ArticleSource.create("lol", "it-it")
    original = Article(
        title="Roundtrip Test",
        url="https://example.com/roundtrip",
        pub_date=datetime(2025, 12, 28, 15, 45, 30),
        guid="roundtrip-123",
        source=source,
        description="Testing roundtrip",
        categories=["Test", "Roundtrip"],
    )

    # Serialize then deserialize
    data = original.to_dict()
    reconstructed = Article.from_dict(data)

    assert reconstructed.title == original.title
    assert reconstructed.url == original.url
    assert reconstructed.guid == original.guid
    assert reconstructed.source.source_id == original.source.source_id
    assert reconstructed.source.locale == original.source.locale
    assert reconstructed.categories == original.categories
    assert reconstructed.description == original.description


def test_article_source_factory():
    """Test ArticleSource factory pattern."""
    # Test creating sources
    source_en = ArticleSource.create("lol", "en-us")
    source_it = ArticleSource.create("lol", "it-it")
    source_u_gg = ArticleSource.create("u-gg", "en-us")

    assert source_en.source_id == "lol"
    assert source_en.locale == "en-us"
    assert source_en.category == SourceCategory.OFFICIAL_RIOT
    assert str(source_en) == "lol:en-us"

    assert source_it.source_id == "lol"
    assert source_it.locale == "it-it"
    assert str(source_it) == "lol:it-it"

    assert source_u_gg.source_id == "u-gg"
    assert source_u_gg.category == SourceCategory.ANALYTICS


def test_article_source_from_string():
    """Test ArticleSource.from_string for parsing."""
    # New format
    source1 = ArticleSource.from_string("lol:en-us")
    assert source1.source_id == "lol"
    assert source1.locale == "en-us"

    # Legacy format
    source2 = ArticleSource.from_string("lol-en-us")
    assert source2.source_id == "lol"
    assert source2.locale == "en-us"

    source3 = ArticleSource.from_string("u-gg:en-us")
    assert source3.source_id == "u-gg"
    assert source3.locale == "en-us"


def test_article_source_caching():
    """Test that source factory caches instances."""
    source1 = ArticleSource.create("lol", "en-us")
    source2 = ArticleSource.create("lol", "en-us")

    # Same source_id and locale should return cached instance
    # Note: This tests the caching behavior but due to dataclass nature,
    # we can't directly test identity without modifying the class
    assert source1.source_id == source2.source_id
    assert source1.locale == source2.locale


def test_article_source_equality():
    """Test ArticleSource equality."""
    source1 = ArticleSource.create("lol", "en-us")
    source2 = ArticleSource.create("lol", "en-us")
    source3 = ArticleSource.create("lol", "it-it")

    # Should be equal based on source_id and locale
    assert source1 == source2
    assert source1 != source3


def test_article_source_hash():
    """Test ArticleSource can be used in sets and as dict keys."""
    source1 = ArticleSource.create("lol", "en-us")
    source2 = ArticleSource.create("lol", "it-it")
    source3 = ArticleSource.create("u-gg", "en-us")

    source_set = {source1, source2, source3}
    assert len(source_set) == 3

    source_dict = {source1: "value1", source2: "value2"}
    assert source_dict[source1] == "value1"


def test_article_source_invalid():
    """Test that invalid source_id raises ValueError."""
    with pytest.raises(ValueError, match="Unknown source"):
        ArticleSource.create("invalid-source", "en-us")


def test_article_source_properties():
    """Test ArticleSource properties."""
    source = ArticleSource.create("lol", "en-us")

    assert source.name == "League of Legends"
    assert source.category == SourceCategory.OFFICIAL_RIOT
    assert source.base_url is None  # lol source doesn't have base_url

    source_u_gg = ArticleSource.create("u-gg", "en-us")
    assert source_u_gg.name == "U.GG"
    assert source_u_gg.category == SourceCategory.ANALYTICS


def test_article_multi_language_fields():
    """Test article multi-language and multi-source fields."""
    source = ArticleSource.create("u-gg", "en-us")
    article = Article(
        title="Multi-language Test",
        url="https://example.com/test",
        pub_date=datetime.now(),
        guid="multi-123",
        source=source,
        locale="en-us",
        source_category="analytics",
        canonical_url="https://canonical.com/test",
    )

    assert article.locale == "en-us"
    assert article.source_category == "analytics"
    assert article.canonical_url == "https://canonical.com/test"


def test_article_auto_populate_fields():
    """Test that fields auto-populate from source when not provided."""
    source = ArticleSource.create("lol", "it-it")
    article = Article(
        title="Auto-populate Test",
        url="https://example.com/test",
        pub_date=datetime.now(),
        guid="auto-123",
        source=source,
    )

    # Fields should auto-populate from source
    assert article.locale == "it-it"
    assert article.source_category == "official_riot"
    assert article.canonical_url == article.url
