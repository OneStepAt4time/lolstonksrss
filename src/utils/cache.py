"""
Caching utilities for the application.

This module provides simple in-memory caching with TTL support
for API responses and build IDs.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Simple in-memory cache with Time-To-Live (TTL) support.

    This cache stores key-value pairs with automatic expiration
    based on TTL. Useful for caching API responses and build IDs.
    """

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        """
        Initialize the cache.

        Args:
            default_ttl_seconds: Default TTL in seconds (default: 1 hour)
        """
        self.default_ttl = default_ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}

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
            logger.debug(f"Cache miss: {key}")
            return None

        value, expiry = self._cache[key]

        if datetime.utcnow() > expiry:
            logger.debug(f"Cache expired: {key}")
            del self._cache[key]
            return None

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
