"""
RSS 2.0 Compliance Validation Suite
"""
from datetime import datetime
from xml.etree import ElementTree as ET

import feedparser
import pytest

from src.models import Article, ArticleSource
from src.rss.generator import RSSFeedGenerator


@pytest.fixture
def sample_article():
    return Article(
        title="Test Article",
        url="https://example.com/test",
        pub_date=datetime(2025, 12, 28, 10, 0, 0),
        guid="test-guid",
        source=ArticleSource.create("lol", "en-us"),
        description="Test description",
        content="<p>Test content</p>",
        image_url="https://example.com/image.jpg",
        author="Test Author",
        categories=["News", "Test"],
    )


@pytest.mark.validation
def test_rss_20_version_compliance(sample_article):
    generator = RSSFeedGenerator()
    feed_xml = generator.generate_feed([sample_article], "http://test/feed.xml")
    feed = feedparser.parse(feed_xml)
    assert feed.version == "rss20"


@pytest.mark.validation
def test_required_channel_elements(sample_article):
    generator = RSSFeedGenerator()
    feed_xml = generator.generate_feed([sample_article], "http://test/feed.xml")
    feed = feedparser.parse(feed_xml)
    assert feed.feed.title
    assert feed.feed.link
    assert feed.feed.description


@pytest.mark.validation
def test_xml_well_formed(sample_article):
    generator = RSSFeedGenerator()
    feed_xml = generator.generate_feed([sample_article], "http://test/feed.xml")
    try:
        ET.fromstring(feed_xml)
    except ET.ParseError as e:
        pytest.fail(f"XML is not well-formed: {e}")
