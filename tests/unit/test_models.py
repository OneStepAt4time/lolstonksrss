"""
Tests for core data models.

This module tests the Article and ArticleSource models, including
validation, serialization, and deserialization.
"""

from datetime import datetime

import pytest

from src.models import Article, ArticleSource


def test_article_creation():
    """Test creating a valid article with all required fields."""
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28, 10, 0, 0),
        guid="test-123",
        source=ArticleSource.LOL_EN_US,
        description="Test description",
        categories=["Game Updates", "Champions"],
    )

    assert article.title == "Test Article"
    assert article.url == "https://example.com/test"
    assert article.source == ArticleSource.LOL_EN_US
    assert len(article.categories) == 2
    assert article.author == "Riot Games"  # Default value


def test_article_minimal_creation():
    """Test creating an article with only required fields."""
    article = Article(
        title="Minimal Article",
        url="https://example.com/minimal",
        pub_date=datetime(2025, 12, 28),
        guid="minimal-123",
        source=ArticleSource.LOL_IT_IT,
    )

    assert article.title == "Minimal Article"
    assert article.description == ""
    assert article.content == ""
    assert article.image_url is None
    assert article.categories == []


def test_article_validation_empty_title():
    """Test that empty title raises ValueError."""
    with pytest.raises(ValueError, match="title cannot be empty"):
        Article(
            title="",
            url="https://example.com/test",
            pub_date=datetime.now(),
            guid="test-123",
            source=ArticleSource.LOL_EN_US,
        )


def test_article_validation_empty_url():
    """Test that empty URL raises ValueError."""
    with pytest.raises(ValueError, match="URL cannot be empty"):
        Article(
            title="Test",
            url="",
            pub_date=datetime.now(),
            guid="test-123",
            source=ArticleSource.LOL_EN_US,
        )


def test_article_validation_empty_guid():
    """Test that empty GUID raises ValueError."""
    with pytest.raises(ValueError, match="GUID cannot be empty"):
        Article(
            title="Test",
            url="https://example.com/test",
            pub_date=datetime.now(),
            guid="",
            source=ArticleSource.LOL_EN_US,
        )


def test_article_to_dict():
    """Test article serialization to dictionary."""
    article = Article(
        title="Test",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28, 10, 30, 0),
        guid="test-123",
        source=ArticleSource.LOL_EN_US,
        categories=["Cat1", "Cat2"],
        description="Test description",
        image_url="https://example.com/image.jpg",
    )

    data = article.to_dict()
    assert data["title"] == "Test"
    assert data["url"] == "https://example.com/test"
    assert data["guid"] == "test-123"
    assert data["source"] == "lol-en-us"
    assert data["categories"] == "Cat1,Cat2"
    assert data["description"] == "Test description"
    assert data["image_url"] == "https://example.com/image.jpg"
    assert "pub_date" in data
    assert "created_at" in data


def test_article_from_dict():
    """Test article deserialization from dictionary."""
    data = {
        "title": "Test",
        "url": "https://example.com/test",
        "pub_date": "2025-12-28T10:00:00",
        "guid": "test-123",
        "source": "lol-en-us",
        "categories": "Cat1,Cat2",
        "description": "Test description",
        "author": "Riot Games",
        "created_at": "2025-12-28T09:00:00",
    }

    article = Article.from_dict(data)
    assert article.title == "Test"
    assert article.url == "https://example.com/test"
    assert article.guid == "test-123"
    assert article.source == ArticleSource.LOL_EN_US
    assert len(article.categories) == 2
    assert article.categories[0] == "Cat1"
    assert article.description == "Test description"


def test_article_from_dict_empty_categories():
    """Test deserialization with empty categories."""
    data = {
        "title": "Test",
        "url": "https://example.com/test",
        "pub_date": "2025-12-28T10:00:00",
        "guid": "test-123",
        "source": "lol-en-us",
        "categories": "",
    }

    article = Article.from_dict(data)
    assert article.categories == []


def test_article_roundtrip():
    """Test that serialization and deserialization are reversible."""
    original = Article(
        title="Roundtrip Test",
        url="https://example.com/roundtrip",
        pub_date=datetime(2025, 12, 28, 15, 45, 30),
        guid="roundtrip-123",
        source=ArticleSource.LOL_IT_IT,
        description="Testing roundtrip",
        categories=["Test", "Roundtrip"],
    )

    # Serialize then deserialize
    data = original.to_dict()
    reconstructed = Article.from_dict(data)

    assert reconstructed.title == original.title
    assert reconstructed.url == original.url
    assert reconstructed.guid == original.guid
    assert reconstructed.source == original.source
    assert reconstructed.categories == original.categories
    assert reconstructed.description == original.description


def test_article_source_enum():
    """Test ArticleSource enum values."""
    assert ArticleSource.LOL_EN_US.value == "lol-en-us"
    assert ArticleSource.LOL_IT_IT.value == "lol-it-it"

    # Test enum from string
    source = ArticleSource("lol-en-us")
    assert source == ArticleSource.LOL_EN_US
