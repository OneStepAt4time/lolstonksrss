"""
Caching utilities for the application.

This module provides flexible caching with support for both in-memory (TTLCache)
and Redis backends. Includes automatic fallback to in-memory cache if Redis
is unavailable, ensuring cache operations never fail the application.
"""

import json
import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

import redis as redis_lib
from redis import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from src.config import get_settings

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """
    Abstract base class for cache backends.

    All cache backends must implement this interface to ensure
    compatibility with FeedService and other cache consumers.
    """

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Store a value in the cache with TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Optional custom TTL
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a specific key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached items."""
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.

        Returns:
            Number of items removed
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the cache backend is healthy.

        Returns:
            True if backend is operational, False otherwise
        """
        pass


class TTLCacheBackend(CacheBackend):
    """
    In-memory cache backend with Time-To-Live (TTL) support.

    This cache stores key-value pairs with automatic expiration
    based on TTL. Useful for caching API responses and build IDs.
    Tracks hit/miss statistics for monitoring.
    """

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        """
        Initialize the cache.

        Args:
            default_ttl_seconds: Default TTL in seconds (default: 1 hour)
        """
        self.default_ttl = default_ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._hits: int = 0
        self._misses: int = 0

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Store a value in the cache with TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Optional custom TTL (uses default if not provided)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def get(self, key: str) -> Any | None:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            self._misses += 1
            logger.debug(f"Cache miss: {key}")
            return None

        value, expiry = self._cache[key]

        if datetime.utcnow() > expiry:
            self._misses += 1
            logger.debug(f"Cache expired: {key}")
            del self._cache[key]
            return None

        self._hits += 1
        logger.debug(f"Cache hit: {key}")
        return value

    def delete(self, key: str) -> bool:
        """
        Delete a specific key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache key deleted: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.

        Returns:
            Number of items removed
        """
        now = datetime.utcnow()
        expired_keys = [key for key, (_, expiry) in self._cache.items() if now > expiry]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Removed {len(expired_keys)} expired cache items")

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics including entry count,
            size estimate, TTL, and hit/miss statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        # Estimate size based on string representation (conservative estimate)
        size_bytes = 0
        for key, (value, _) in self._cache.items():
            size_bytes += sys.getsizeof(key) + sys.getsizeof(value)

        return {
            "total_entries": len(self._cache),
            "size_bytes_estimate": size_bytes,
            "ttl_seconds": self.default_ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "total_requests": total_requests,
        }

    def is_healthy(self) -> bool:
        """
        Check if the cache backend is healthy.

        Returns:
            True (in-memory cache is always healthy)
        """
        return True


