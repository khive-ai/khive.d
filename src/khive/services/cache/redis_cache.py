"""Redis cache backend implementation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from khive.utils import get_logger

from .base import CacheBackend
from .models import CacheEntry, CacheStats

if TYPE_CHECKING:
    from .config import CacheConfig

logger = get_logger("khive.services.cache.redis")


class RedisCache(CacheBackend):
    """Redis-based cache backend."""

    def __init__(self, config: CacheConfig):
        """Initialize Redis cache backend.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._pool: ConnectionPool | None = None
        self._redis: redis.Redis | None = None
        self._stats = CacheStats()

    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection, creating it if necessary."""
        if self._redis is None:
            await self._connect()
        return self._redis

    async def _connect(self) -> None:
        """Establish Redis connection with pool."""
        try:
            # Create connection pool
            pool_kwargs = {
                "host": self.config.redis_host,
                "port": self.config.redis_port,
                "db": self.config.redis_db,
                "password": self.config.redis_password,
                "max_connections": self.config.max_connections,
                "retry_on_timeout": self.config.retry_on_timeout,
                "socket_timeout": self.config.socket_timeout,
                "decode_responses": True,
            }

            # Only add SSL if it's enabled and supported
            if self.config.redis_ssl:
                pool_kwargs["ssl"] = True

            self._pool = ConnectionPool(**pool_kwargs)

            # Create Redis client
            self._redis = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()
            logger.info(
                f"Connected to Redis at {self.config.redis_host}:{self.config.redis_port}"
            )

        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error connecting to Redis: {e}")
            raise

    async def get(self, key: str) -> CacheEntry | None:
        """Get a cache entry by key."""
        if not self.config.enabled:
            return None

        try:
            redis_client = await self._get_redis()

            # Get value from Redis
            value = await redis_client.get(key)
            if value is None:
                self._stats.misses += 1
                if self.config.log_cache_operations:
                    logger.debug(f"Cache miss: {key}")
                return None

            # Deserialize cache entry
            entry = CacheEntry.from_redis_value(key, value)

            # Check if expired (Redis TTL should handle this, but double-check)
            if entry.is_expired():
                await self.delete(key)
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            if self.config.log_cache_operations:
                logger.debug(f"Cache hit: {key}")

            return entry

        except RedisError as e:
            logger.warning(f"Redis error getting key {key}: {e}")
            self._stats.misses += 1
            if not self.config.fallback_on_error:
                raise
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error for key {key}: {e}")
            # Corrupt data, delete it
            await self.delete(key)
            self._stats.misses += 1
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting key {key}: {e}")
            self._stats.misses += 1
            if not self.config.fallback_on_error:
                raise
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Set a cache entry."""
        if not self.config.enabled:
            return False

        try:
            # Validate key length
            if len(key) > self.config.max_key_length:
                logger.warning(f"Key too long, skipping cache: {key[:50]}...")
                return False

            # Create cache entry
            expires_at = None
            if ttl_seconds:
                from datetime import timedelta

                expires_at = datetime.now(timezone.utc).replace(
                    microsecond=0
                ) + timedelta(seconds=ttl_seconds)

            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                metadata=metadata or {},
            )

            # Serialize entry
            redis_value = entry.to_redis_value()

            # Check value size
            value_size_mb = len(redis_value.encode("utf-8")) / (1024 * 1024)
            if value_size_mb > self.config.max_value_size_mb:
                logger.warning(
                    f"Value too large ({value_size_mb:.2f}MB), skipping cache: {key}"
                )
                return False

            # Store in Redis with TTL
            redis_client = await self._get_redis()
            if ttl_seconds:
                await redis_client.setex(key, ttl_seconds, redis_value)
            else:
                await redis_client.set(key, redis_value)

            if self.config.log_cache_operations:
                logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")

            return True

        except RedisError as e:
            logger.warning(f"Redis error setting key {key}: {e}")
            if not self.config.fallback_on_error:
                raise
            return False
        except Exception as e:
            logger.exception(f"Unexpected error setting key {key}: {e}")
            if not self.config.fallback_on_error:
                raise
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        if not self.config.enabled:
            return False

        try:
            redis_client = await self._get_redis()
            result = await redis_client.delete(key)

            if self.config.log_cache_operations:
                logger.debug(f"Cache delete: {key} (existed: {result > 0})")

            return result > 0

        except RedisError as e:
            logger.warning(f"Redis error deleting key {key}: {e}")
            if not self.config.fallback_on_error:
                raise
            return False
        except Exception as e:
            logger.exception(f"Unexpected error deleting key {key}: {e}")
            if not self.config.fallback_on_error:
                raise
            return False

    async def exists(self, key: str) -> bool:
        """Check if a cache entry exists."""
        if not self.config.enabled:
            return False

        try:
            redis_client = await self._get_redis()
            result = await redis_client.exists(key)
            return result > 0

        except RedisError as e:
            logger.warning(f"Redis error checking existence of key {key}: {e}")
            if not self.config.fallback_on_error:
                raise
            return False
        except Exception as e:
            logger.exception(f"Unexpected error checking existence of key {key}: {e}")
            if not self.config.fallback_on_error:
                raise
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a pattern."""
        if not self.config.enabled:
            return 0

        try:
            redis_client = await self._get_redis()

            # Get all keys matching pattern
            keys = await redis_client.keys(pattern)
            if not keys:
                return 0

            # Delete all matching keys
            deleted = await redis_client.delete(*keys)

            logger.info(f"Cleared {deleted} cache entries matching pattern: {pattern}")
            self._stats.evictions += deleted

            return deleted

        except RedisError as e:
            logger.warning(f"Redis error clearing pattern {pattern}: {e}")
            if not self.config.fallback_on_error:
                raise
            return 0
        except Exception as e:
            logger.exception(f"Unexpected error clearing pattern {pattern}: {e}")
            if not self.config.fallback_on_error:
                raise
            return 0

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        if not self.config.collect_stats:
            return self._stats

        try:
            redis_client = await self._get_redis()

            # Get Redis info
            info = await redis_client.info()

            # Update stats with Redis data
            self._stats.total_keys = info.get("db0", {}).get("keys", 0)
            self._stats.memory_usage_bytes = info.get("used_memory", 0)
            self._stats.calculate_hit_rate()

            return self._stats

        except RedisError as e:
            logger.warning(f"Redis error getting stats: {e}")
            return self._stats
        except Exception as e:
            logger.exception(f"Unexpected error getting stats: {e}")
            return self._stats

    async def health_check(self) -> bool:
        """Check if the cache backend is healthy."""
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            return True

        except (ConnectionError, TimeoutError):
            logger.warning("Redis health check failed: connection error")
            return False
        except Exception as e:
            logger.exception(f"Redis health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the cache backend connection."""
        try:
            if self._redis:
                await self._redis.close()
            if self._pool:
                await self._pool.disconnect()

            logger.info("Redis cache connection closed")

        except Exception as e:
            logger.exception(f"Error closing Redis connection: {e}")
        finally:
            self._redis = None
            self._pool = None

    # Convenience methods for easier testing and simpler usage
    async def get_value(self, key: str) -> Any | None:
        """Get raw value from cache (convenience method)."""
        entry = await self.get(key)
        return entry.value if entry else None

    async def set_value(
        self, key: str, value: Any, ttl_seconds: int | None = None
    ) -> bool:
        """Set raw value in cache (convenience method)."""
        return await self.set(key, value, ttl_seconds)

    async def get_json(self, key: str) -> Any | None:
        """Get JSON-decoded value from cache."""
        return await self.get_value(key)

    async def set_json(
        self, key: str, value: Any, ttl_seconds: int | None = None
    ) -> bool:
        """Set JSON-encoded value in cache."""
        return await self.set_value(key, value, ttl_seconds)
