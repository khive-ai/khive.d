# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Khive Service Health Monitoring

Provides comprehensive health monitoring for all 8 core khive services:
- dev, git, info, fmt, ci, mcp, new-doc, init

Features:
- Real-time health checks
- Metrics collection (response times, success rates, error patterns)
- Dashboard interface
- Alerting capabilities
- API endpoints for external monitoring integration
"""

from .monitoring_service import MonitoringService
from .parts import (
    HealthStatus,
    ServiceHealth,
    MonitoringRequest,
    MonitoringResponse,
    HealthMetrics,
    AlertConfig,
)

__all__ = [
    "MonitoringService",
    "HealthStatus",
    "ServiceHealth",
    "MonitoringRequest",
    "MonitoringResponse",
    "HealthMetrics",
    "AlertConfig",
]
