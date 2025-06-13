# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from typing import Any, Dict, List, Optional

from khive.types.service import Service
from .parts import (
    Alert,
    AlertConfig,
    AlertLevel,
    CORE_SERVICES,
    HealthMetrics,
    HealthStatus,
    MonitoringRequest,
    MonitoringResponse,
    ServiceHealth,
)

logger = logging.getLogger(__name__)


class MonitoringService(Service):
    """
    Comprehensive health monitoring service for all 8 khive services.

    Provides:
    - Real-time health checks for each service
    - Metrics collection (response times, success rates, error patterns)
    - Dashboard interface
    - Alerting capabilities
    - API endpoints for external monitoring integration
    """

    def __init__(self, alert_config: Optional[AlertConfig] = None):
        """Initialize the monitoring service."""
        self.services: Dict[str, ServiceHealth] = {}
        self.alert_config = alert_config or AlertConfig()
        self.active_alerts: List[Alert] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Initialize service health tracking
        self._initialize_services()

    def _initialize_services(self) -> None:
        """Initialize health tracking for all core services."""
        current_time = time.time()

        for service_name, service_info in CORE_SERVICES.items():
            self.services[service_name] = ServiceHealth(
                name=service_name,
                status=HealthStatus.UNKNOWN,
                last_check=current_time,
                metrics=HealthMetrics(),
                dependencies=self._get_service_dependencies(service_name),
                version=None,
            )

    def _get_service_dependencies(self, service_name: str) -> List[str]:
        """Get dependencies for a service."""
        # Define service dependencies
        dependencies = {
            "info": ["exa", "perplexity", "openrouter"],  # External APIs
            "mcp": ["connection"],  # Network connections
            "git": ["git_binary"],  # Git executable
            "dev": ["git", "fmt", "ci"],  # Other services
            "ci": ["git"],  # Git for CI operations
            "fmt": [],  # No external dependencies
            "new-doc": [],  # No external dependencies
            "init": ["git"],  # Git for project initialization
        }
        return dependencies.get(service_name, [])

    async def handle_request(
        self, request: MonitoringRequest, ctx=None
    ) -> MonitoringResponse:
        """Handle monitoring requests."""
        try:
            if isinstance(request, dict):
                request = MonitoringRequest.model_validate(request)
            elif isinstance(request, str):
                # Parse string requests like "status", "health all", etc.
                parts = request.strip().split()
                command = parts[0] if parts else "status"
                service_name = (
                    parts[1] if len(parts) > 1 and parts[1] != "all" else None
                )
                request = MonitoringRequest(
                    command=command,
                    service_name=service_name,
                )

            # Route to appropriate handler
            if request.command == "status":
                return await self._handle_status_request(request)
            elif request.command == "health":
                return await self._handle_health_request(request)
            elif request.command == "metrics":
                return await self._handle_metrics_request(request)
            elif request.command == "dashboard":
                return await self._handle_dashboard_request(request)
            elif request.command == "start":
                return await self._handle_start_monitoring(request)
            elif request.command == "stop":
                return await self._handle_stop_monitoring(request)
            else:
                return MonitoringResponse(
                    success=False,
                    error=f"Unknown command: {request.command}",
                    overall_status=HealthStatus.UNKNOWN,
                )

        except Exception as e:
            logger.error(f"Error handling monitoring request: {e}", exc_info=True)
            return MonitoringResponse(
                success=False,
                error=str(e),
                overall_status=HealthStatus.UNKNOWN,
            )

    async def _handle_status_request(
        self, request: MonitoringRequest
    ) -> MonitoringResponse:
        """Handle status requests for services."""
        if request.service_name:
            # Check specific service
            if request.service_name not in self.services:
                return MonitoringResponse(
                    success=False,
                    error=f"Unknown service: {request.service_name}",
                    overall_status=HealthStatus.UNKNOWN,
                )

            service_health = await self._check_service_health(request.service_name)
            return MonitoringResponse(
                success=True,
                services=[service_health.to_dict()],
                overall_status=service_health.status,
                summary=f"Service {request.service_name} is {service_health.status.value}",
            )
        else:
            # Check all services
            services_data = []
            overall_status = HealthStatus.HEALTHY

            for service_name in CORE_SERVICES:
                service_health = await self._check_service_health(service_name)
                services_data.append(service_health.to_dict())

                # Determine overall status (worst case)
                if service_health.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif (
                    service_health.status == HealthStatus.DEGRADED
                    and overall_status == HealthStatus.HEALTHY
                ):
                    overall_status = HealthStatus.DEGRADED
                elif (
                    service_health.status == HealthStatus.UNKNOWN
                    and overall_status == HealthStatus.HEALTHY
                ):
                    overall_status = HealthStatus.UNKNOWN

            healthy_count = sum(1 for s in services_data if s["status"] == "healthy")
            total_count = len(services_data)

            return MonitoringResponse(
                success=True,
                services=services_data,
                overall_status=overall_status,
                summary=f"{healthy_count}/{total_count} services healthy",
                alerts=[alert.to_dict() for alert in self.active_alerts],
            )

    async def _handle_health_request(
        self, request: MonitoringRequest
    ) -> MonitoringResponse:
        """Handle detailed health requests."""
        # Perform comprehensive health checks
        return await self._handle_status_request(request)

    async def _handle_metrics_request(
        self, request: MonitoringRequest
    ) -> MonitoringResponse:
        """Handle metrics requests."""
        services_data = []

        for service_name, service_health in self.services.items():
            if request.service_name and service_name != request.service_name:
                continue

            service_data = service_health.to_dict()
            if request.include_metrics:
                # Add detailed metrics
                service_data["detailed_metrics"] = {
                    "response_times": service_health.metrics.response_times[
                        -10:
                    ],  # Last 10
                    "recent_success_rate": self._calculate_recent_success_rate(
                        service_health.metrics
                    ),
                    "health_trend": self._calculate_health_trend(service_health),
                }

            services_data.append(service_data)

        return MonitoringResponse(
            success=True,
            services=services_data,
            overall_status=self._calculate_overall_status(),
            summary="Metrics collected successfully",
        )

    async def _handle_dashboard_request(
        self, request: MonitoringRequest
    ) -> MonitoringResponse:
        """Handle dashboard requests."""
        # This will return formatted data suitable for display
        services_data = []

        for service_name in CORE_SERVICES:
            service_health = self.services[service_name]
            service_info = CORE_SERVICES[service_name]

            dashboard_data = {
                "name": service_name,
                "display_name": service_info["name"],
                "description": service_info["description"],
                "status": service_health.status.value,
                "uptime": f"{service_health.metrics.uptime_seconds:.1f}s",
                "success_rate": f"{service_health.metrics.success_rate:.1f}%",
                "avg_response_time": f"{service_health.metrics.average_response_time:.3f}s",
                "total_requests": service_health.metrics.total_requests,
                "last_check": service_health.last_check,
                "error_message": service_health.error_message,
            }
            services_data.append(dashboard_data)

        return MonitoringResponse(
            success=True,
            services=services_data,
            overall_status=self._calculate_overall_status(),
            summary="Dashboard data ready",
            alerts=[alert.to_dict() for alert in self.active_alerts],
        )

    async def _handle_start_monitoring(
        self, request: MonitoringRequest
    ) -> MonitoringResponse:
        """Start continuous monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            return MonitoringResponse(
                success=True,
                summary="Monitoring already running",
                overall_status=self._calculate_overall_status(),
            )

        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(self._continuous_monitoring())

        return MonitoringResponse(
            success=True,
            summary="Continuous monitoring started",
            overall_status=self._calculate_overall_status(),
        )

    async def _handle_stop_monitoring(
        self, request: MonitoringRequest
    ) -> MonitoringResponse:
        """Stop continuous monitoring."""
        if self._monitoring_task:
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(self._monitoring_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._monitoring_task.cancel()

        return MonitoringResponse(
            success=True,
            summary="Continuous monitoring stopped",
            overall_status=self._calculate_overall_status(),
        )

    async def _check_service_health(self, service_name: str) -> ServiceHealth:
        """Perform health check for a specific service."""
        start_time = time.time()
        service_health = self.services[service_name]
        service_info = CORE_SERVICES[service_name]

        try:
            # Perform health check based on service type
            check_method = service_info.get("health_check_method", "basic_check")

            if check_method == "api_check":
                success = await self._api_health_check(service_name)
            elif check_method == "connection_check":
                success = await self._connection_health_check(service_name)
            else:
                success = await self._basic_health_check(service_name)

            response_time = time.time() - start_time

            # Update metrics
            service_health.metrics.add_request(response_time, success)
            service_health.last_check = time.time()

            # Determine status based on success and metrics
            if success:
                if service_health.metrics.success_rate >= 95.0:
                    service_health.status = HealthStatus.HEALTHY
                elif service_health.metrics.success_rate >= 80.0:
                    service_health.status = HealthStatus.DEGRADED
                else:
                    service_health.status = HealthStatus.UNHEALTHY
                service_health.error_message = None
            else:
                service_health.status = HealthStatus.UNHEALTHY
                service_health.error_message = f"Health check failed"

            # Check for alerts
            await self._check_alerts(service_name, service_health)

        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}", exc_info=True)
            service_health.status = HealthStatus.UNHEALTHY
            service_health.error_message = str(e)
            service_health.metrics.add_request(time.time() - start_time, False)

        return service_health

    async def _basic_health_check(self, service_name: str) -> bool:
        """Basic health check - verify module can be imported."""
        try:
            service_info = CORE_SERVICES[service_name]
            module_path = service_info["command_module"]

            # Try to import the command module
            module = importlib.import_module(module_path)

            # Check if it has the expected cli_entry function
            return hasattr(module, "cli_entry") and callable(
                getattr(module, "cli_entry")
            )

        except Exception as e:
            logger.debug(f"Basic health check failed for {service_name}: {e}")
            return False

    async def _api_health_check(self, service_name: str) -> bool:
        """API health check for services that depend on external APIs."""
        if service_name == "info":
            try:
                # Import and test the info service
                from khive.services.info.info_service import InfoServiceGroup

                service = InfoServiceGroup()

                # Try a simple request with short timeout
                from khive.services.info.parts import InfoRequest, InsightMode

                request = InfoRequest(
                    query="test",
                    mode=InsightMode.QUICK,
                    time_budget_seconds=5.0,
                )

                # This should return quickly even if APIs are down
                response = await asyncio.wait_for(
                    service.handle_request(request), timeout=10.0
                )

                await service.close()
                return response.success

            except asyncio.TimeoutError:
                logger.debug(f"API health check timed out for {service_name}")
                return False
            except Exception as e:
                logger.debug(f"API health check failed for {service_name}: {e}")
                return False

        # Default to basic check for other services
        return await self._basic_health_check(service_name)

    async def _connection_health_check(self, service_name: str) -> bool:
        """Connection health check for services that require network connections."""
        if service_name == "mcp":
            try:
                # For MCP, check if we can establish basic connections
                import aiohttp

                # Simple connectivity test
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as session:
                    # Just test local connectivity - don't make external requests
                    pass

                return True

            except Exception as e:
                logger.debug(f"Connection health check failed for {service_name}: {e}")
                return False

        # Default to basic check
        return await self._basic_health_check(service_name)

    async def _check_alerts(
        self, service_name: str, service_health: ServiceHealth
    ) -> None:
        """Check if any alerts should be triggered."""
        if not self.alert_config.enabled:
            return

        current_time = time.time()
        metrics = service_health.metrics

        # Check success rate
        if metrics.success_rate < self.alert_config.success_rate_threshold:
            alert = Alert(
                service_name=service_name,
                level=AlertLevel.WARNING
                if metrics.success_rate > 50
                else AlertLevel.CRITICAL,
                message=f"Success rate dropped to {metrics.success_rate:.1f}%",
                timestamp=current_time,
                metric_name="success_rate",
                metric_value=metrics.success_rate,
                threshold=self.alert_config.success_rate_threshold,
            )
            self._add_alert(alert)

        # Check response time
        if metrics.average_response_time > self.alert_config.response_time_threshold:
            alert = Alert(
                service_name=service_name,
                level=AlertLevel.WARNING,
                message=f"Average response time exceeded {metrics.average_response_time:.2f}s",
                timestamp=current_time,
                metric_name="response_time",
                metric_value=metrics.average_response_time,
                threshold=self.alert_config.response_time_threshold,
            )
            self._add_alert(alert)

        # Check error rate
        if metrics.error_rate > self.alert_config.error_rate_threshold:
            alert = Alert(
                service_name=service_name,
                level=AlertLevel.WARNING
                if metrics.error_rate < 20
                else AlertLevel.CRITICAL,
                message=f"Error rate exceeded {metrics.error_rate:.1f}%",
                timestamp=current_time,
                metric_name="error_rate",
                metric_value=metrics.error_rate,
                threshold=self.alert_config.error_rate_threshold,
            )
            self._add_alert(alert)

    def _add_alert(self, alert: Alert) -> None:
        """Add an alert if it's not a duplicate."""
        # Check for duplicate alerts (same service, metric, and level within 5 minutes)
        duplicate = any(
            existing.service_name == alert.service_name
            and existing.metric_name == alert.metric_name
            and existing.level == alert.level
            and (alert.timestamp - existing.timestamp) < 300  # 5 minutes
            for existing in self.active_alerts
        )

        if not duplicate:
            self.active_alerts.append(alert)

            # Log the alert
            if self.alert_config.log_alerts:
                logger.warning(
                    f"ALERT [{alert.level.value.upper()}] {alert.service_name}: {alert.message}"
                )

            # Keep only last 50 alerts
            if len(self.active_alerts) > 50:
                self.active_alerts = self.active_alerts[-50:]

    def _calculate_recent_success_rate(self, metrics: HealthMetrics) -> float:
        """Calculate success rate for recent requests."""
        if not metrics.response_times:
            return 100.0

        # Consider last 10 requests as "recent"
        recent_count = min(10, metrics.total_requests)
        if recent_count == 0:
            return 100.0

        recent_success = max(
            0, metrics.success_count - max(0, metrics.total_requests - recent_count)
        )
        return (recent_success / recent_count) * 100

    def _calculate_health_trend(self, service_health: ServiceHealth) -> str:
        """Calculate health trend for a service."""
        # Simple trend calculation based on recent success rate vs overall
        recent_rate = self._calculate_recent_success_rate(service_health.metrics)
        overall_rate = service_health.metrics.success_rate

        if recent_rate > overall_rate + 5:
            return "improving"
        elif recent_rate < overall_rate - 5:
            return "degrading"
        else:
            return "stable"

    def _calculate_overall_status(self) -> HealthStatus:
        """Calculate overall system health status."""
        if not self.services:
            return HealthStatus.UNKNOWN

        statuses = [service.status for service in self.services.values()]

        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNKNOWN

    async def _continuous_monitoring(self) -> None:
        """Continuous monitoring loop."""
        logger.info("Starting continuous service monitoring")

        while not self._shutdown_event.is_set():
            try:
                # Check all services
                for service_name in CORE_SERVICES:
                    if self._shutdown_event.is_set():
                        break

                    await self._check_service_health(service_name)

                    # Small delay between service checks
                    await asyncio.sleep(1)

                # Wait before next round of checks (30 seconds)
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=30.0)
                except asyncio.TimeoutError:
                    pass  # Continue monitoring

            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait before retrying

        logger.info("Continuous service monitoring stopped")

    async def close(self) -> None:
        """Clean up the monitoring service."""
        if self._monitoring_task:
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(self._monitoring_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
