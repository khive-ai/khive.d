"""High-level cache service for khive services."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
from typing import TYPE_CHECKING, Any

from khive.utils import get_logger

from .config import CacheConfig
from .models import CacheKey, CacheStats
from .redis_cache import RedisCache

if TYPE_CHECKING:
    from .base import CacheBackend

logger = get_logger("khive.services.cache.service")


class CacheService:
    """High-level cache service that orchestrates cache backends."""

    def __init__(self, config: CacheConfig | None = None):
        """Initialize cache service.

        Args:
            config: Cache configuration. If None, loads from environment.
        """
        self.config = config or CacheConfig.from_env()
        self._backend: CacheBackend | None = None
        self._stats = CacheStats()
        self._initialized = False

        logger.info(f"CacheService initialized with config: {self.config.model_dump()}")

    async def initialize(self) -> None:
        """Initialize the cache service and backend."""
        if self._initialized:
            return

        if not self.config.enabled:
            logger.info("Cache service disabled by configuration")
            return

        try:
            # Initialize Redis backend
            self._backend = RedisCache(self.config)

            # Test connection
            if await self._backend.health_check():
                logger.info("Cache service initialized successfully")
                self._initialized = True
            else:
                logger.error("Cache backend health check failed")
                if not self.config.fallback_on_error:
                    raise ConnectionError("Cache backend unhealthy")

        except Exception as e:
            logger.exception(f"Failed to initialize cache service: {e}")
            if not self.config.fallback_on_error:
                raise

    async def close(self) -> None:
        """Close cache service and backend connections."""
        if self._backend:
            await self._backend.close()
            self._backend = None
        self._initialized = False
        logger.info("Cache service closed")

    def _generate_hash(self, data: str | dict[str, Any]) -> str:
        """Generate consistent hash for cache keys."""
        if isinstance(data, dict):
            # Sort dict for consistent hashing
            data_str = str(sorted(data.items()))
        else:
            data_str = str(data)

        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    async def cache_planning_result(
        self,
        request: str | dict[str, Any],
        result: Any,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Cache planning service results.

        Args:
            request: The original planning request
            result: The planning result to cache
            metadata: Additional metadata to store

        Returns:
            True if cached successfully, False otherwise
        """
        if not self._is_available():
            return False

        try:
            request_hash = self._generate_hash(request)
            cache_key = CacheKey.planning_result(request_hash)
            ttl = self.config.get_ttl_for_type("planning")

            success = await self._backend.set(
                cache_key, result, ttl_seconds=ttl, metadata=metadata or {}
            )

            if success:
                logger.debug(f"Cached planning result for hash {request_hash}")
            else:
                logger.warning(
                    f"Failed to cache planning result for hash {request_hash}"
                )

            return success

        except Exception as e:
            logger.exception(f"Error caching planning result: {e}")
            return False

    async def get_planning_result(self, request: str | dict[str, Any]) -> Any | None:
        """Retrieve cached planning result.

        Args:
            request: The original planning request

        Returns:
            Cached planning result if found, None otherwise
        """
        if not self._is_available():
            return None

        try:
            request_hash = self._generate_hash(request)
            cache_key = CacheKey.planning_result(request_hash)

            entry = await self._backend.get(cache_key)

            if entry and not entry.is_expired():
                logger.debug(f"Cache hit for planning result hash {request_hash}")
                self._stats.hits += 1
                return entry.value
            logger.debug(f"Cache miss for planning result hash {request_hash}")
            self._stats.misses += 1
            return None

        except Exception as e:
            logger.exception(f"Error retrieving planning result: {e}")
            self._stats.misses += 1
            return None

    async def cache_complexity_assessment(
        self,
        request: str | dict[str, Any],
        assessment: Any,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Cache complexity assessment results.

        Args:
            request: The original request
            assessment: The complexity assessment to cache
            metadata: Additional metadata to store

        Returns:
            True if cached successfully, False otherwise
        """
        if not self._is_available():
            return False

        try:
            request_hash = self._generate_hash(request)
            cache_key = CacheKey.complexity_assessment(request_hash)
            ttl = self.config.get_ttl_for_type("complexity")

            success = await self._backend.set(
                cache_key, assessment, ttl_seconds=ttl, metadata=metadata or {}
            )

            if success:
                logger.debug(f"Cached complexity assessment for hash {request_hash}")

            return success

        except Exception as e:
            logger.exception(f"Error caching complexity assessment: {e}")
            return False

    async def get_complexity_assessment(
        self, request: str | dict[str, Any]
    ) -> Any | None:
        """Retrieve cached complexity assessment.

        Args:
            request: The original request

        Returns:
            Cached complexity assessment if found, None otherwise
        """
        if not self._is_available():
            return None

        try:
            request_hash = self._generate_hash(request)
            cache_key = CacheKey.complexity_assessment(request_hash)

            entry = await self._backend.get(cache_key)

            if entry and not entry.is_expired():
                logger.debug(f"Cache hit for complexity assessment hash {request_hash}")
                self._stats.hits += 1
                return entry.value
            logger.debug(f"Cache miss for complexity assessment hash {request_hash}")
            self._stats.misses += 1
            return None

        except Exception as e:
            logger.exception(f"Error retrieving complexity assessment: {e}")
            self._stats.misses += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Generic cache set operation.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            metadata: Additional metadata

        Returns:
            True if set successfully, False otherwise
        """
        if not self._is_available():
            return False

        try:
            return await self._backend.set(key, value, ttl_seconds, metadata)
        except Exception as e:
            logger.exception(f"Error setting cache key {key}: {e}")
            return False

    async def get(self, key: str) -> Any | None:
        """Generic cache get operation.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise
        """
        if not self._is_available():
            return None

        try:
            entry = await self._backend.get(key)

            if entry and not entry.is_expired():
                self._stats.hits += 1
                return entry.value
            self._stats.misses += 1
            return None

        except Exception as e:
            logger.exception(f"Error getting cache key {key}: {e}")
            self._stats.misses += 1
            return None

    async def delete(self, key: str) -> bool:
        """Delete a cache entry.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self._is_available():
            return False

        try:
            return await self._backend.delete(key)
        except Exception as e:
            logger.exception(f"Error deleting cache key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a pattern.

        Args:
            pattern: Pattern to match (Redis glob-style)

        Returns:
            Number of keys deleted
        """
        if not self._is_available():
            return 0

        try:
            return await self._backend.clear_pattern(pattern)
        except Exception as e:
            logger.exception(f"Error clearing cache pattern {pattern}: {e}")
            return 0

    async def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        if not self._is_available():
            return self._stats

        try:
            # Get backend stats and merge with service stats
            backend_stats = await self._backend.get_stats()

            # Update service stats with backend data
            self._stats.total_keys = backend_stats.total_keys
            self._stats.memory_usage_bytes = backend_stats.memory_usage_bytes
            self._stats.calculate_hit_rate()

            return self._stats

        except Exception as e:
            logger.exception(f"Error getting cache stats: {e}")
            return self._stats

    async def health_check(self) -> bool:
        """Check cache service health.

        Returns:
            True if healthy, False otherwise
        """
        if not self.config.enabled:
            return True  # Disabled is considered healthy

        if not self._backend:
            return False

        try:
            return await self._backend.health_check()
        except Exception as e:
            logger.exception(f"Cache health check failed: {e}")
            return False

    def _is_available(self) -> bool:
        """Check if cache service is available for operations."""
        if not self.config.enabled:
            return False

        if not self._initialized:
            # Try to initialize if not already done
            with contextlib.suppress(Exception):
                asyncio.create_task(self.initialize())
            return False

        return self._backend is not None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
