"""
Prometheus metrics export for LoL Stonks RSS application.

This module provides Prometheus metrics for monitoring and alerting,
including article counts, scraping latency, cache statistics, and
circuit breaker states.
"""

import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generic, TypeVar

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)
from prometheus_client.openmetrics.exposition import generate_latest as generate_latest_openmetrics

from src.utils.cache import TTLCache
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry, CircuitBreakerState

T = TypeVar("T")

logger = logging.getLogger(__name__)

# =============================================================================
# Metrics Configuration
# =============================================================================

# Default labels for multi-instance metrics
_default_labels: dict[str, str] = {}

# Histogram buckets for duration metrics (in seconds)
_DEFAULT_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
    float("inf"),
)

# =============================================================================
# Counter Metrics
# =============================================================================

articles_fetched_total = Counter(
    "articles_fetched_total",
    "Total number of articles fetched from sources",
    ["source", "locale"],
)

scraping_requests_total = Counter(
    "scraping_requests_total",
    "Total number of scraping requests",
    ["source", "locale", "status"],
)

feed_generation_requests_total = Counter(
    "feed_generation_requests_total",
    "Total number of feed generation requests",
    ["locale", "status"],
)

cache_operations_total = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    ["operation", "status"],  # operation: get/set/delete, status: hit/miss/success/failure
)

# =============================================================================
# Histogram Metrics
# =============================================================================

scraping_duration_seconds = Histogram(
    "scraping_duration_seconds",
    "Scraping duration in seconds",
    ["source", "locale"],
    buckets=_DEFAULT_BUCKETS,
)

feed_generation_duration_seconds = Histogram(
    "feed_generation_duration_seconds",
    "Feed generation duration in seconds",
    ["locale", "type"],
    buckets=_DEFAULT_BUCKETS,
)

database_operation_duration_seconds = Histogram(
    "database_operation_duration_seconds",
    "Database operation duration in seconds",
    ["operation"],
    buckets=_DEFAULT_BUCKETS,
)

# =============================================================================
# Gauge Metrics
# =============================================================================

cache_hit_rate = Gauge(
    "cache_hit_rate",
    "Cache hit rate (0.0 to 1.0)",
    ["cache_name"],  # cache_name: feed_cache/etc
)

cache_size_bytes = Gauge(
    "cache_size_bytes",
    "Estimated cache size in bytes",
    ["cache_name"],
)

cache_entries = Gauge(
    "cache_entries",
    "Number of entries in cache",
    ["cache_name"],
)

scraper_last_success_timestamp = Gauge(
    "scraper_last_success_timestamp",
    "Unix timestamp of last successful scrape",
    ["source", "locale"],
)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["source"],
)

circuit_breaker_failure_count = Gauge(
    "circuit_breaker_failure_count",
    "Current circuit breaker failure count",
    ["source"],
)

active_update_tasks = Gauge(
    "active_update_tasks",
    "Number of active update tasks",
)

# =============================================================================
# Info Metrics
# =============================================================================

build_info = Info(
    "build_info",
    "Build information",
)


# =============================================================================
# Metrics Update Functions
# =============================================================================


