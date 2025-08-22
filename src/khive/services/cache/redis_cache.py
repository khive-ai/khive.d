"""Redis cache backend implementation."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from khive.utils import get_logger

from .base import CacheBackend
from .config import CacheConfig
from .models import CacheEntry, CacheStats

logger = get_logger("khive.services.cache.redis")


class RedisCache(CacheBackend):
    """Redis-based cache backend."""

    def __init__(self, config: CacheConfig):
        """Initialize Redis cache backend.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[redis.Redis] = None
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
            self._pool = ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                ssl=self.config.redis_ssl,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                socket_timeout=self.config.socket_timeout,
                decode_responses=True,
            )

            # Create Redis client
            self._redis = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()
            logger.info(
                f"Connected to Redis at {self.config.redis_host}:{self.config.redis_port}"
            )

        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            raise

    async def get(self, key: str) -> Optional[CacheEntry]:
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
            logger.error(f"Unexpected error getting key {key}: {e}")
            self._stats.misses += 1
            if not self.config.fallback_on_error:
                raise
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
                expires_at = (
                    datetime.now(timezone.utc).replace(microsecond=0)
                    + timezone.utc.localize(
                        datetime.fromtimestamp(ttl_seconds)
                    ).utctimetuple()
                )

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
            logger.error(f"Unexpected error setting key {key}: {e}")
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
            logger.error(f"Unexpected error deleting key {key}: {e}")
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
            logger.error(f"Unexpected error checking existence of key {key}: {e}")
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
            logger.error(f"Unexpected error clearing pattern {pattern}: {e}")
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
            logger.error(f"Unexpected error getting stats: {e}")
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
            logger.error(f"Redis health check failed: {e}")
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
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            self._redis = None
            self._pool = None
