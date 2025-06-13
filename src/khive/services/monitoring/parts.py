# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status levels for services."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HealthMetrics:
    """Metrics collected for a service over time."""

    response_times: List[float] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    last_success_time: Optional[float] = None
    last_error_time: Optional[float] = None
    total_requests: int = 0
    uptime_start: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.success_count / self.total_requests) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests) * 100

    @property
    def average_response_time(self) -> float:
        """Calculate average response time in seconds."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return time.time() - self.uptime_start

    def add_request(self, response_time: float, success: bool) -> None:
        """Record a new request."""
        self.total_requests += 1
        self.response_times.append(response_time)

        # Keep only last 100 response times for memory efficiency
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]

        current_time = time.time()
        if success:
            self.success_count += 1
            self.last_success_time = current_time
        else:
            self.error_count += 1
            self.last_error_time = current_time


@dataclass
class ServiceHealth:
    """Health information for a single service."""

    name: str
    status: HealthStatus
    last_check: float
    metrics: HealthMetrics
    error_message: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    version: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        """Check if service is degraded."""
        return self.status == HealthStatus.DEGRADED

    @property
    def is_unhealthy(self) -> bool:
        """Check if service is unhealthy."""
        return self.status == HealthStatus.UNHEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check,
            "error_message": self.error_message,
            "dependencies": self.dependencies,
            "version": self.version,
            "metrics": {
                "success_rate": self.metrics.success_rate,
                "error_rate": self.metrics.error_rate,
                "average_response_time": self.metrics.average_response_time,
                "total_requests": self.metrics.total_requests,
                "uptime_seconds": self.metrics.uptime_seconds,
                "last_success_time": self.metrics.last_success_time,
                "last_error_time": self.metrics.last_error_time,
            },
        }


class MonitoringRequest(BaseModel):
    """Request for monitoring operations."""

    command: str = Field(
        ...,
        description="Monitoring command: 'status', 'health', 'metrics', 'dashboard'",
    )
    service_name: Optional[str] = Field(
        None, description="Specific service to monitor (optional)"
    )
    include_metrics: bool = Field(True, description="Include detailed metrics")
    include_history: bool = Field(False, description="Include historical data")
    format: str = Field(
        "json", description="Output format: 'json', 'table', 'dashboard'"
    )


class MonitoringResponse(BaseModel):
    """Response from monitoring operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    timestamp: float = Field(
        default_factory=time.time, description="Response timestamp"
    )
    services: List[Dict[str, Any]] = Field(
        default_factory=list, description="Service health data"
    )
    overall_status: HealthStatus = Field(
        HealthStatus.UNKNOWN, description="Overall system health"
    )
    summary: str = Field("", description="Summary of system health")
    alerts: List[Dict[str, Any]] = Field(
        default_factory=list, description="Active alerts"
    )
    error: Optional[str] = Field(None, description="Error message if operation failed")

    class Config:
        use_enum_values = True


@dataclass
class AlertConfig:
    """Configuration for health alerts."""

    enabled: bool = True
    success_rate_threshold: float = 95.0  # Alert if success rate drops below this
    response_time_threshold: float = (
        5.0  # Alert if avg response time exceeds this (seconds)
    )
    error_rate_threshold: float = 5.0  # Alert if error rate exceeds this percentage
    consecutive_failures_threshold: int = (
        3  # Alert after this many consecutive failures
    )

    # Alert destinations
    log_alerts: bool = True
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)


@dataclass
class Alert:
    """Individual alert instance."""

    service_name: str
    level: AlertLevel
    message: str
    timestamp: float
    metric_name: str
    metric_value: Any
    threshold: Any

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "service_name": self.service_name,
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
        }


# Service definitions for the 8 core khive services
CORE_SERVICES = {
    "dev": {
        "name": "Development Intelligence Service",
        "description": "Code validation, fixing, and diagnostic service",
        "command_module": "khive.commands.dev",
        "health_check_method": "basic_check",
    },
    "git": {
        "name": "Natural Git Operations Service",
        "description": "Natural language git operations for humans and AI",
        "command_module": "khive.commands.git",
        "health_check_method": "basic_check",
    },
    "info": {
        "name": "Information Service",
        "description": "Web search and LLM consultation service",
        "command_module": "khive.commands.info",
        "health_check_method": "api_check",
    },
    "fmt": {
        "name": "Code Formatting Service",
        "description": "Multi-stack code formatting service",
        "command_module": "khive.commands.fmt",
        "health_check_method": "basic_check",
    },
    "ci": {
        "name": "Continuous Integration Service",
        "description": "Testing and CI/CD service",
        "command_module": "khive.commands.ci",
        "health_check_method": "basic_check",
    },
    "mcp": {
        "name": "MCP Operations Service",
        "description": "Model Control Protocol operations service",
        "command_module": "khive.commands.mcp",
        "health_check_method": "connection_check",
    },
    "new-doc": {
        "name": "Document Generation Service",
        "description": "Template-based document scaffolding service",
        "command_module": "khive.commands.new_doc",
        "health_check_method": "basic_check",
    },
    "init": {
        "name": "Project Initialization Service",
        "description": "Project bootstrap and environment setup service",
        "command_module": "khive.commands.init",
        "health_check_method": "basic_check",
    },
}
