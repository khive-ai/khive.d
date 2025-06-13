# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the monitoring service.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from khive.services.monitoring.monitoring_service import MonitoringService
from khive.services.monitoring.parts import (
    AlertConfig,
    HealthStatus,
    MonitoringRequest,
    MonitoringResponse,
    CORE_SERVICES,
)


class TestMonitoringService:
    """Test the monitoring service functionality."""

    @pytest.fixture
    async def monitoring_service(self):
        """Create a monitoring service for testing."""
        service = MonitoringService()
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_service_initialization(self, monitoring_service):
        """Test that the service initializes properly."""
        assert len(monitoring_service.services) == len(CORE_SERVICES)

        # Check that all core services are tracked
        for service_name in CORE_SERVICES:
            assert service_name in monitoring_service.services
            service_health = monitoring_service.services[service_name]
            assert service_health.name == service_name
            assert service_health.status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_status_request_all_services(self, monitoring_service):
        """Test status request for all services."""
        request = MonitoringRequest(command="status")
        response = await monitoring_service.handle_request(request)

        assert isinstance(response, MonitoringResponse)
        assert response.success
        assert len(response.services) == len(CORE_SERVICES)
        assert response.overall_status in [status for status in HealthStatus]

    @pytest.mark.asyncio
    async def test_status_request_specific_service(self, monitoring_service):
        """Test status request for a specific service."""
        request = MonitoringRequest(command="status", service_name="info")
        response = await monitoring_service.handle_request(request)

        assert response.success
        assert len(response.services) == 1
        assert response.services[0]["name"] == "info"

    @pytest.mark.asyncio
    async def test_status_request_unknown_service(self, monitoring_service):
        """Test status request for unknown service."""
        request = MonitoringRequest(command="status", service_name="unknown")
        response = await monitoring_service.handle_request(request)

        assert not response.success
        assert "Unknown service" in response.error

    @pytest.mark.asyncio
    async def test_health_check_basic(self, monitoring_service):
        """Test basic health check functionality."""
        with patch("importlib.import_module") as mock_import:
            # Mock successful module import
            mock_module = MagicMock()
            mock_module.cli_entry = MagicMock()
            mock_import.return_value = mock_module

            success = await monitoring_service._basic_health_check("dev")
            assert success

            # Test failed import
            mock_import.side_effect = ImportError("Module not found")
            success = await monitoring_service._basic_health_check("dev")
            assert not success

    @pytest.mark.asyncio
    async def test_api_health_check_info_service(self, monitoring_service):
        """Test API health check for info service."""
        with patch(
            "khive.services.info.info_service.InfoServiceGroup"
        ) as mock_service_class:
            # Mock the info service
            mock_service = AsyncMock()
            mock_response = MagicMock()
            mock_response.success = True
            mock_service.handle_request.return_value = mock_response
            mock_service_class.return_value = mock_service

            success = await monitoring_service._api_health_check("info")
            assert success

            # Test failed API check
            mock_response.success = False
            success = await monitoring_service._api_health_check("info")
            assert not success

    @pytest.mark.asyncio
    async def test_metrics_request(self, monitoring_service):
        """Test metrics request."""
        request = MonitoringRequest(command="metrics", include_metrics=True)
        response = await monitoring_service.handle_request(request)

        assert response.success
        assert len(response.services) == len(CORE_SERVICES)

        # Check that metrics are included
        for service_data in response.services:
            assert "metrics" in service_data
            metrics = service_data["metrics"]
            assert "success_rate" in metrics
            assert "error_rate" in metrics
            assert "total_requests" in metrics

    @pytest.mark.asyncio
    async def test_dashboard_request(self, monitoring_service):
        """Test dashboard request."""
        request = MonitoringRequest(command="dashboard")
        response = await monitoring_service.handle_request(request)

        assert response.success
        assert len(response.services) == len(CORE_SERVICES)

        # Check dashboard-specific fields
        for service_data in response.services:
            assert "display_name" in service_data
            assert "description" in service_data
            assert "uptime" in service_data

    @pytest.mark.asyncio
    async def test_continuous_monitoring_start_stop(self, monitoring_service):
        """Test starting and stopping continuous monitoring."""
        # Start monitoring
        start_request = MonitoringRequest(command="start")
        response = await monitoring_service.handle_request(start_request)

        assert response.success
        assert "started" in response.summary.lower()
        assert monitoring_service._monitoring_task is not None

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Stop monitoring
        stop_request = MonitoringRequest(command="stop")
        response = await monitoring_service.handle_request(stop_request)

        assert response.success
        assert "stopped" in response.summary.lower()

    @pytest.mark.asyncio
    async def test_alert_generation(self, monitoring_service):
        """Test alert generation when thresholds are exceeded."""
        # Configure alerts with low thresholds
        monitoring_service.alert_config = AlertConfig(
            success_rate_threshold=99.0,  # Very high threshold
            response_time_threshold=0.001,  # Very low threshold
            error_rate_threshold=1.0,  # Very low threshold
        )

        # Get a service and simulate poor performance
        service_health = monitoring_service.services["dev"]
        service_health.metrics.add_request(10.0, False)  # Slow failed request
        service_health.metrics.add_request(10.0, False)  # Another slow failed request

        # Check for alerts
        await monitoring_service._check_alerts("dev", service_health)

        # Should have generated alerts
        assert len(monitoring_service.active_alerts) > 0

        # Check alert types
        alert_metrics = {
            alert.metric_name for alert in monitoring_service.active_alerts
        }
        assert "success_rate" in alert_metrics
        assert "response_time" in alert_metrics
        assert "error_rate" in alert_metrics

    @pytest.mark.asyncio
    async def test_overall_status_calculation(self, monitoring_service):
        """Test overall status calculation."""
        # All healthy
        for service_health in monitoring_service.services.values():
            service_health.status = HealthStatus.HEALTHY

        assert monitoring_service._calculate_overall_status() == HealthStatus.HEALTHY

        # One degraded
        monitoring_service.services["dev"].status = HealthStatus.DEGRADED
        assert monitoring_service._calculate_overall_status() == HealthStatus.DEGRADED

        # One unhealthy
        monitoring_service.services["info"].status = HealthStatus.UNHEALTHY
        assert monitoring_service._calculate_overall_status() == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_service_dependencies(self, monitoring_service):
        """Test service dependency tracking."""
        # Check that dependencies are correctly identified
        info_service = monitoring_service.services["info"]
        assert (
            "exa" in info_service.dependencies
            or "perplexity" in info_service.dependencies
        )

        git_service = monitoring_service.services["git"]
        assert "git_binary" in git_service.dependencies

        dev_service = monitoring_service.services["dev"]
        assert len(dev_service.dependencies) > 0

    @pytest.mark.asyncio
    async def test_string_request_parsing(self, monitoring_service):
        """Test parsing of string requests."""
        # Test simple status command
        response = await monitoring_service.handle_request("status")
        assert response.success

        # Test status for specific service
        response = await monitoring_service.handle_request("status info")
        assert response.success
        assert len(response.services) == 1

        # Test metrics command
        response = await monitoring_service.handle_request("metrics")
        assert response.success

    @pytest.mark.asyncio
    async def test_health_trend_calculation(self, monitoring_service):
        """Test health trend calculation."""
        service_health = monitoring_service.services["dev"]

        # Add some requests to establish a trend
        for _ in range(5):
            service_health.metrics.add_request(0.1, True)  # Old successful requests

        for _ in range(3):
            service_health.metrics.add_request(0.1, False)  # Recent failed requests

        trend = monitoring_service._calculate_health_trend(service_health)
        assert trend in ["improving", "degrading", "stable"]

    @pytest.mark.asyncio
    async def test_error_handling(self, monitoring_service):
        """Test error handling in various scenarios."""
        # Test invalid command
        request = MonitoringRequest(command="invalid")
        response = await monitoring_service.handle_request(request)

        assert not response.success
        assert "Unknown command" in response.error

        # Test with invalid request format
        response = await monitoring_service.handle_request({"invalid": "request"})
        assert not response.success

    def test_health_metrics_calculations(self):
        """Test health metrics calculations."""
        from khive.services.monitoring.parts import HealthMetrics

        metrics = HealthMetrics()

        # Test initial state
        assert metrics.success_rate == 100.0
        assert metrics.error_rate == 0.0
        assert metrics.average_response_time == 0.0

        # Add some requests
        metrics.add_request(0.1, True)
        metrics.add_request(0.2, True)
        metrics.add_request(0.3, False)

        assert metrics.total_requests == 3
        assert metrics.success_count == 2
        assert metrics.error_count == 1
        assert abs(metrics.success_rate - 66.67) < 0.1
        assert abs(metrics.error_rate - 33.33) < 0.1
        assert abs(metrics.average_response_time - 0.2) < 0.01

    def test_service_health_properties(self):
        """Test ServiceHealth property methods."""
        from khive.services.monitoring.parts import ServiceHealth, HealthMetrics

        metrics = HealthMetrics()
        service_health = ServiceHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            last_check=time.time(),
            metrics=metrics,
        )

        assert service_health.is_healthy
        assert not service_health.is_degraded
        assert not service_health.is_unhealthy

        service_health.status = HealthStatus.DEGRADED
        assert not service_health.is_healthy
        assert service_health.is_degraded
        assert not service_health.is_unhealthy

        service_health.status = HealthStatus.UNHEALTHY
        assert not service_health.is_healthy
        assert not service_health.is_degraded
        assert service_health.is_unhealthy

        # Test serialization
        data = service_health.to_dict()
        assert data["name"] == "test"
        assert data["status"] == "unhealthy"
        assert "metrics" in data


if __name__ == "__main__":
    pytest.main([__file__])
