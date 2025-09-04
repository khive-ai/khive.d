"""
Enhanced Khive daemon server with comprehensive monitoring integration.

Extends the existing daemon server with production-grade monitoring endpoints
for system performance, application health, business logic, and alerting.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from khive.daemon.server import KhiveDaemonServer
from khive.services.monitoring import (
    MonitoringCoordinator,
    SystemPerformanceMonitor,
    ApplicationHealthMonitor, 
    BusinessLogicMonitor,
    MultiTierAlertingSystem,
    AlertLevel,
    Alert
)

logger = logging.getLogger(__name__)


# Enhanced response models
class MonitoringSummaryResponse(BaseModel):
    overall_status: str
    monitoring_active: bool
    last_monitoring_run: Optional[str]
    system_health: str
    application_health: str
    business_health: str
    active_alerts: int
    monitoring_stats: Dict[str, Any]


class DashboardDataResponse(BaseModel):
    timestamp: str
    recent_metrics: List[Dict[str, Any]]
    active_alerts: int
    alert_breakdown: Dict[str, int]
    top_violations: List[Dict[str, Any]]
    performance_trends: Dict[str, str]
    system_health: Dict[str, Any]
    ocean_targets: Dict[str, Any]


class AlertResponse(BaseModel):
    id: str
    level: str
    title: str
    message: str
    source: str
    metric_name: str
    current_value: Any
    threshold_value: Any
    timestamp: str
    status: str


class AlertingConfigRequest(BaseModel):
    alerting_enabled: Optional[bool] = None
    auto_resolve_alerts: Optional[bool] = None
    notification_channels: Optional[Dict[str, Any]] = None
    suppression_rules: Optional[List[Dict[str, Any]]] = None


class MonitoringEnhancedDaemonServer(KhiveDaemonServer):
    """
    Enhanced daemon server with comprehensive monitoring capabilities.
    
    Extends the base daemon server with production-grade monitoring endpoints
    for system performance, application health, business logic, and alerting.
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize comprehensive monitoring system
        self.monitoring_coordinator = MonitoringCoordinator(
            monitoring_interval_seconds=30,  # 30-second monitoring for production
            alerting_enabled=True,
            auto_resolve_alerts=True
        )
        
        # Monitoring state
        self.monitoring_initialized = False
        
        # Setup enhanced routes
        self._setup_monitoring_routes()
    
    async def startup(self):
        """Initialize enhanced daemon services."""
        # Initialize base services
        await super().startup()
        
        # Initialize monitoring system
        try:
            # Configure alerting with reasonable defaults
            await self.monitoring_coordinator.configure_alerting({
                "notification_channels": {
                    "console": {
                        "config": {},
                        "enabled": True
                    },
                    "system": {
                        "config": {},
                        "enabled": True
                    }
                },
                "alerting_enabled": True,
                "auto_resolve_alerts": True
            })
            
            # Start continuous monitoring
            await self.monitoring_coordinator.start_monitoring()
            self.monitoring_initialized = True
            
            logger.info("Comprehensive monitoring system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring system: {e}")
            self.monitoring_initialized = False
    
    def _setup_monitoring_routes(self):
        """Setup comprehensive monitoring API routes."""
        
        @self.app.get("/api/monitoring/summary", response_model=MonitoringSummaryResponse)
        async def get_monitoring_summary():
            """Get comprehensive monitoring system summary."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503, 
                        detail="Monitoring system not initialized"
                    )
                
                summary = await self.monitoring_coordinator.get_monitoring_summary()
                
                return MonitoringSummaryResponse(
                    overall_status=summary["overall_status"],
                    monitoring_active=summary["monitoring_active"],
                    last_monitoring_run=summary["last_monitoring_run"],
                    system_health=summary["system_monitoring"]["status"],
                    application_health=summary["health_monitoring"]["overall_status"],
                    business_health=summary["business_monitoring"]["business_health"],
                    active_alerts=summary["alerting"]["active_alerts"],
                    monitoring_stats=summary["monitoring_stats"]
                )
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Monitoring summary failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/monitoring/dashboard", response_model=DashboardDataResponse)
        async def get_dashboard_data():
            """Get optimized data for monitoring dashboard."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                dashboard_data = await self.monitoring_coordinator.get_dashboard_data()
                
                return DashboardDataResponse(**dashboard_data)
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Dashboard data retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/monitoring/system")
        async def get_system_metrics():
            """Get detailed system performance metrics."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                system_summary = self.monitoring_coordinator.system_monitor.get_performance_summary()
                return system_summary
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"System metrics retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/monitoring/health")
        async def get_health_metrics():
            """Get detailed application health metrics."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                health_summary = self.monitoring_coordinator.health_monitor.get_health_summary()
                return health_summary
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Health metrics retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/monitoring/business")
        async def get_business_metrics():
            """Get detailed business logic metrics."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                business_summary = self.monitoring_coordinator.business_monitor.get_business_summary()
                return business_summary
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Business metrics retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/monitoring/alerts", response_model=List[AlertResponse])
        async def get_active_alerts():
            """Get all active alerts."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                active_alerts = self.monitoring_coordinator.alerting_system.get_active_alerts()
                
                return [
                    AlertResponse(
                        id=alert.id,
                        level=alert.level.value,
                        title=alert.title,
                        message=alert.message,
                        source=alert.source,
                        metric_name=alert.metric_name,
                        current_value=alert.current_value,
                        threshold_value=alert.threshold_value,
                        timestamp=alert.timestamp.isoformat(),
                        status=alert.status.value
                    )
                    for alert in active_alerts
                ]
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Alert retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/monitoring/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(alert_id: str, acknowledged_by: str = "system"):
            """Acknowledge an active alert."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                success = await self.monitoring_coordinator.alerting_system.acknowledge_alert(
                    alert_id, acknowledged_by
                )
                
                if not success:
                    raise HTTPException(status_code=404, detail="Alert not found")
                
                return {"status": "acknowledged", "alert_id": alert_id}
            except HTTPException:
                raise
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Alert acknowledgment failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/monitoring/alerts/{alert_id}/resolve")
        async def resolve_alert(alert_id: str):
            """Manually resolve an alert."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                success = await self.monitoring_coordinator.alerting_system.resolve_alert(alert_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Alert not found")
                
                return {"status": "resolved", "alert_id": alert_id}
            except HTTPException:
                raise
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Alert resolution failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/monitoring/alerts/statistics")
        async def get_alert_statistics():
            """Get alert system statistics."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                stats = self.monitoring_coordinator.alerting_system.get_alert_statistics()
                return stats
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Alert statistics retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/monitoring/configure")
        async def configure_monitoring(config: AlertingConfigRequest):
            """Configure monitoring and alerting system."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                # Convert Pydantic model to dict
                config_dict = config.dict(exclude_none=True)
                
                await self.monitoring_coordinator.configure_alerting(config_dict)
                
                return {"status": "configured", "applied_settings": config_dict}
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Monitoring configuration failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/monitoring/test-alert")
        async def create_test_alert():
            """Create a test alert for system verification."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                test_alert = await self.monitoring_coordinator.alerting_system.create_alert(
                    level=AlertLevel.INFO,
                    title="Test Alert",
                    message="This is a test alert to verify the monitoring system is working correctly",
                    source="system_test",
                    metric_name="test_metric",
                    current_value="test",
                    threshold_value="test",
                    tags=["test", "system_verification"]
                )
                
                return {
                    "status": "test_alert_created",
                    "alert_id": test_alert.id,
                    "message": "Test alert created successfully"
                }
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Test alert creation failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/monitoring/insights")
        async def get_performance_insights():
            """Get actionable performance insights."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    raise HTTPException(
                        status_code=503,
                        detail="Monitoring system not initialized"
                    )
                
                insights = self.monitoring_coordinator.business_monitor.get_performance_insights()
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "insights": insights,
                    "insight_count": len(insights)
                }
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Performance insights retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/monitoring/track/cli-command")
        async def track_cli_command(
            command: str,
            execution_time_ms: float,
            success: bool,
            error_message: Optional[str] = None,
            session_id: Optional[str] = None
        ):
            """Track CLI command execution for business monitoring."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    return {"status": "monitoring_not_initialized"}
                
                await self.monitoring_coordinator.business_monitor.track_cli_command(
                    command=command,
                    execution_time_ms=execution_time_ms,
                    success=success,
                    error_message=error_message,
                    session_id=session_id
                )
                
                return {"status": "tracked", "command": command}
            except Exception as e:
                logger.error(f"CLI command tracking failed: {e}")
                return {"status": "failed", "error": str(e)}
        
        @self.app.post("/api/monitoring/track/agent-activity")
        async def track_agent_activity(
            agent_id: str,
            role: str,
            domain: Optional[str],
            task_description: str,
            duration_ms: float,
            success: bool,
            coordination_overhead_ms: float = 0.0,
            error_message: Optional[str] = None
        ):
            """Track agent activity for orchestration monitoring."""
            self.stats["requests"] += 1
            try:
                if not self.monitoring_initialized:
                    return {"status": "monitoring_not_initialized"}
                
                await self.monitoring_coordinator.business_monitor.track_agent_activity(
                    agent_id=agent_id,
                    role=role,
                    domain=domain,
                    task_description=task_description,
                    duration_ms=duration_ms,
                    success=success,
                    coordination_overhead_ms=coordination_overhead_ms,
                    error_message=error_message
                )
                
                return {"status": "tracked", "agent_id": agent_id}
            except Exception as e:
                logger.error(f"Agent activity tracking failed: {e}")
                return {"status": "failed", "error": str(e)}
        
        # Override health check to include monitoring status
        @self.app.get("/health")
        async def enhanced_health_check():
            """Enhanced health check including monitoring system status."""
            base_health = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
                "stats": self.stats,
            }
            
            # Add monitoring system health
            if self.monitoring_initialized:
                try:
                    monitoring_summary = await self.monitoring_coordinator.get_monitoring_summary()
                    base_health["monitoring"] = {
                        "status": monitoring_summary["overall_status"],
                        "active": monitoring_summary["monitoring_active"],
                        "last_run": monitoring_summary["last_monitoring_run"],
                        "active_alerts": monitoring_summary["alerting"]["active_alerts"]
                    }
                except Exception as e:
                    base_health["monitoring"] = {
                        "status": "ERROR",
                        "error": str(e)
                    }
            else:
                base_health["monitoring"] = {
                    "status": "NOT_INITIALIZED"
                }
            
            return base_health
    
    async def shutdown(self):
        """Shutdown enhanced daemon services."""
        # Stop monitoring system
        if self.monitoring_initialized:
            try:
                await self.monitoring_coordinator.close()
                logger.info("Monitoring system shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down monitoring system: {e}")


def create_monitoring_enhanced_daemon_server() -> MonitoringEnhancedDaemonServer:
    """Create enhanced daemon server instance with monitoring."""
    return MonitoringEnhancedDaemonServer()


async def run_monitoring_enhanced_daemon_server(host: str = "localhost", port: int = 11634):
    """Run enhanced daemon server with monitoring."""
    import uvicorn
    
    server = create_monitoring_enhanced_daemon_server()
    config = uvicorn.Config(server.app, host=host, port=port, log_level="info")
    
    uvicorn_server = uvicorn.Server(config)
    
    try:
        await uvicorn_server.serve()
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(run_monitoring_enhanced_daemon_server())