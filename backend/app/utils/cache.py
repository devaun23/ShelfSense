"""
Hybrid caching layer with Redis (production) and in-memory fallback (development).

Usage:
    from app.utils.cache import cache

    # Get cached value
    value = cache.get("user_stats:123")

    # Set with TTL (default 300 seconds)
    cache.set("user_stats:123", {"accuracy": 0.75}, ttl=60)

    # Delete cache entry
    cache.delete("user_stats:123")

    # Decorator for caching function results
    @cached(key_prefix="user_stats", ttl=60)
    def get_user_stats(user_id: str):
        ...
"""

import os
import json
import logging
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)


class TTLCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        self._cache: dict = {}
        self._timestamps: dict = {}
        self._lock = threading.Lock()
        self.maxsize = maxsize
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                expiry = self._timestamps.get(key)
                if expiry and datetime.utcnow() < expiry:
                    return self._cache[key]
                # Expired - clean up
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.maxsize and key not in self._cache:
                self._evict_oldest()

            self._cache[key] = value
            self._timestamps[key] = datetime.utcnow() + timedelta(seconds=ttl)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def _evict_oldest(self) -> None:
        """Evict the oldest entry (by expiry time)."""
        if self._timestamps:
            oldest_key = min(self._timestamps.items(), key=lambda x: x[1])[0]
            del self._cache[oldest_key]
            del self._timestamps[oldest_key]


class RedisCache:
    """Redis-based cache with JSON serialization."""

    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._client = None
        self._redis_url = redis_url or os.getenv("REDIS_URL")

        if self._redis_url:
            try:
                import redis
                self._client = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                # Test connection
                self._client.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, will use in-memory cache: {e}")
                self._client = None

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._client is not None

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self._client:
            return None
        try:
            data = self._client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with TTL."""
        if not self._client:
            return False
        try:
            ttl = ttl or self.default_ttl
            self._client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self._client:
            return False
        try:
            return self._client.delete(key) > 0
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    def clear(self, pattern: str = "*") -> None:
        """Clear cache entries matching pattern."""
        if not self._client:
            return
        try:
            keys = self._client.keys(pattern)
            if keys:
                self._client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")


class HybridCache:
    """
    Hybrid cache that uses Redis when available, falls back to in-memory.

    This provides:
    - Redis for production (distributed, persistent)
    - In-memory for development (fast, no dependencies)
    """

    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._redis = RedisCache(default_ttl=default_ttl)
        self._local = TTLCache(maxsize=maxsize, default_ttl=default_ttl)

    @property
    def backend(self) -> str:
        """Return current cache backend name."""
        return "redis" if self._redis.is_connected else "memory"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self._redis.is_connected:
            return self._redis.get(key)
        return self._local.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        if self._redis.is_connected:
            self._redis.set(key, value, ttl)
        else:
            self._local.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self._redis.is_connected:
            return self._redis.delete(key)
        return self._local.delete(key)

    def clear(self, pattern: str = "*") -> None:
        """Clear cache entries."""
        if self._redis.is_connected:
            self._redis.clear(pattern)
        else:
            self._local.clear()


# Global cache instance
cache = HybridCache(maxsize=1000, default_ttl=300)


def cached(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable[..., str]] = None
):
    """
    Decorator to cache function results.

    Args:
        key_prefix: Prefix for cache key (e.g., "user_stats")
        ttl: Time to live in seconds (default 300)
        key_builder: Optional function to build cache key from args

    Usage:
        @cached(key_prefix="user_stats", ttl=60)
        def get_user_stats(user_id: str):
            # Expensive computation...
            return stats

        # Cache key will be "user_stats:user_123"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            elif args:
                # Use first arg as key (common pattern: user_id)
                cache_key = f"{key_prefix}:{args[0]}"
            else:
                cache_key = key_prefix

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Compute and cache
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        # Add cache invalidation method
        def invalidate(*args, **kwargs):
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            elif args:
                cache_key = f"{key_prefix}:{args[0]}"
            else:
                cache_key = key_prefix
            cache.delete(cache_key)

        wrapper.invalidate = invalidate
        return wrapper

    return decorator


# Convenience function for invalidating user-related caches
def invalidate_user_cache(user_id: str) -> None:
    """Invalidate all caches for a user."""
    cache.delete(f"user_stats:{user_id}")
    cache.delete(f"specialty:{user_id}")
    cache.delete(f"dashboard:{user_id}")
    cache.delete(f"analytics:{user_id}")
