"""
Lock manager for concurrency control in the Artifacts Service.

Provides asyncio-based locking for coordinating document updates.
Based on Gemini Deep Think V2 architecture.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from .exceptions import ConcurrencyError

logger = logging.getLogger(__name__)


class LockManager:
    """
    Manages asynchronous locks keyed by resource identifiers.

    Provides synchronization across concurrent requests within a single service instance.
    Uses asyncio.Lock for efficient coordination without blocking the event loop.

    Note: This implementation is for single-process coordination. For multi-process
    scenarios, consider using file-based locks or distributed lock managers.
    """

    def __init__(self, default_timeout: float = 10.0):
        """
        Initialize the lock manager.

        Args:
            default_timeout: Default timeout in seconds for lock acquisition
        """
        # Stores the asyncio Lock instance for a given key
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._timeout = default_timeout

        # Track lock usage for potential cleanup (production optimization)
        self._lock_usage: dict[str, int] = defaultdict(int)

    @asynccontextmanager
    async def acquire(
        self, resource_key: str, timeout: float | None = None
    ) -> AsyncIterator[None]:
        """
        Acquires a lock for the given resource key with a timeout.

        Args:
            resource_key: Unique identifier for the resource to lock
            timeout: Timeout in seconds (uses default if None)

        Raises:
            ConcurrencyError: If lock acquisition times out

        Example:
            async with lock_manager.acquire("session_1:deliverable:report.md"):
                # Critical section - only one coroutine can be here
                document = await storage.read(...)
                document.append_contribution(...)
                await storage.save(document)
        """
        effective_timeout = timeout or self._timeout
        lock = self._locks[resource_key]

        # Track usage for cleanup purposes
        self._lock_usage[resource_key] += 1

        logger.debug(f"Attempting to acquire lock for resource: {resource_key}")

        try:
            # Use asyncio.wait_for for timeout control
            async with asyncio.timeout(effective_timeout):
                async with lock:
                    logger.debug(f"Lock acquired for resource: {resource_key}")
                    yield

        except (asyncio.TimeoutError, TimeoutError):
            logger.warning(
                f"Lock acquisition timeout ({effective_timeout}s) for resource: {resource_key}"
            )
            raise ConcurrencyError(
                f"Timeout ({effective_timeout}s) waiting for lock on resource: {resource_key}"
            )
        finally:
            # Lock is automatically released by lionagi's context manager
            logger.debug(f"Lock released for resource: {resource_key}")

            # Note on Cleanup: In a long-running production system, unused locks should be pruned
            # from self._locks (e.g., using reference counting or a background task)
            # to prevent unbounded memory growth if keys are transient.

    def get_lock_stats(self) -> dict[str, dict[str, any]]:
        """
        Get statistics about lock usage (useful for monitoring and debugging).

        Returns:
            Dictionary with lock statistics
        """
        return {
            "total_locks": len(self._locks),
            "lock_usage": dict(self._lock_usage),
            "currently_locked": {
                key: lock.locked() for key, lock in self._locks.items()
            },
        }

    async def cleanup_unused_locks(self, max_locks: int = 1000) -> int:
        """
        Cleanup unused locks to prevent memory leaks in long-running systems.

        Args:
            max_locks: Maximum number of locks to keep

        Returns:
            Number of locks cleaned up
        """
        if len(self._locks) <= max_locks:
            return 0

        # Remove locks that are not currently held and have low usage
        keys_to_remove = []

        for key, lock in self._locks.items():
            if not lock.locked() and self._lock_usage[key] <= 1:
                keys_to_remove.append(key)

        # Keep only the most frequently used locks
        if len(keys_to_remove) > (len(self._locks) - max_locks):
            # Sort by usage and keep the most used ones
            sorted_keys = sorted(
                keys_to_remove, key=lambda k: self._lock_usage[k], reverse=True
            )
            keys_to_remove = sorted_keys[max_locks:]

        # Clean up the selected locks
        for key in keys_to_remove:
            if key in self._locks and not self._locks[key].locked():
                del self._locks[key]
                del self._lock_usage[key]

        cleaned_count = len(keys_to_remove)
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} unused locks")

        return cleaned_count

    def format_lock_key(self, session_id: str, doc_type: str, doc_name: str) -> str:
        """
        Standard format for creating lock keys.

        Args:
            session_id: Session identifier
            doc_type: Document type
            doc_name: Document name

        Returns:
            Formatted lock key
        """
        return f"{session_id}:{doc_type}:{doc_name}"
