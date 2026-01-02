"""
Tests for caching utilities.

This module tests both TTLCacheBackend (in-memory) and RedisCacheBackend
with comprehensive coverage of cache operations, error handling, and
fallback behavior.
"""

from time import sleep
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError, TimeoutError

from src.utils.cache import (
    CacheBackend,
    RedisCacheBackend,
    TTLCache,
    TTLCacheBackend,
    create_cache_backend,
)


class TestTTLCacheBackend:
    """Tests for in-memory TTLCacheBackend."""

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = TTLCacheBackend(default_ttl_seconds=60)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_get_nonexistent(self):
        """Test that getting non-existent key returns None."""
        cache = TTLCacheBackend()
        assert cache.get("nonexistent") is None

    def test_cache_expiration(self):
        """Test that cache items expire after TTL."""
        cache = TTLCacheBackend(default_ttl_seconds=1)

        cache.set("key1", "value1", ttl_seconds=1)
        assert cache.get("key1") == "value1"

        # Wait for expiration
        sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_custom_ttl(self):
        """Test setting custom TTL per item."""
        cache = TTLCacheBackend(default_ttl_seconds=60)

        cache.set("key1", "value1", ttl_seconds=100)
        cache.set("key2", "value2", ttl_seconds=1)

        # key1 should still be valid
        assert cache.get("key1") == "value1"

        # key2 should expire quickly
        sleep(1.1)
        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"  # key1 still valid

    def test_cache_clear(self):
        """Test clearing all cache items."""
        cache = TTLCacheBackend()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_cleanup_expired(self):
        """Test cleaning up expired items."""
        cache = TTLCacheBackend()

        cache.set("key1", "value1", ttl_seconds=1)
        cache.set("key2", "value2", ttl_seconds=100)

        sleep(1.1)

        # Cleanup should remove expired items
        removed = cache.cleanup_expired()
        assert removed == 1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cache_different_types(self):
        """Test caching different data types."""
        cache = TTLCacheBackend()

        cache.set("string", "value")
        cache.set("int", 42)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"key": "value"})

        assert cache.get("string") == "value"
        assert cache.get("int") == 42
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"key": "value"}

    def test_cache_delete(self):
        """Test deleting specific cache key."""
        cache = TTLCacheBackend()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

        # Delete non-existent key
        assert cache.delete("nonexistent") is False

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = TTLCacheBackend(default_ttl_seconds=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.get("key1")  # hit
        cache.get("key2")  # hit
        cache.get("key3")  # miss

        stats = cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.6667  # Rounded to 4 decimal places
        assert stats["ttl_seconds"] == 60
        assert stats["total_requests"] == 3

    def test_cache_is_healthy(self):
        """Test in-memory cache is always healthy."""
        cache = TTLCacheBackend()
        assert cache.is_healthy() is True

    def test_legacy_ttlcache_compatibility(self):
        """Test that legacy TTLCache class works identically."""
        cache = TTLCache(default_ttl_seconds=60)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Should have is_healthy method from CacheBackend
        assert cache.is_healthy() is True


class TestRedisCacheBackend:
    """Tests for RedisCacheBackend."""

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_init_success(self, mock_from_url):
        """Test successful Redis initialization."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        assert cache._connected is True
        assert cache._client is not None
        mock_client.ping.assert_called_once()

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_init_connection_error(self, mock_from_url):
        """Test Redis initialization with connection error."""
        mock_from_url.side_effect = ConnectionError("Connection refused")

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        assert cache._connected is False
        assert cache._client is None

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_set_and_get(self, mock_from_url):
        """Test Redis set and get operations."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        # Mock the setex/get to return None initially (miss)
        mock_client.get.return_value = None

        cache.set("key1", "value1")
        mock_client.setex.assert_called_once()

        # Test get miss
        result = cache.get("key1")
        assert result is None

        # Test get hit
        mock_client.get.return_value = '"value1"'
        result = cache.get("key1")
        assert result == "value1"

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_set_custom_ttl(self, mock_from_url):
        """Test Redis set with custom TTL."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(
            redis_url="redis://localhost:6379/0",
            default_ttl_seconds=3600,
        )

        cache.set("key1", "value1", ttl_seconds=7200)

        # Check that setex was called with custom TTL
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        # call_args[0] contains positional args: (key, ttl, value)
        assert call_args[0][1] == 7200  # TTL is the second argument

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_delete(self, mock_from_url):
        """Test Redis delete operation."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.delete.return_value = 1
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        result = cache.delete("key1")
        assert result is True
        mock_client.delete.assert_called_once()

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_clear(self, mock_from_url):
        """Test Redis clear operation."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.keys.return_value = ["lolstonks:key1", "lolstonks:key2"]
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        cache.clear()

        mock_client.keys.assert_called_once_with("lolstonks:*")
        mock_client.delete.assert_called_once_with("lolstonks:key1", "lolstonks:key2")

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_stats(self, mock_from_url):
        """Test Redis statistics."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.keys.return_value = ["lolstonks:key1", "lolstonks:key2"]
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        # Simulate some hits and misses
        mock_client.get.return_value = None  # miss first
        cache.get("key1")
        mock_client.get.return_value = '"value"'  # then hit
        cache.get("key1")

        stats = cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["redis_connected"] is True
        assert stats["redis_url"] == "redis://localhost:6379/0"

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_is_healthy(self, mock_from_url):
        """Test Redis health check."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")
        assert cache.is_healthy() is True

        # Simulate connection failure
        mock_client.ping.side_effect = ConnectionError()
        assert cache.is_healthy() is False
        assert cache._connected is False

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_connection_error_during_get(self, mock_from_url):
        """Test Redis handles connection errors during get."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.side_effect = ConnectionError("Connection lost")
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        result = cache.get("key1")
        assert result is None
        assert cache._connected is False

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_connection_error_during_set(self, mock_from_url):
        """Test Redis handles connection errors during set."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.setex.side_effect = TimeoutError("Timeout")
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        # Should not raise exception
        cache.set("key1", "value1")
        assert cache._connected is False

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_not_connected_skips_operations(self, mock_from_url):
        """Test Redis skips operations when not connected."""
        mock_from_url.side_effect = ConnectionError("Connection refused")

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        # All operations should be safe (no exceptions)
        cache.set("key1", "value1")
        result = cache.get("key1")
        deleted = cache.delete("key1")
        cache.clear()

        assert result is None
        assert deleted is False

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_cleanup_expired_noop(self, mock_from_url):
        """Test Redis cleanup_expired returns 0 (no-op)."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        removed = cache.cleanup_expired()
        assert removed == 0

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_key_prefix(self, mock_from_url):
        """Test Redis keys are prefixed correctly."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.delete.return_value = 1
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend(
            redis_url="redis://localhost:6379/0",
            key_prefix="test:",
        )

        cache.set("mykey", "value")
        cache.get("mykey")
        cache.delete("mykey")

        # Check that prefix was added
        setex_call = mock_client.setex.call_args
        assert setex_call[0][0] == "test:mykey"

        get_call = mock_client.get.call_args
        assert get_call[0][0] == "test:mykey"

        delete_call = mock_client.delete.call_args
        assert delete_call[0][0] == "test:mykey"


class TestCreateCacheBackend:
    """Tests for cache backend factory function."""

    @patch("src.utils.cache.get_settings")
    def test_create_memory_backend_explicit(self, mock_settings):
        """Test creating in-memory backend explicitly."""
        mock_settings.return_value = MagicMock(
            cache_backend="auto",
            redis_url="redis://localhost:6379/0",
        )

        backend = create_cache_backend(backend_type="memory")

        assert isinstance(backend, TTLCacheBackend)
        assert not isinstance(backend, RedisCacheBackend)

    @patch("src.utils.cache.redis_lib.from_url")
    @patch("src.utils.cache.get_settings")
    def test_create_redis_backend_connected(self, mock_settings, mock_from_url):
        """Test creating Redis backend when connected."""
        mock_settings.return_value = MagicMock(
            cache_backend="auto",
            redis_url="redis://localhost:6379/0",
        )
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        backend = create_cache_backend(backend_type="redis")

        assert isinstance(backend, RedisCacheBackend)

    @patch("src.utils.cache.redis_lib.from_url")
    @patch("src.utils.cache.get_settings")
    def test_create_auto_backend_with_redis_available(self, mock_settings, mock_from_url):
        """Test auto mode uses Redis when available."""
        mock_settings.return_value = MagicMock(
            cache_backend="auto",
            redis_url="redis://localhost:6379/0",
        )
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        backend = create_cache_backend(backend_type="auto")

        assert isinstance(backend, RedisCacheBackend)

    @patch("src.utils.cache.redis_lib.from_url")
    @patch("src.utils.cache.get_settings")
    def test_create_auto_backend_falls_back_to_memory(self, mock_settings, mock_from_url):
        """Test auto mode falls back to memory when Redis unavailable."""
        mock_settings.return_value = MagicMock(
            cache_backend="auto",
            redis_url="redis://localhost:6379/0",
        )
        mock_from_url.side_effect = ConnectionError("Connection refused")

        backend = create_cache_backend(backend_type="auto")

        assert isinstance(backend, TTLCacheBackend)

    @patch("src.utils.cache.redis_lib.from_url")
    @patch("src.utils.cache.get_settings")
    def test_create_redis_backend_unconnected(self, mock_settings, mock_from_url):
        """Test explicit Redis mode returns backend even if disconnected."""
        mock_settings.return_value = MagicMock(
            cache_backend="auto",
            redis_url="redis://localhost:6379/0",
        )
        mock_from_url.side_effect = ConnectionError("Connection refused")

        backend = create_cache_backend(backend_type="redis")

        # Still returns Redis backend (it will handle errors gracefully)
        assert isinstance(backend, RedisCacheBackend)

    @patch("src.utils.cache.redis_lib.from_url")
    @patch("src.utils.cache.get_settings")
    def test_uses_settings_when_params_not_provided(self, mock_settings, mock_from_url):
        """Test factory uses settings when parameters not provided."""
        mock_settings.return_value = MagicMock(
            cache_backend="memory",
            redis_url="redis://custom:6380/1",
        )

        backend = create_cache_backend()

        assert isinstance(backend, TTLCacheBackend)

    @patch("src.utils.cache.redis_lib.from_url")
    @patch("src.utils.cache.get_settings")
    def test_custom_redis_url(self, mock_settings, mock_from_url):
        """Test factory with custom Redis URL."""
        mock_settings.return_value = MagicMock(
            cache_backend="auto",
            redis_url="redis://localhost:6379/0",
        )
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        create_cache_backend(
            backend_type="redis",
            redis_url="redis://custom:6380/1",
        )

        # Check that the custom URL was used
        mock_from_url.assert_called_once()
        call_args = mock_from_url.call_args
        assert "redis://custom:6380/1" in str(call_args)

    @patch("src.utils.cache.redis_lib.from_url")
    @patch("src.utils.cache.get_settings")
    def test_custom_ttl(self, mock_settings, mock_from_url):
        """Test factory with custom TTL."""
        mock_settings.return_value = MagicMock(
            cache_backend="memory",
            redis_url="redis://localhost:6379/0",
        )

        backend = create_cache_backend(default_ttl_seconds=7200)

        assert backend.default_ttl == 7200


class TestCacheBackendInterface:
    """Tests for CacheBackend abstract interface."""

    def test_cache_backend_is_abstract(self):
        """Test that CacheBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CacheBackend()

    def test_ttl_cache_backend_implements_interface(self):
        """Test that TTLCacheBackend implements all required methods."""
        cache = TTLCacheBackend()

        assert hasattr(cache, "set")
        assert hasattr(cache, "get")
        assert hasattr(cache, "delete")
        assert hasattr(cache, "clear")
        assert hasattr(cache, "cleanup_expired")
        assert hasattr(cache, "get_stats")
        assert hasattr(cache, "is_healthy")

        # All methods should be callable
        assert callable(cache.set)
        assert callable(cache.get)
        assert callable(cache.delete)
        assert callable(cache.clear)
        assert callable(cache.cleanup_expired)
        assert callable(cache.get_stats)
        assert callable(cache.is_healthy)

    @patch("src.utils.cache.redis_lib.from_url")
    def test_redis_cache_backend_implements_interface(self, mock_from_url):
        """Test that RedisCacheBackend implements all required methods."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = RedisCacheBackend()

        assert hasattr(cache, "set")
        assert hasattr(cache, "get")
        assert hasattr(cache, "delete")
        assert hasattr(cache, "clear")
        assert hasattr(cache, "cleanup_expired")
        assert hasattr(cache, "get_stats")
        assert hasattr(cache, "is_healthy")

        # All methods should be callable
        assert callable(cache.set)
        assert callable(cache.get)
        assert callable(cache.delete)
        assert callable(cache.clear)
        assert callable(cache.cleanup_expired)
        assert callable(cache.get_stats)
        assert callable(cache.is_healthy)