def init_metrics(version: str = "1.0.0", commit: str = "unknown") -> None:
    """
    Initialize metrics with build information.

    Args:
        version: Application version
        commit: Git commit hash
    """
    build_info.info(
        {
            "version": version,
            "commit": commit,
            "build_date": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Metrics initialized: version={version}, commit={commit}")


def update_cache_metrics(cache_name: str, cache: TTLCache) -> None:
    """
    Update cache-related metrics from a TTLCache instance.

    Args:
        cache_name: Name identifier for the cache
        cache: TTLCache instance to extract metrics from
    """
    stats = cache.get_stats()

    # Update hit rate
    hit_rate = stats.get("hit_rate", 0.0)
    cache_hit_rate.labels(cache_name=cache_name).set(hit_rate)

    # Update size in bytes
    size_bytes = stats.get("size_bytes_estimate", 0)
    cache_size_bytes.labels(cache_name=cache_name).set(size_bytes)

    # Update entry count
    entries = stats.get("total_entries", 0)
    cache_entries.labels(cache_name=cache_name).set(entries)


def track_cache_operation(operation: str, status: str) -> None:
    """
    Track a cache operation.

    Args:
        operation: Operation type (get, set, delete)
        status: Operation status (hit, miss, success, failure)
    """
    cache_operations_total.labels(operation=operation, status=status).inc()


def update_circuit_breaker_metrics(source: str, circuit_breaker: CircuitBreaker) -> None:
    """
    Update circuit breaker metrics.

    Args:
        source: Source identifier
        circuit_breaker: CircuitBreaker instance
    """
    # Map state to numeric value (0=closed, 1=half_open, 2=open)
    state_map = {
        CircuitBreakerState.CLOSED: 0,
        CircuitBreakerState.HALF_OPEN: 1,
        CircuitBreakerState.OPEN: 2,
    }

    state_value = state_map.get(circuit_breaker.stats.state, 0)
    circuit_breaker_state.labels(source=source).set(state_value)
    circuit_breaker_failure_count.labels(source=source).set(circuit_breaker.stats.failure_count)


def update_all_circuit_breaker_metrics(registry: CircuitBreakerRegistry) -> None:
    """
    Update metrics for all circuit breakers in a registry.

    Args:
        registry: CircuitBreakerRegistry instance
    """
    for source, cb in registry.get_all().items():
        update_circuit_breaker_metrics(source, cb)


def update_scraper_last_success(source: str, locale: str) -> None:
    """
    Update the last success timestamp for a scraper.

    Args:
        source: Source identifier
        locale: Locale code
    """
    timestamp = time.time()
    scraper_last_success_timestamp.labels(source=source, locale=locale).set(timestamp)


# =============================================================================
# Context Managers for Timing
# =============================================================================


@contextmanager
def track_scraping_duration(source: str, locale: str) -> Iterator[None]:
    """
    Context manager to track scraping duration.

    Usage:
        with track_scraping_duration("lol", "en-us"):
            articles = await scraper.fetch_articles()

    Args:
        source: Source identifier
        locale: Locale code

    Yields:
        None
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        scraping_duration_seconds.labels(source=source, locale=locale).observe(duration)


@contextmanager
def track_feed_generation_duration(locale: str, feed_type: str) -> Iterator[None]:
    """
    Context manager to track feed generation duration.

    Usage:
        with track_feed_generation_duration("en-us", "main"):
            feed_xml = await service.get_main_feed(...)

    Args:
        locale: Locale code
        feed_type: Type of feed (main, source, category)

    Yields:
        None
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        feed_generation_duration_seconds.labels(locale=locale, type=feed_type).observe(duration)


@contextmanager
def track_database_operation(operation: str) -> Iterator[None]:
    """
    Context manager to track database operation duration.

    Usage:
        with track_database_operation("save"):
            await repository.save(article)

    Args:
        operation: Operation name (save, get, count, etc)

    Yields:
        None
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        database_operation_duration_seconds.labels(operation=operation).observe(duration)


# =============================================================================
# Metrics Export
# =============================================================================


def get_metrics_text(content_type: str = "text/plain") -> bytes:
    """
    Generate Prometheus metrics text for export.

    Args:
        content_type: Content type (text/plain or application/openmetrics-text)

    Returns:
        Metrics as bytes
    """
    if content_type == "application/openmetrics-text":
        result = generate_latest_openmetrics(REGISTRY)
        return result if isinstance(result, bytes) else result.encode("utf-8")
    result = generate_latest(REGISTRY)
    return result if isinstance(result, bytes) else result.encode("utf-8")


def get_metrics_registry() -> CollectorRegistry:
    """
    Get the default Prometheus metrics registry.

    Returns:
        CollectorRegistry instance
    """
    return REGISTRY


def reset_metrics() -> None:
    """
    Reset all metrics (useful for testing).

    WARNING: This should only be used in test environments.
    """
    logger.warning("Resetting all metrics (should only be used in tests)")
    # Clear all metrics from the default registry
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)

    # Re-initialize metrics
    init_metrics()


# =============================================================================
# Metrics Helpers
# =============================================================================


def get_git_commit() -> str:
    """
    Get the current git commit hash.

    Returns:
        Commit hash or "unknown" if not available
    """
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Could not get git commit: {e}")
    return "unknown"


def auto_init_metrics() -> None:
    """
    Auto-initialize metrics from environment or git.

    Attempts to get version and commit from environment variables,
    falling back to git commands if not available.
    """
    version = os.getenv("APP_VERSION", "1.0.0")
    commit = os.getenv("GIT_COMMIT", get_git_commit())
    init_metrics(version=version, commit=commit)


# =============================================================================
# MetricsCache Wrapper
# =============================================================================


class MetricsCache(Generic[T]):
    """
    Wrapper around TTLCache that automatically tracks Prometheus metrics.

    This class wraps a TTLCache instance and automatically updates
    Prometheus metrics for cache operations (get, set, delete) and
    periodically updates cache statistics (hit rate, size, entries).

    Example:
        cache = MetricsCache("feed_cache", default_ttl_seconds=300)
        cache.set("key", "value")
        value = cache.get("key")  # Automatically tracks hit/miss
    """

    def __init__(self, cache_name: str, default_ttl_seconds: int = 300) -> None:
        """
        Initialize a metrics-tracked cache.

        Args:
            cache_name: Name identifier for this cache (used in metrics labels)
            default_ttl_seconds: Default TTL in seconds
        """
        self.cache_name = cache_name
        self._cache = TTLCache(default_ttl_seconds=default_ttl_seconds)

    def set(self, key: str, value: T, ttl_seconds: int | None = None) -> None:
        """
        Store a value in the cache with TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Optional custom TTL (uses default if not provided)
        """
        self._cache.set(key, value, ttl_seconds)
        track_cache_operation("set", "success")
        self._update_metrics()

    def get(self, key: str) -> T | None:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        value = self._cache.get(key)
        if value is not None:
            track_cache_operation("get", "hit")
        else:
            track_cache_operation("get", "miss")
        self._update_metrics()
        return value

    def delete(self, key: str) -> bool:
        """
        Delete a specific key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        result = self._cache.delete(key)
        track_cache_operation("delete", "success" if result else "failure")
        self._update_metrics()
        return result

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        track_cache_operation("clear", "success")
        self._update_metrics()

    def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.

        Returns:
            Number of items removed
        """
        removed = self._cache.cleanup_expired()
        track_cache_operation("cleanup", "success")
        self._update_metrics()
        return removed

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics from underlying TTLCache
        """
        return self._cache.get_stats()

    def _update_metrics(self) -> None:
        """Update Prometheus metrics from cache statistics."""
        update_cache_metrics(self.cache_name, self._cache)
