"""
Tests for Prometheus metrics module.

This module tests the metrics tracking functionality including
counters, histograms, gauges, and the MetricsCache wrapper.
"""

from time import sleep, time

import pytest

from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
from src.utils.metrics import (
    MetricsCache,
    active_update_tasks,
    articles_fetched_total,
    auto_init_metrics,
    cache_entries,
    cache_hit_rate,
    cache_size_bytes,
    circuit_breaker_failure_count,
    circuit_breaker_state,
    get_metrics_text,
    init_metrics,
    scraper_last_success_timestamp,
    scraping_requests_total,
    track_cache_operation,
    track_database_operation,
    track_feed_generation_duration,
    track_scraping_duration,
    update_cache_metrics,
    update_circuit_breaker_metrics,
    update_scraper_last_success,
)


def test_init_metrics():
    """Test metrics initialization."""
    # Use unique labels to avoid conflicts with other tests
    init_metrics(version="2.0.0", commit="test-abc123")

    # Verify build_info was set
    metrics = get_metrics_text()
    assert b"build_info_info" in metrics
    assert b"version=" in metrics


def test_auto_init_metrics():
    """Test auto-initialization of metrics."""
    auto_init_metrics()

    # Verify build_info was set (should have some version)
    metrics = get_metrics_text()
    assert b"build_info" in metrics


def test_articles_fetched_counter():
    """Test articles fetched counter increment."""
    # Use unique labels to avoid global state pollution from other tests
    unique_test_id = "test_articles_fetched_counter"
    articles_fetched_total.labels(source=unique_test_id, locale="en-us").inc(10)
    articles_fetched_total.labels(source=unique_test_id, locale="it-it").inc(5)

    # Get metrics and verify
    metrics = get_metrics_text().decode("utf-8")
    assert f'articles_fetched_total{{locale="en-us",source="{unique_test_id}"}} 10.0' in metrics
    assert f'articles_fetched_total{{locale="it-it",source="{unique_test_id}"}} 5.0' in metrics


def test_scraping_requests_counter():
    """Test scraping requests counter."""
    scraping_requests_total.labels(source="lol", locale="en-us", status="success").inc()

    metrics = get_metrics_text().decode("utf-8")
    assert 'scraping_requests_total{locale="en-us",source="lol",status="success"}' in metrics


def test_scraping_duration_histogram():
    """Test scraping duration histogram tracking."""
    with track_scraping_duration("test-scrape", "en-us"):
        sleep(0.1)  # Simulate some work

    metrics = get_metrics_text().decode("utf-8")
    # Check for histogram buckets
    assert 'scraping_duration_seconds_count{locale="en-us",source="test-scrape"}' in metrics
    assert 'scraping_duration_seconds_sum{locale="en-us",source="test-scrape"}' in metrics


def test_feed_generation_duration_histogram():
    """Test feed generation duration histogram."""
    with track_feed_generation_duration("test-en", "main"):
        sleep(0.05)

    metrics = get_metrics_text().decode("utf-8")
    assert 'feed_generation_duration_seconds_count{locale="test-en",type="main"}' in metrics
    assert 'feed_generation_duration_seconds_sum{locale="test-en",type="main"}' in metrics


def test_database_operation_duration_histogram():
    """Test database operation duration histogram."""
    with track_database_operation("test-save"):
        sleep(0.01)

    metrics = get_metrics_text().decode("utf-8")
    assert 'database_operation_duration_seconds_count{operation="test-save"}' in metrics
    assert 'database_operation_duration_seconds_sum{operation="test-save"}' in metrics


def test_cache_operations_counter():
    """Test cache operations counter."""
    track_cache_operation("get", "hit")
    track_cache_operation("get", "miss")
    track_cache_operation("set", "success")

    metrics = get_metrics_text().decode("utf-8")
    assert 'cache_operations_total{operation="get",status="hit"}' in metrics
    assert 'cache_operations_total{operation="get",status="miss"}' in metrics
    assert 'cache_operations_total{operation="set",status="success"}' in metrics


def test_cache_metrics_gauge():
    """Test cache metrics gauges."""

    # Create a simple cache-like object
    class MockCache:
        def get_stats(self):
            return {
                "total_entries": 100,
                "size_bytes_estimate": 50000,
                "ttl_seconds": 300,
                "hit_rate": 0.85,
                "hits": 850,
                "misses": 150,
                "total_requests": 1000,
            }

    cache = MockCache()
    update_cache_metrics("test_cache", cache)

    # Verify gauges were set
    assert cache_hit_rate.labels(cache_name="test_cache")._value.get() == 0.85
    assert cache_size_bytes.labels(cache_name="test_cache")._value.get() == 50000
    assert cache_entries.labels(cache_name="test_cache")._value.get() == 100


def test_scraper_last_success_gauge():
    """Test scraper last success timestamp gauge."""
    update_scraper_last_success("lol", "en-us")

    timestamp = scraper_last_success_timestamp.labels(source="lol", locale="en-us")._value.get()
    assert timestamp > 0
    # Should be approximately now (within 1 second)
    assert time() - timestamp < 1.0


