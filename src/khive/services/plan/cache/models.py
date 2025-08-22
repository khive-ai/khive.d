"""Cache-related Pydantic models and configurations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from khive.services.plan.parts import PlannerResponse
from khive.services.plan.triage.complexity_triage import TriageConsensus


class CacheConfig(BaseModel):
    """Configuration for the caching layer."""

    enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    redis_timeout: float = 5.0
    compression_enabled: bool = True
    metrics_enabled: bool = True
    health_checks_enabled: bool = True

    # TTL configurations (in seconds)
    planning_results_ttl: int = 86400  # 24 hours
    triage_results_ttl: int = 43200  # 12 hours
    compositions_ttl: int = 21600  # 6 hours
    sessions_ttl: int = 3600  # 1 hour

    # Cache size limits
    max_memory: str = "1GB"

    class Config:
        extra = "forbid"


@dataclass
class CacheMetrics:
    """Cache performance and health metrics."""

    hit_rate: float  # Cache hit percentage (0.0-1.0)
    miss_rate: float  # Cache miss percentage (0.0-1.0)
    avg_response_time_ms: float  # Average cache response time in milliseconds
    memory_usage_bytes: int  # Redis memory usage in bytes
    key_count: int  # Total number of cached keys
    eviction_count: int  # Number of evicted keys
    error_rate: float  # Cache operation error rate (0.0-1.0)
    total_operations: int  # Total cache operations
    last_updated: datetime  # When metrics were last calculated

    @property
    def memory_usage_mb(self) -> float:
        """Memory usage in megabytes."""
        return self.memory_usage_bytes / (1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "memory_usage_bytes": self.memory_usage_bytes,
            "memory_usage_mb": self.memory_usage_mb,
            "key_count": self.key_count,
            "eviction_count": self.eviction_count,
            "error_rate": self.error_rate,
            "total_operations": self.total_operations,
            "last_updated": self.last_updated.isoformat(),
        }


class CachedPlanningResult(BaseModel):
    """Cached planning result with metadata."""

    planner_response: PlannerResponse
    metadata: dict[str, Any] = Field(default_factory=dict)
    cached_at: datetime = Field(default_factory=datetime.now)
    config_version: str
    hit_count: int = 0

    class Config:
        arbitrary_types_allowed = True


class CachedTriageResult(BaseModel):
    """Cached triage result with metadata."""

    should_escalate: bool
    consensus: TriageConsensus
    metadata: dict[str, Any] = Field(default_factory=dict)
    cached_at: datetime = Field(default_factory=datetime.now)
    hit_count: int = 0

    class Config:
        arbitrary_types_allowed = True


class CacheKey(BaseModel):
    """Structured cache key with components."""

    prefix: str  # e.g., "khive"
    service: str  # e.g., "planning", "triage"
    version: str  # e.g., "v1"
    identifier: str  # hash or specific identifier

    def __str__(self) -> str:
        """Generate Redis key string."""
        return f"{self.prefix}:{self.service}:{self.version}:{self.identifier}"

    @classmethod
    def planning_result(cls, request_hash: str) -> "CacheKey":
        """Create cache key for planning results."""
        return cls(
            prefix="khive",
            service="planning",
            version="v1",
            identifier=request_hash,
        )

    @classmethod
    def triage_result(cls, request_hash: str) -> "CacheKey":
        """Create cache key for triage results."""
        return cls(
            prefix="khive",
            service="triage",
            version="v1",
            identifier=request_hash,
        )

    @classmethod
    def composition(cls, role: str, domain: str) -> "CacheKey":
        """Create cache key for agent compositions."""
        return cls(
            prefix="khive",
            service="composition",
            version="v1",
            identifier=f"{role}:{domain}",
        )

    @classmethod
    def session_template(cls, complexity: str) -> "CacheKey":
        """Create cache key for session templates."""
        return cls(
            prefix="khive",
            service="session",
            version="v1",
            identifier=complexity,
        )

    @classmethod
    def config_version(cls) -> "CacheKey":
        """Create cache key for configuration version."""
        return cls(
            prefix="khive",
            service="config",
            version="v1",
            identifier="current",
        )


class CacheError(Exception):
    """Base exception for cache-related errors."""

    pass


class CacheConnectionError(CacheError):
    """Exception raised when Redis connection fails."""

    pass


class CacheSerializationError(CacheError):
    """Exception raised when serialization/deserialization fails."""

    pass


class CacheKeyError(CacheError):
    """Exception raised for invalid cache keys."""

    pass
