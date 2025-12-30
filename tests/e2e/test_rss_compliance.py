"""Complete RSS 2.0 compliance validation tests for E2E testing."""
import xml.etree.ElementTree as ET

import feedparser
import httpx
import pytest

# BASE_URL is provided by conftest fixture
RSS_20_VERSION = "rss20"
REQUIRED_CHANNEL_ELEMENTS = ["title", "link", "description"]


class RSSComplianceValidator:
    @staticmethod
    def validate_xml_wellformed(xml_content):
        try:
            root = ET.fromstring(xml_content)
            return root
        except ET.ParseError as e:
            pytest.fail(f"XML is not well-formed: {e}")

    @staticmethod
    def validate_rss_version(root):
        assert root.tag == "rss"
        version = root.get("version")
        assert version == "2.0"
        return version

    @staticmethod
    def validate_guid_uniqueness(feed):
        guids = []
        for entry in feed.entries:
            if hasattr(entry, "id"):
                guids.append(entry.id)
        assert len(guids) == len(set(guids))

    @staticmethod
    def validate_pub_date_format(feed):
        for entry in feed.entries:
            if hasattr(entry, "published_parsed"):
                assert entry.published_parsed is not None
                assert isinstance(entry.published_parsed, tuple)
                assert len(entry.published_parsed) == 9

    @staticmethod
    def validate_enclosure_format(feed):
        for entry in feed.entries:
            if hasattr(entry, "enclosures") and entry.enclosures:
                for enclosure in entry.enclosures:
                    assert "href" in enclosure
                    assert "type" in enclosure
                    assert enclosure["href"]
                    assert enclosure["type"].startswith("image/")


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.smoke
async def test_main_feed_rss_version(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert feed.version == RSS_20_VERSION


@pytest.mark.e2e
@pytest.mark.validation
async def test_main_feed_xml_wellformed(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        root = RSSComplianceValidator.validate_xml_wellformed(response.text)
        RSSComplianceValidator.validate_rss_version(root)


@pytest.mark.e2e
@pytest.mark.validation
async def test_required_channel_elements(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        for element in REQUIRED_CHANNEL_ELEMENTS:
            assert hasattr(feed.feed, element)
        assert feed.feed.title
        assert feed.feed.link
        assert feed.feed.description


@pytest.mark.e2e
@pytest.mark.validation
async def test_required_item_elements(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert len(feed.entries) > 0
        for entry in feed.entries:
            assert hasattr(entry, "title") or hasattr(entry, "description")
            assert hasattr(entry, "link")
            assert entry.link


@pytest.mark.e2e
@pytest.mark.validation
async def test_guid_uniqueness(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        RSSComplianceValidator.validate_guid_uniqueness(feed)


@pytest.mark.e2e
@pytest.mark.validation
async def test_pubdate_format(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        RSSComplianceValidator.validate_pub_date_format(feed)


@pytest.mark.e2e
@pytest.mark.validation
async def test_category_format(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        for entry in feed.entries:
            if hasattr(entry, "tags") and entry.tags:
                for tag in entry.tags:
                    assert "term" in tag
                    assert tag["term"]


@pytest.mark.e2e
@pytest.mark.validation
async def test_enclosure_format(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        RSSComplianceValidator.validate_enclosure_format(feed)


@pytest.mark.e2e
@pytest.mark.validation
async def test_charset_encoding(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "charset" in content_type.lower()
        assert "utf-8" in content_type.lower()
        assert response.text.startswith("<?xml")


@pytest.mark.e2e
@pytest.mark.validation
async def test_english_feed_compliance(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed/en-us.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert feed.version == RSS_20_VERSION
        assert len(feed.entries) > 0


@pytest.mark.e2e
@pytest.mark.validation
async def test_italian_feed_compliance(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed/it-it.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert feed.version == RSS_20_VERSION
        assert len(feed.entries) > 0


@pytest.mark.e2e
@pytest.mark.validation
async def test_feed_validation_with_rss_validator(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert len(feed.entries) > 0
        for entry in feed.entries:
            assert hasattr(entry, "title") or hasattr(entry, "description")
            if hasattr(entry, "link"):
                # Allow both absolute and relative URLs
                assert entry.link.startswith("http") or entry.link.startswith("/")
        RSSComplianceValidator.validate_guid_uniqueness(feed)
        RSSComplianceValidator.validate_pub_date_format(feed)


@pytest.mark.e2e
@pytest.mark.validation
async def test_html_escaping(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        try:
            root = RSSComplianceValidator.validate_xml_wellformed(response.text)
            assert root is not None
        except ET.ParseError as e:
            pytest.fail(f"HTML not properly escaped: {e}")


@pytest.mark.e2e
@pytest.mark.validation
async def test_feed_size_limits(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        size_mb = len(response.content) / (1024 * 1024)
        assert size_mb < 5
        feed = feedparser.parse(response.text)
        assert len(feed.entries) <= 200


@pytest.mark.e2e
@pytest.mark.validation
async def test_content_type_header(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/rss+xml" in content_type


@pytest.mark.e2e
@pytest.mark.validation
async def test_cache_headers(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        cache_control = response.headers.get("cache-control", "")
        assert cache_control
        assert "max-age=" in cache_control


@pytest.mark.e2e
@pytest.mark.validation
async def test_multiple_feeds_consistency(BASE_URL):
    feeds_to_test = ["/feed.xml", "/feed/en-us.xml", "/feed/it-it.xml"]
    async with httpx.AsyncClient() as client:
        for feed_path in feeds_to_test:
            response = await client.get(f"{BASE_URL}{feed_path}")
            assert response.status_code == 200
            feed = feedparser.parse(response.text)
            assert feed.version == RSS_20_VERSION
            assert len(feed.entries) > 0


@pytest.mark.e2e
@pytest.mark.validation
async def test_link_elements_valid(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert hasattr(feed.feed, "link")
        assert feed.feed.link.startswith("http")
        for entry in feed.entries:
            if hasattr(entry, "link"):
                # Allow both absolute and relative URLs
                assert entry.link.startswith("http") or entry.link.startswith("/")


@pytest.mark.e2e
@pytest.mark.validation
async def test_xml_declaration(BASE_URL):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        assert response.text.startswith("<?xml")
        assert "version=" in response.text
        assert "encoding=" in response.text