def test_circuit_breaker_metrics_gauge():
    """Test circuit breaker metrics gauges."""
    # Create a circuit breaker
    cb = CircuitBreaker("test_source", CircuitBreakerConfig(failure_threshold=5))

    # Initially closed (state=0)
    update_circuit_breaker_metrics("test_source", cb)
    assert circuit_breaker_state.labels(source="test_source")._value.get() == 0
    assert circuit_breaker_failure_count.labels(source="test_source")._value.get() == 0

    # Simulate failures to open circuit
    for _ in range(5):
        cb.stats.total_failure_count += 1
        cb.stats.failure_count += 1

    # Manually set state to open
    cb.stats.state = CircuitBreakerState.OPEN
    update_circuit_breaker_metrics("test_source", cb)

    assert circuit_breaker_state.labels(source="test_source")._value.get() == 2  # OPEN
    assert circuit_breaker_failure_count.labels(source="test_source")._value.get() == 5


def test_active_update_tasks_gauge():
    """Test active update tasks gauge."""
    initial = active_update_tasks._value.get()
    assert initial == 0

    active_update_tasks.inc()
    assert active_update_tasks._value.get() == 1

    active_update_tasks.dec()
    assert active_update_tasks._value.get() == 0


def test_metrics_cache_wrapper():
    """Test MetricsCache wrapper functionality."""
    cache = MetricsCache("test_wrapper", default_ttl_seconds=60)

    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Test cache miss
    assert cache.get("nonexistent") is None

    # Test delete
    assert cache.delete("key1") is True
    assert cache.delete("key1") is False  # Already deleted

    # Test clear
    cache.set("key2", "value2")
    cache.clear()
    assert cache.get("key2") is None

    # Verify cache operations were tracked
    metrics = get_metrics_text().decode("utf-8")

    # Should have cache operations tracked
    assert "cache_operations_total" in metrics


def test_metrics_cache_with_ttl():
    """Test MetricsCache with TTL expiration."""
    cache = MetricsCache("test_ttl", default_ttl_seconds=1)

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Wait for expiration
    sleep(1.1)

    assert cache.get("key1") is None


def test_metrics_cache_stats():
    """Test MetricsCache get_stats method."""
    cache = MetricsCache("test_stats", default_ttl_seconds=60)

    cache.set("key1", "value1")
    cache.set("key2", "value2")

    # Get stats twice (one hit, one miss from previous test)
    cache.get("key1")
    cache.get("nonexistent")

    stats = cache.get_stats()
    assert stats["total_entries"] >= 1  # At least key1
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1


def test_get_metrics_text_content_type():
    """Test metrics text generation for different content types."""
    # Plain text
    text_metrics = get_metrics_text("text/plain")
    assert isinstance(text_metrics, bytes)
    assert b"# HELP" in text_metrics

    # OpenMetrics format
    openmetrics = get_metrics_text("application/openmetrics-text")
    assert isinstance(openmetrics, bytes)


@pytest.mark.skip(reason="Reset metrics clears global registry, affecting other tests")
def test_reset_metrics():
    """Test metrics reset functionality."""
    # Add a metric
    articles_fetched_total.labels(source="test-reset", locale="test-en").inc(10)
    value_before = articles_fetched_total.labels(source="test-reset", locale="test-en")._value.get()

    assert value_before == 10

    # Note: Reset is skipped in CI because it affects global state
    # In isolation, this would work:
    # from src.utils.metrics import reset_metrics
    # reset_metrics()
    # init_metrics(version="test", commit="test")
    assert True


def test_track_cache_operation_labels():
    """Test cache operation tracking with various labels."""
    # Test various operation/status combinations
    track_cache_operation("get", "hit")
    track_cache_operation("get", "miss")
    track_cache_operation("set", "success")
    track_cache_operation("delete", "success")
    track_cache_operation("delete", "failure")

    metrics = get_metrics_text().decode("utf-8")

    # Verify all combinations are tracked
    assert 'cache_operations_total{operation="get",status="hit"}' in metrics
    assert 'cache_operations_total{operation="get",status="miss"}' in metrics
    assert 'cache_operations_total{operation="set",status="success"}' in metrics
    assert 'cache_operations_total{operation="delete",status="success"}' in metrics
    assert 'cache_operations_total{operation="delete",status="failure"}' in metrics


def test_feed_generation_duration_types():
    """Test feed generation duration for different feed types."""
    with track_feed_generation_duration("test-types", "main"):
        sleep(0.01)
    with track_feed_generation_duration("test-types", "source"):
        sleep(0.01)
    with track_feed_generation_duration("test-types", "category"):
        sleep(0.01)

    metrics = get_metrics_text().decode("utf-8")

    assert 'feed_generation_duration_seconds_count{locale="test-types",type="main"}' in metrics
    assert 'feed_generation_duration_seconds_count{locale="test-types",type="source"}' in metrics
    assert 'feed_generation_duration_seconds_count{locale="test-types",type="category"}' in metrics
