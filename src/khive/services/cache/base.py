"""Abstract base classes for cache backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from .models import CacheEntry, CacheStats


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get a cache entry by key.

        Args:
            key: The cache key

        Returns:
            CacheEntry if found, None otherwise
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Set a cache entry.

        Args:
            key: The cache key
            value: The value to cache
            ttl_seconds: Time to live in seconds (None for default)
            metadata: Additional metadata to store

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a cache entry.

        Args:
            key: The cache key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a cache entry exists.

        Args:
            key: The cache key

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a pattern.

        Args:
            pattern: The pattern to match (Redis glob-style)

        Returns:
            Number of keys deleted
        """
        pass

    @abstractmethod
    async def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the cache backend is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the cache backend connection."""
        pass
