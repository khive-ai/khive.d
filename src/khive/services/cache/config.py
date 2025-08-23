"""Cache configuration management."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    """Configuration for cache service."""

    # Redis connection
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str | None = Field(default=None, description="Redis password")
    redis_ssl: bool = Field(default=False, description="Use SSL for Redis connection")

    # Connection pool settings
    max_connections: int = Field(default=10, description="Maximum Redis connections")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    socket_timeout: float = Field(default=5.0, description="Socket timeout in seconds")

    # Cache TTL settings (in seconds)
    planning_ttl: int = Field(
        default=86400, description="Planning results TTL (24 hours)"
    )
    triage_ttl: int = Field(default=21600, description="Triage results TTL (6 hours)")
    complexity_ttl: int = Field(
        default=3600, description="Complexity assessment TTL (1 hour)"
    )
    stats_ttl: int = Field(default=604800, description="Statistics TTL (1 week)")

    # Cache behavior
    enabled: bool = Field(default=True, description="Enable/disable caching")
    fallback_on_error: bool = Field(
        default=True, description="Fallback to computation on cache errors"
    )
    warm_cache_on_startup: bool = Field(
        default=False, description="Warm cache on service startup"
    )

    # Performance settings
    max_key_length: int = Field(default=250, description="Maximum cache key length")
    max_value_size_mb: int = Field(
        default=10, description="Maximum cached value size in MB"
    )
    compression_enabled: bool = Field(
        default=False, description="Enable value compression"
    )

    # Monitoring
    collect_stats: bool = Field(default=True, description="Collect cache statistics")
    log_cache_operations: bool = Field(
        default=False, description="Log cache operations"
    )

    @classmethod
    def from_env(cls) -> CacheConfig:
        """Create configuration from environment variables."""
        return cls(
            redis_host=os.getenv("KHIVE_REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("KHIVE_REDIS_PORT", "6379")),
            redis_db=int(os.getenv("KHIVE_REDIS_DB", "0")),
            redis_password=os.getenv("KHIVE_REDIS_PASSWORD"),
            redis_ssl=os.getenv("KHIVE_REDIS_SSL", "false").lower() == "true",
            max_connections=int(os.getenv("KHIVE_REDIS_MAX_CONNECTIONS", "10")),
            socket_timeout=float(os.getenv("KHIVE_REDIS_TIMEOUT", "5.0")),
            planning_ttl=int(os.getenv("KHIVE_CACHE_PLANNING_TTL", "86400")),
            triage_ttl=int(os.getenv("KHIVE_CACHE_TRIAGE_TTL", "21600")),
            complexity_ttl=int(os.getenv("KHIVE_CACHE_COMPLEXITY_TTL", "3600")),
            enabled=os.getenv("KHIVE_CACHE_ENABLED", "true").lower() == "true",
            fallback_on_error=os.getenv("KHIVE_CACHE_FALLBACK", "true").lower()
            == "true",
            collect_stats=os.getenv("KHIVE_CACHE_COLLECT_STATS", "true").lower()
            == "true",
            log_cache_operations=os.getenv("KHIVE_CACHE_LOG_OPS", "false").lower()
            == "true",
        )

    def get_ttl_for_type(self, cache_type: str) -> int:
        """Get TTL for a specific cache type."""
        ttl_mapping = {
            "planning": self.planning_ttl,
            "triage": self.triage_ttl,
            "complexity": self.complexity_ttl,
            "stats": self.stats_ttl,
        }
        return ttl_mapping.get(cache_type, self.planning_ttl)