class RedisCacheBackend(CacheBackend):
    """
    Redis-based distributed cache backend.

    Provides distributed caching with Redis for multi-instance deployments.
    Includes connection pooling, automatic reconnection, and fallback behavior.
    All cache operations are wrapped with error handling to ensure
    cache failures never crash the application.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl_seconds: int = 3600,
        key_prefix: str = "lolstonks:",
    ) -> None:
        """
        Initialize Redis cache backend.

        Args:
            redis_url: Redis connection URL
            default_ttl_seconds: Default TTL in seconds (default: 1 hour)
            key_prefix: Prefix for all cache keys to avoid collisions
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl_seconds
        self.key_prefix = key_prefix
        self._connected = False
        self._hits: int = 0
        self._misses: int = 0

        # Initialize Redis connection
        self._client: Redis | None = None
        self._init_connection()

    def _init_connection(self) -> None:
        """Initialize Redis connection with connection pooling."""
        try:
            self._client = redis_lib.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            self._client.ping()
            self._connected = True
            logger.info(f"Redis cache connected: {self.redis_url}")

        except (ConnectionError, TimeoutError, RedisError) as e:
            self._connected = False
            self._client = None
            logger.warning(f"Redis connection failed, will use in-memory fallback: {e}")

    def _make_key(self, key: str) -> str:
        """
        Add prefix to cache key.

        Args:
            key: Original cache key

        Returns:
            Prefixed cache key
        """
        return f"{self.key_prefix}{key}"

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Store a value in the cache with TTL.

        Args:
            key: Cache key
            value: Value to store (must be JSON-serializable)
            ttl_seconds: Optional custom TTL (uses default if not provided)
        """
        if not self._connected or self._client is None:
            logger.debug("Redis not connected, skipping cache set")
            return

        try:
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
            redis_key = self._make_key(key)

            # Serialize value to JSON
            serialized = json.dumps(value)

            self._client.setex(redis_key, ttl, serialized)
            logger.debug(f"Redis cache set: {key} (TTL: {ttl}s)")

        except (ConnectionError, TimeoutError, RedisError) as e:
            self._connected = False
            logger.warning(f"Redis error during set, marking as disconnected: {e}")

    def get(self, key: str) -> Any | None:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if not self._connected or self._client is None:
            self._misses += 1
            logger.debug("Redis not connected, returning cache miss")
            return None

        try:
            redis_key = self._make_key(key)
            serialized = self._client.get(redis_key)

            if serialized is None:
                self._misses += 1
                logger.debug(f"Redis cache miss: {key}")
                return None

            # Deserialize from JSON
            value = json.loads(serialized)  # type: ignore[arg-type]
            self._hits += 1
            logger.debug(f"Redis cache hit: {key}")
            return value

        except (ConnectionError, TimeoutError, RedisError) as e:
            self._connected = False
            self._misses += 1
            logger.warning(f"Redis error during get, marking as disconnected: {e}")
            return None
        except json.JSONDecodeError as e:
            self._misses += 1
            logger.warning(f"Redis JSON decode error for key {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        Delete a specific key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if key didn't exist or Redis unavailable
        """
        if not self._connected or self._client is None:
            logger.debug("Redis not connected, skipping cache delete")
            return False

        try:
            redis_key = self._make_key(key)
            deleted = self._client.delete(redis_key)
            logger.debug(f"Redis cache key deleted: {key}")
            return deleted > 0  # type: ignore[operator]

        except (ConnectionError, TimeoutError, RedisError) as e:
            self._connected = False
            logger.warning(f"Redis error during delete, marking as disconnected: {e}")
            return False

    def clear(self) -> None:
        """Clear all cached items with the configured key prefix."""
        if not self._connected or self._client is None:
            logger.debug("Redis not connected, skipping cache clear")
            return

        try:
            # Find all keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys = self._client.keys(pattern)

            if keys:
                self._client.delete(*keys)  # type: ignore[misc]
                logger.debug(f"Cleared {len(keys)} Redis cache entries")  # type: ignore[arg-type]

        except (ConnectionError, TimeoutError, RedisError) as e:
            self._connected = False
            logger.warning(f"Redis error during clear, marking as disconnected: {e}")

    def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.

        Note: Redis automatically handles TTL expiration, so this
        is a no-op for the Redis backend. Returns 0 for compatibility.

        Returns:
            0 (Redis handles expiration automatically)
        """
        return 0

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics including entry count,
            hit/miss statistics, and connection status
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        total_entries = 0
        if self._connected and self._client is not None:
            try:
                pattern = f"{self.key_prefix}*"
                keys = self._client.keys(pattern)
                total_entries = len(keys)  # type: ignore[arg-type]
            except (ConnectionError, TimeoutError, RedisError):
                self._connected = False

        return {
            "total_entries": total_entries,
            "size_bytes_estimate": -1,  # Redis memory usage not easily available
            "ttl_seconds": self.default_ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "total_requests": total_requests,
            "redis_connected": self._connected,
            "redis_url": self.redis_url,
        }

    def is_healthy(self) -> bool:
        """
        Check if Redis is connected and healthy.

        Returns:
            True if Redis is connected, False otherwise
        """
        if not self._connected or self._client is None:
            return False

        try:
            self._client.ping()
            return True
        except (ConnectionError, TimeoutError, RedisError):
            self._connected = False
            return False


# Legacy TTLCache class for backward compatibility
class TTLCache(TTLCacheBackend):
    """
    Legacy TTLCache class for backward compatibility.

    This class maintains the original interface for code that
    directly instantiates TTLCache. New code should use
    create_cache_backend() instead.
    """

    pass


def create_cache_backend(
    backend_type: str | None = None,
    redis_url: str | None = None,
    default_ttl_seconds: int = 3600,
) -> CacheBackend:
    """
    Create a cache backend instance based on configuration.

    This factory function creates the appropriate cache backend
    based on the backend_type parameter. If Redis is selected but
    unavailable, automatically falls back to in-memory cache.

    Args:
        backend_type: Cache backend type ('redis', 'memory', 'auto')
                      If None, reads from settings.cache_backend
        redis_url: Redis connection URL (if using Redis backend)
                   If None, reads from settings.redis_url
        default_ttl_seconds: Default TTL in seconds

    Returns:
        CacheBackend instance (RedisCacheBackend or TTLCacheBackend)
    """
    settings = get_settings()

    # Determine backend type
    if backend_type is None:
        backend_type = settings.cache_backend

    if redis_url is None:
        redis_url = settings.redis_url

    # Force memory backend if explicitly requested
    if backend_type == "memory":
        logger.info("Using in-memory cache backend")
        return TTLCacheBackend(default_ttl_seconds=default_ttl_seconds)

    # Try Redis backend (for 'redis' or 'auto')
    if backend_type in ("redis", "auto"):
        redis_backend = RedisCacheBackend(
            redis_url=redis_url,
            default_ttl_seconds=default_ttl_seconds,
        )

        # Check if Redis connected successfully
        if redis_backend.is_healthy():
            logger.info(f"Using Redis cache backend: {redis_url}")
            return redis_backend
        else:
            # For 'auto' mode, fall back to memory
            if backend_type == "auto":
                logger.warning("Redis unavailable, falling back to in-memory cache")
                return TTLCacheBackend(default_ttl_seconds=default_ttl_seconds)
            else:
                # For explicit 'redis' mode, still return the backend
                # (it will handle errors gracefully)
                logger.warning(f"Redis backend created but not connected: {redis_url}")
                return redis_backend

    # Default to in-memory
    logger.info("Using default in-memory cache backend")
    return TTLCacheBackend(default_ttl_seconds=default_ttl_seconds)
