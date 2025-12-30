"""E2E tests for all HTTP endpoints."""
import time
import xml.etree.ElementTree as ET

import feedparser
import httpx
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 60


class EndpointMetrics:
    def __init__(self):
        self.results = []

    def add_result(self, endpoint, method, status_code, response_time, success, details=""):
        self.results.append(
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time_ms": round(response_time * 1000, 2),
                "success": success,
                "details": details,
            }
        )

    def get_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
        }


metrics = EndpointMetrics()


def validate_rss_feed(xml_content, expected_version="rss20"):
    validation_errors = []
    warnings = []

    try:
        feed = feedparser.parse(xml_content)

        if feed.version != expected_version:
            validation_errors.append(f"Expected RSS version {expected_version}, got {feed.version}")

        if not feed.feed.get("title"):
            validation_errors.append("Missing feed title")

        if not feed.feed.get("link"):
            validation_errors.append("Missing feed link")

        if len(feed.entries) == 0:
            warnings.append("Feed has no entries")

        for i, entry in enumerate(feed.entries[:5]):
            if not entry.get("title"):
                validation_errors.append(f"Entry {i}: Missing title")
            if not entry.get("link"):
                validation_errors.append(f"Entry {i}: Missing link")

        try:
            ET.fromstring(xml_content)
        except ET.ParseError as e:
            validation_errors.append(f"Invalid XML structure: {e}")

        return {
            "valid": len(validation_errors) == 0,
            "feed_version": feed.version,
            "feed_title": feed.feed.get("title", ""),
            "entry_count": len(feed.entries),
            "errors": validation_errors,
            "warnings": warnings,
            "feed": feed,
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Feed parsing failed: {str(e)}"],
            "warnings": [],
            "feed": None,
        }


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_root_endpoint():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/")
        elapsed = time.time() - start
        metrics.add_result("/", "GET", response.status_code, elapsed, response.status_code == 200)
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_health_check():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/health")
        elapsed = time.time() - start
        assert response.status_code == 200
        data = response.json()
        metrics.add_result(
            "/health", "GET", response.status_code, elapsed, data.get("status") == "healthy"
        )
        assert data["status"] == "healthy"


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_main_feed():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/feed.xml")
        elapsed = time.time() - start
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "rss+xml" in content_type or "xml" in content_type
        validation = validate_rss_feed(response.text)
        metrics.add_result("/feed.xml", "GET", response.status_code, elapsed, validation["valid"])
        assert validation["valid"]
        assert validation["feed_version"] == "rss20"
        assert validation["entry_count"] > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_english_source_feed():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/feed/en-us.xml")
        elapsed = time.time() - start
        assert response.status_code == 200
        validation = validate_rss_feed(response.text)
        metrics.add_result(
            "/feed/en-us.xml", "GET", response.status_code, elapsed, validation["valid"]
        )
        assert validation["valid"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_italian_source_feed():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/feed/it-it.xml")
        elapsed = time.time() - start
        assert response.status_code == 200
        validation = validate_rss_feed(response.text)
        metrics.add_result(
            "/feed/it-it.xml", "GET", response.status_code, elapsed, validation["valid"]
        )
        assert validation["valid"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_invalid_source_feed():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/feed/invalid.xml")
        elapsed = time.time() - start
        metrics.add_result(
            "/feed/invalid.xml", "GET", response.status_code, elapsed, response.status_code == 404
        )
        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_articles():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/api/articles")
        elapsed = time.time() - start
        assert response.status_code == 200
        articles = response.json()
        assert isinstance(articles, list)
        metrics.add_result("/api/articles", "GET", response.status_code, elapsed, True)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_admin_refresh():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(f"{BASE_URL}/admin/refresh")
        elapsed = time.time() - start
        assert response.status_code == 200
        data = response.json()
        metrics.add_result(
            "/admin/refresh", "POST", response.status_code, elapsed, data.get("status") == "success"
        )
        assert data["status"] == "success"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_admin_scheduler_status():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/admin/scheduler/status")
        elapsed = time.time() - start
        assert response.status_code == 200
        data = response.json()
        metrics.add_result("/admin/scheduler/status", "GET", response.status_code, elapsed, True)
        assert "running" in data
        assert "jobs" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_admin_scheduler_trigger():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(f"{BASE_URL}/admin/scheduler/trigger")
        elapsed = time.time() - start
        assert response.status_code == 200
        data = response.json()
        metrics.add_result("/admin/scheduler/trigger", "POST", response.status_code, elapsed, True)
        assert "total_fetched" in data or "error" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openapi_docs():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/docs")
        elapsed = time.time() - start
        metrics.add_result(
            "/docs", "GET", response.status_code, elapsed, response.status_code == 200
        )
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openapi_schema():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/openapi.json")
        elapsed = time.time() - start
        assert response.status_code == 200
        schema = response.json()
        metrics.add_result(
            "/openapi.json",
            "GET",
            response.status_code,
            elapsed,
            "openapi" in schema and "paths" in schema,
        )
        assert "openapi" in schema
        assert "paths" in schema


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_rss_guid_uniqueness():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        guids = [
            entry.get("id") or entry.get("guid")
            for entry in feed.entries
            if entry.get("id") or entry.get("guid")
        ]
        unique_guids = set(guids)
        duplicates = len(guids) - len(unique_guids)
        metrics.add_result("/feed.xml (GUIDs)", "GET", response.status_code, 0, duplicates == 0)
        assert duplicates == 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_feed_encoding():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        _content_type = response.headers.get("content-type", "")
        try:
            response.content.decode("utf-8")
            is_valid_utf8 = True
        except UnicodeDecodeError:
            is_valid_utf8 = False
        metrics.add_result("/feed.xml (encoding)", "GET", response.status_code, 0, is_valid_utf8)
        assert is_valid_utf8


@pytest.fixture(scope="session", autouse=True)
def generate_test_report():
    yield
    print(chr(10) + "=" * 80)
    print("HTTP ENDPOINTS E2E TEST REPORT")
    print("=" * 80)
    summary = metrics.get_summary()
    print(chr(10) + "Summary:")
    print("  Total Tests: {}".format(summary["total_tests"]))
    print("  Passed: {}".format(summary["passed"]))
    print("  Failed: {}".format(summary["failed"]))
    print("  Success Rate: {}".format(summary["success_rate"]))
    print(chr(10) + "Detailed Results:")
    print("-" * 80)
    print("{:<40} {:<8} {:<7} {:<7}".format("Endpoint", "Method", "Status", "Result"))
    print("-" * 80)
    for result in metrics.results:
        status = "PASS" if result["success"] else "FAIL"
        print(
            "{:<40} {:<8} {:<7} {:<7}".format(
                result["endpoint"], result["method"], result["status_code"], status
            )
        )
    print("=" * 80 + chr(10))
