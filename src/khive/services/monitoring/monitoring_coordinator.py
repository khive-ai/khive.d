"""
Monitoring coordinator that orchestrates all monitoring systems.

Provides unified interface for comprehensive system monitoring, coordinating
system performance, application health, business logic monitoring, and alerting.
"""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from .system_monitor import SystemPerformanceMonitor, SystemMetrics
from .health_monitor import ApplicationHealthMonitor, ApplicationHealthMetrics
from .business_monitor import BusinessLogicMonitor, BusinessLogicMetrics
from .alerting_system import MultiTierAlertingSystem, AlertLevel, Alert

logger = logging.getLogger(__name__)


class MonitoringCoordinator:
    """
    Central coordinator for comprehensive monitoring infrastructure.
    
    Orchestrates system performance, application health, business logic monitoring,
    and alerting to provide unified monitoring and alerting for production deployment.
    """
    
    def __init__(
        self,
        monitoring_interval_seconds: int = 60,
        alerting_enabled: bool = True,
        auto_resolve_alerts: bool = True
    ):
        # Initialize monitoring components
        self.system_monitor = SystemPerformanceMonitor()
        self.health_monitor = ApplicationHealthMonitor()
        self.business_monitor = BusinessLogicMonitor()
        self.alerting_system = MultiTierAlertingSystem()
        
        # Configuration
        self.monitoring_interval = monitoring_interval_seconds
        self.alerting_enabled = alerting_enabled
        self.auto_resolve_alerts = auto_resolve_alerts
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.last_monitoring_run: Optional[datetime] = None
        
        # Consolidated metrics history
        self.consolidated_metrics: List[Dict[str, Any]] = []
        self.max_consolidated_history = 2000
        
        # Alert correlation tracking
        self.alert_correlation_cache: Dict[str, List[str]] = {}
        
        # Performance baselines
        self.performance_baselines: Dict[str, float] = {}
        self._last_baseline_calculation: Optional[datetime] = None
        
        # Monitoring statistics
        self.monitoring_stats = {
            "monitoring_cycles": 0,
            "alerts_created": 0,
            "alerts_resolved": 0,
            "monitoring_errors": 0,
            "last_error": None
        }
    
    async def start_monitoring(self):
        """Start continuous monitoring."""
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Monitoring started with {self.monitoring_interval}s interval")
    
    async def stop_monitoring(self):
        """Stop continuous monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                await self._run_monitoring_cycle()
                self.monitoring_stats["monitoring_cycles"] += 1
                self.last_monitoring_run = datetime.now()
                
            except Exception as e:
                logger.error(f"Monitoring cycle failed: {e}", exc_info=True)
                self.monitoring_stats["monitoring_errors"] += 1
                self.monitoring_stats["last_error"] = str(e)
            
            # Wait for next interval
            try:
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
    
    async def _run_monitoring_cycle(self):
        """Execute a complete monitoring cycle."""
        cycle_start = datetime.now()
        
        # Collect metrics from all monitoring systems
        system_metrics = await self.system_monitor.collect_metrics()
        health_metrics = await self.health_monitor.collect_health_metrics()
        business_metrics = await self.business_monitor.collect_business_metrics()
        
        # Consolidate metrics
        consolidated = self._consolidate_metrics(system_metrics, health_metrics, business_metrics)
        self.consolidated_metrics.append(consolidated)
        
        # Trim history
        if len(self.consolidated_metrics) > self.max_consolidated_history:
            self.consolidated_metrics.pop(0)
        
        # Check for threshold violations and create alerts
        if self.alerting_enabled:
            await self._process_alerts(system_metrics, health_metrics, business_metrics)
        
        # Update performance baselines periodically
        await self._update_baselines()
        
        # Auto-resolve alerts if conditions are met
        if self.auto_resolve_alerts:
            await self._auto_resolve_alerts(system_metrics, health_metrics, business_metrics)
        
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        logger.debug(f"Monitoring cycle completed in {cycle_duration:.2f}s")
    
    def _consolidate_metrics(
        self, 
        system_metrics: SystemMetrics,
        health_metrics: ApplicationHealthMetrics,
        business_metrics: BusinessLogicMetrics
    ) -> Dict[str, Any]:
        """Consolidate metrics from all monitoring systems."""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "disk_usage": system_metrics.disk_usage,
                "api_response_times": system_metrics.api_response_times,
                "network_connections": system_metrics.network_connections,
                "websocket_connections": system_metrics.websocket_connections
            },
            "health": {
                "overall_status": health_metrics.overall_status,
                "api_endpoints_up": health_metrics.api_endpoints_up,
                "api_endpoints_total": health_metrics.api_endpoints_total,
                "api_response_time_avg": health_metrics.api_response_time_avg,
                "active_agents": health_metrics.active_agents,
                "agent_success_rate": health_metrics.agent_success_rate,
                "coordination_health": health_metrics.coordination_health
            },
            "business": {
                "cli_success_rate": business_metrics.cli_success_rate_overall,
                "cli_response_time_avg": business_metrics.cli_avg_response_time_ms,
                "orchestration_success_rate": business_metrics.orchestration_success_rate,
                "user_satisfaction": business_metrics.overall_user_satisfaction,
                "optimization_score": business_metrics.optimization_score
            }
        }
    
    async def _process_alerts(
        self,
        system_metrics: SystemMetrics,
        health_metrics: ApplicationHealthMetrics, 
        business_metrics: BusinessLogicMetrics
    ):
        """Process threshold violations and create alerts."""
        
        # System performance alerts
        system_violations = self.system_monitor.check_thresholds(system_metrics)
        for violation in system_violations:
            await self._create_alert_from_violation(violation, "system")
        
        # Application health alerts
        health_violations = self.health_monitor.check_health_violations(health_metrics)
        for violation in health_violations:
            await self._create_alert_from_violation(violation, "application")
        
        # Business logic alerts  
        business_violations = self.business_monitor.check_business_violations(business_metrics)
        for violation in business_violations:
            await self._create_alert_from_violation(violation, "business")
        
        # Correlation-based alerts (detect patterns across systems)
        await self._create_correlation_alerts(system_metrics, health_metrics, business_metrics)
    
    async def _create_alert_from_violation(self, violation: Dict[str, Any], source: str):
        """Create alert from a threshold violation."""
        
        # Determine alert level
        severity = violation.get("severity", "WARNING")
        if severity == "CRITICAL":
            level = AlertLevel.CRITICAL
        elif severity == "WARNING":
            level = AlertLevel.WARNING
        else:
            level = AlertLevel.INFO
        
        # Create alert title and message
        metric_name = violation["metric"]
        current = violation["current"]
        threshold = violation["threshold"]
        
        title = f"{metric_name.replace('_', ' ').title()} Threshold Exceeded"
        message = f"{metric_name} is {current} (threshold: {threshold})"
        
        if "impact" in violation:
            message += f". Impact: {violation['impact']}"
        
        # Add special handling for Ocean's CLI performance target
        if metric_name == "cli_response_time" and "target" in violation:
            message += f". {violation['target']}"
        
        # Create alert
        alert = await self.alerting_system.create_alert(
            level=level,
            title=title,
            message=message,
            source=source,
            metric_name=metric_name,
            current_value=current,
            threshold_value=threshold,
            metadata={
                "violation_data": violation,
                "monitoring_cycle": self.monitoring_stats["monitoring_cycles"]
            }
        )
        
        self.monitoring_stats["alerts_created"] += 1
        logger.info(f"Alert created: {alert.id} - {title}")
    
    async def _create_correlation_alerts(
        self,
        system_metrics: SystemMetrics,
        health_metrics: ApplicationHealthMetrics,
        business_metrics: BusinessLogicMetrics
    ):
        """Create alerts based on cross-system correlations."""
        
        # Example correlation: High CPU + Low CLI success rate
        if (system_metrics.cpu_percent > 80 and 
            business_metrics.cli_success_rate_overall < 85):
            
            await self.alerting_system.create_alert(
                level=AlertLevel.WARNING,
                title="System Performance Impacting CLI Reliability",
                message=f"High CPU usage ({system_metrics.cpu_percent:.1f}%) coinciding with low CLI success rate ({business_metrics.cli_success_rate_overall:.1f}%)",
                source="correlation",
                metric_name="cpu_cli_correlation",
                current_value={
                    "cpu_percent": system_metrics.cpu_percent,
                    "cli_success_rate": business_metrics.cli_success_rate_overall
                },
                threshold_value={"cpu_max": 80, "cli_success_min": 85},
                tags=["correlation", "performance", "reliability"]
            )
        
        # Example correlation: API errors + Agent failures
        if (health_metrics.api_error_rate > 10 and 
            health_metrics.agent_success_rate < 80):
            
            await self.alerting_system.create_alert(
                level=AlertLevel.CRITICAL,
                title="API Issues Causing Agent Orchestration Failures",
                message=f"API error rate ({health_metrics.api_error_rate:.1f}%) and agent success rate ({health_metrics.agent_success_rate:.1f}%) indicate systemic issues",
                source="correlation", 
                metric_name="api_agent_correlation",
                current_value={
                    "api_error_rate": health_metrics.api_error_rate,
                    "agent_success_rate": health_metrics.agent_success_rate
                },
                threshold_value={"api_error_max": 10, "agent_success_min": 80},
                tags=["correlation", "api", "orchestration"]
            )
    
    async def _auto_resolve_alerts(
        self,
        system_metrics: SystemMetrics,
        health_metrics: ApplicationHealthMetrics,
        business_metrics: BusinessLogicMetrics
    ):
        """Automatically resolve alerts when conditions improve."""
        
        active_alerts = self.alerting_system.get_active_alerts()
        
        for alert in active_alerts:
            should_resolve = False
            
            # Check if alert condition has been resolved
            if alert.source == "system":
                should_resolve = self._check_system_alert_resolution(alert, system_metrics)
            elif alert.source == "application":
                should_resolve = self._check_health_alert_resolution(alert, health_metrics)
            elif alert.source == "business":
                should_resolve = self._check_business_alert_resolution(alert, business_metrics)
            
            if should_resolve:
                await self.alerting_system.resolve_alert(alert.id)
                self.monitoring_stats["alerts_resolved"] += 1
                logger.info(f"Auto-resolved alert: {alert.id}")
    
    def _check_system_alert_resolution(self, alert: Alert, metrics: SystemMetrics) -> bool:
        """Check if system alert should be auto-resolved."""
        metric_name = alert.metric_name
        threshold = alert.threshold_value
        
        if metric_name == "cpu_percent":
            return metrics.cpu_percent < threshold * 0.9  # 10% buffer
        elif metric_name == "memory_percent":
            return metrics.memory_percent < threshold * 0.9
        elif metric_name.startswith("api_response_time"):
            endpoint = metric_name.replace("api_response_time_", "")
            current_time = metrics.api_response_times.get(endpoint, 0)
            return current_time > 0 and current_time < threshold * 0.9
        elif metric_name.startswith("api_availability"):
            endpoint = metric_name.replace("api_availability_", "")
            return metrics.api_response_times.get(endpoint, -1) > 0
        
        return False
    
    def _check_health_alert_resolution(self, alert: Alert, metrics: ApplicationHealthMetrics) -> bool:
        """Check if health alert should be auto-resolved."""
        metric_name = alert.metric_name
        
        if metric_name == "api_error_rate":
            return metrics.api_error_rate < alert.threshold_value * 0.8
        elif metric_name == "agent_success_rate":
            return metrics.agent_success_rate > alert.threshold_value * 1.1
        elif metric_name.endswith("_availability"):
            service_name = metric_name.replace("_availability", "")
            service_health = metrics.services.get(service_name)
            return service_health and service_health.status == "UP"
        
        return False
    
    def _check_business_alert_resolution(self, alert: Alert, metrics: BusinessLogicMetrics) -> bool:
        """Check if business alert should be auto-resolved."""
        metric_name = alert.metric_name
        
        if metric_name == "cli_success_rate":
            return metrics.cli_success_rate_overall > alert.threshold_value * 1.1
        elif metric_name == "cli_response_time":
            return metrics.cli_avg_response_time_ms < alert.threshold_value * 0.9
        elif metric_name == "user_satisfaction":
            return metrics.overall_user_satisfaction > alert.threshold_value * 1.1
        
        return False
    
    async def _update_baselines(self):
        """Update performance baselines based on historical data."""
        if not self._last_baseline_calculation:
            self._last_baseline_calculation = datetime.now()
            return
        
        # Update baselines every hour
        time_since_update = datetime.now() - self._last_baseline_calculation
        if time_since_update < timedelta(hours=1):
            return
        
        # Calculate baselines from recent history
        recent_metrics = [
            m for m in self.consolidated_metrics
            if datetime.fromisoformat(m["timestamp"]) >= datetime.now() - timedelta(hours=24)
        ]
        
        if len(recent_metrics) < 10:  # Need sufficient data
            return
        
        # System baselines
        cpu_values = [m["system"]["cpu_percent"] for m in recent_metrics]
        memory_values = [m["system"]["memory_percent"] for m in recent_metrics]
        
        self.performance_baselines.update({
            "cpu_percent_baseline": sum(cpu_values) / len(cpu_values),
            "memory_percent_baseline": sum(memory_values) / len(memory_values),
        })
        
        # Business baselines
        cli_response_times = [m["business"]["cli_response_time_avg"] for m in recent_metrics]
        cli_success_rates = [m["business"]["cli_success_rate"] for m in recent_metrics]
        
        self.performance_baselines.update({
            "cli_response_time_baseline": sum(cli_response_times) / len(cli_response_times),
            "cli_success_rate_baseline": sum(cli_success_rates) / len(cli_success_rates),
        })
        
        self._last_baseline_calculation = datetime.now()
        logger.debug("Performance baselines updated")
    
    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring system summary."""
        
        # Get latest metrics if available
        latest_consolidated = self.consolidated_metrics[-1] if self.consolidated_metrics else None
        
        # Get system summaries
        system_summary = self.system_monitor.get_performance_summary()
        health_summary = self.health_monitor.get_health_summary()
        business_summary = self.business_monitor.get_business_summary()
        alert_stats = self.alerting_system.get_alert_statistics()
        
        # Overall system status
        overall_status = "HEALTHY"
        if (system_summary.get("status") == "CRITICAL" or 
            health_summary.get("overall_status") == "CRITICAL" or
            business_summary.get("business_health") == "CRITICAL"):
            overall_status = "CRITICAL"
        elif (system_summary.get("status") == "WARNING" or
              health_summary.get("overall_status") == "DEGRADED" or
              business_summary.get("business_health") == "WARNING"):
            overall_status = "WARNING"
        
        return {
            "overall_status": overall_status,
            "monitoring_active": self.is_monitoring,
            "last_monitoring_run": self.last_monitoring_run.isoformat() if self.last_monitoring_run else None,
            "monitoring_interval_seconds": self.monitoring_interval,
            "monitoring_stats": self.monitoring_stats,
            "latest_metrics": latest_consolidated,
            "system_monitoring": system_summary,
            "health_monitoring": health_summary,
            "business_monitoring": business_summary,
            "alerting": alert_stats,
            "performance_baselines": self.performance_baselines,
            "consolidated_metrics_history": len(self.consolidated_metrics)
        }
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data optimized for monitoring dashboard display."""
        
        # Recent metrics for charts (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_metrics = [
            m for m in self.consolidated_metrics
            if datetime.fromisoformat(m["timestamp"]) >= recent_cutoff
        ]
        
        # Active alerts
        active_alerts = self.alerting_system.get_active_alerts()
        
        # Top violations
        recent_violations = []
        for alert in active_alerts:
            recent_violations.append({
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "metric": alert.metric_name,
                "current": alert.current_value,
                "threshold": alert.threshold_value,
                "timestamp": alert.timestamp.isoformat()
            })
        
        # Performance trends (simple calculation)
        trends = {}
        if len(recent_metrics) >= 2:
            latest = recent_metrics[-1]
            previous = recent_metrics[-2]
            
            trends["cpu_trend"] = "up" if latest["system"]["cpu_percent"] > previous["system"]["cpu_percent"] else "down"
            trends["memory_trend"] = "up" if latest["system"]["memory_percent"] > previous["system"]["memory_percent"] else "down"
            trends["cli_performance_trend"] = "up" if latest["business"]["cli_success_rate"] > previous["business"]["cli_success_rate"] else "down"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "recent_metrics": recent_metrics[-100:],  # Last 100 data points
            "active_alerts": len(active_alerts),
            "alert_breakdown": {
                level.value: sum(1 for a in active_alerts if a.level == level)
                for level in AlertLevel
            },
            "top_violations": recent_violations[:10],
            "performance_trends": trends,
            "system_health": {
                "apis_up": self.consolidated_metrics[-1]["health"]["api_endpoints_up"] if self.consolidated_metrics else 0,
                "apis_total": self.consolidated_metrics[-1]["health"]["api_endpoints_total"] if self.consolidated_metrics else 0,
                "agents_active": self.consolidated_metrics[-1]["health"]["active_agents"] if self.consolidated_metrics else 0,
                "coordination_health": self.consolidated_metrics[-1]["health"]["coordination_health"] if self.consolidated_metrics else "UNKNOWN"
            },
            "ocean_targets": {
                "cli_response_time_target_ms": 100.0,
                "cli_response_time_current_ms": self.consolidated_metrics[-1]["business"]["cli_response_time_avg"] if self.consolidated_metrics else 0,
                "cli_success_rate_current": self.consolidated_metrics[-1]["business"]["cli_success_rate"] if self.consolidated_metrics else 100
            }
        }
    
    async def configure_alerting(self, config: Dict[str, Any]):
        """Configure alerting system."""
        
        # Configure notification channels
        if "notification_channels" in config:
            for channel_name, channel_config in config["notification_channels"].items():
                self.alerting_system.configure_notification_channel(
                    channel_name, 
                    channel_config.get("config", {}),
                    channel_config.get("enabled", True)
                )
        
        # Configure suppression rules
        if "suppression_rules" in config:
            for rule in config["suppression_rules"]:
                self.alerting_system.add_suppression_rule(rule)
        
        # Update alerting settings
        if "alerting_enabled" in config:
            self.alerting_enabled = config["alerting_enabled"]
        
        if "auto_resolve_alerts" in config:
            self.auto_resolve_alerts = config["auto_resolve_alerts"]
        
        logger.info("Alerting configuration updated")
    
    async def close(self):
        """Close all monitoring resources."""
        await self.stop_monitoring()
        
        await self.system_monitor.close()
        await self.health_monitor.close()
        await self.alerting_system.close()
        
        logger.info("Monitoring coordinator closed")