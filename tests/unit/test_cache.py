"""
Tests for caching utilities.

This module tests the TTLCache class for in-memory caching with TTL support.
"""

import pytest
from time import sleep
from src.utils.cache import TTLCache


def test_cache_set_and_get():
    """Test basic cache set and get operations."""
    cache = TTLCache(default_ttl_seconds=60)

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_get_nonexistent():
    """Test that getting non-existent key returns None."""
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_cache_expiration():
    """Test that cache items expire after TTL."""
    cache = TTLCache(default_ttl_seconds=1)

    cache.set("key1", "value1", ttl_seconds=1)
    assert cache.get("key1") == "value1"

    # Wait for expiration
    sleep(1.1)
    assert cache.get("key1") is None


def test_cache_custom_ttl():
    """Test setting custom TTL per item."""
    cache = TTLCache(default_ttl_seconds=60)

    cache.set("key1", "value1", ttl_seconds=100)
    cache.set("key2", "value2", ttl_seconds=1)

    # key1 should still be valid
    assert cache.get("key1") == "value1"

    # key2 should expire quickly
    sleep(1.1)
    assert cache.get("key2") is None
    assert cache.get("key1") == "value1"  # key1 still valid


def test_cache_clear():
    """Test clearing all cache items."""
    cache = TTLCache()

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    cache.clear()

    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_cleanup_expired():
    """Test cleaning up expired items."""
    cache = TTLCache()

    cache.set("key1", "value1", ttl_seconds=1)
    cache.set("key2", "value2", ttl_seconds=100)

    sleep(1.1)

    # Cleanup should remove expired items
    removed = cache.cleanup_expired()
    assert removed == 1

    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"


def test_cache_different_types():
    """Test caching different data types."""
    cache = TTLCache()

    cache.set("string", "value")
    cache.set("int", 42)
    cache.set("list", [1, 2, 3])
    cache.set("dict", {"key": "value"})

    assert cache.get("string") == "value"
    assert cache.get("int") == 42
    assert cache.get("list") == [1, 2, 3]
    assert cache.get("dict") == {"key": "value"}
