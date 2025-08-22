"""Data models for cache service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """A cached entry with metadata."""

    key: str = Field(..., description="The cache key")
    value: Any = Field(..., description="The cached value")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="When the entry expires")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: str = Field(default="1.0", description="Cache format version")

    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def to_redis_value(self) -> str:
        """Serialize to Redis-compatible JSON string."""
        data = {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "version": self.version,
        }
        return json.dumps(data, default=str)

    @classmethod
    def from_redis_value(cls, key: str, redis_value: str) -> CacheEntry:
        """Deserialize from Redis JSON string."""
        data = json.loads(redis_value)

        # Parse datetime strings
        created_at = datetime.fromisoformat(data["created_at"])
        expires_at = (
            datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None
        )

        return cls(
            key=key,
            value=data["value"],
            created_at=created_at,
            expires_at=expires_at,
            metadata=data.get("metadata", {}),
            version=data.get("version", "1.0"),
        )


class CacheStats(BaseModel):
    """Cache statistics and metrics."""

    total_keys: int = Field(0, description="Total number of cached keys")
    hits: int = Field(0, description="Cache hits since last reset")
    misses: int = Field(0, description="Cache misses since last reset")
    evictions: int = Field(0, description="Number of evicted entries")
    memory_usage_bytes: Optional[int] = Field(None, description="Memory usage in bytes")
    hit_rate: float = Field(0.0, description="Cache hit rate (0.0-1.0)")

    def calculate_hit_rate(self) -> float:
        """Calculate and update hit rate."""
        total_requests = self.hits + self.misses
        if total_requests == 0:
            self.hit_rate = 0.0
        else:
            self.hit_rate = self.hits / total_requests
        return self.hit_rate


class CacheKey:
    """Utility class for generating consistent cache keys."""

    @staticmethod
    def planning_result(request_hash: str) -> str:
        """Generate key for full planning results."""
        return f"khive:plan:hash:{request_hash}"

    @staticmethod
    def triage_result(request_hash: str) -> str:
        """Generate key for triage results."""
        return f"khive:triage:hash:{request_hash}"

    @staticmethod
    def complexity_assessment(request_hash: str) -> str:
        """Generate key for complexity assessment."""
        return f"khive:complexity:hash:{request_hash}"

    @staticmethod
    def stats() -> str:
        """Generate key for cache statistics."""
        return "khive:meta:stats"

    @staticmethod
    def config() -> str:
        """Generate key for cache configuration."""
        return "khive:meta:config"
