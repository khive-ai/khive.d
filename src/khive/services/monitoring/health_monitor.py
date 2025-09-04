"""
Application health monitoring for comprehensive service availability tracking.

Monitors service availability, error rates, session lifecycle, and agent 
coordination system health with deep integration into existing infrastructure.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import aiohttp

from khive.daemon.client import get_daemon_client
from khive.services.claude.hooks.coordination_metrics import get_metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    """Health status for a specific service."""
    name: str
    status: str  # "UP", "DOWN", "DEGRADED"
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    uptime_percentage: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationHealthMetrics:
    """Comprehensive application health metrics."""
    timestamp: datetime
    overall_status: str  # "HEALTHY", "DEGRADED", "CRITICAL"
    
    # Service Health
    services: Dict[str, ServiceHealth] = field(default_factory=dict)
    
    # API Health
    api_endpoints_up: int = 0
    api_endpoints_total: int = 0
    api_response_time_avg: float = 0.0
    api_error_rate: float = 0.0
    
    # Session Lifecycle
    active_sessions: int = 0
    session_success_rate: float = 100.0
    avg_session_duration: float = 0.0
    
    # Agent Coordination Health
    coordination_health: str = "UNKNOWN"
    active_agents: int = 0
    agent_success_rate: float = 100.0
    coordination_conflicts: int = 0
    
    # Database Health
    database_status: str = "UNKNOWN"
    database_response_time_ms: Optional[float] = None
    
    # WebSocket Health  
    websocket_status: str = "UNKNOWN"
    websocket_connections: int = 0


class ApplicationHealthMonitor:
    """
    Comprehensive application health monitoring system.
    
    Provides deep health monitoring for all application components including
    APIs, databases, coordination systems, and business logic.
    """
    
    def __init__(self):
        self.daemon_client = get_daemon_client()
        self.metrics_collector = get_metrics_collector()
        
        # Service definitions to monitor
        self.services = {
            "daemon": {
                "check_method": self._check_daemon_health,
                "critical": True
            },
            "coordination": {
                "check_method": self._check_coordination_health,
                "critical": True
            },
            "api": {
                "check_method": self._check_api_health,
                "critical": True
            },
            "database": {
                "check_method": self._check_database_health,
                "critical": False
            },
            "websocket": {
                "check_method": self._check_websocket_health,
                "critical": False
            },
        }
        
        # Health history for trend analysis
        self.health_history: List[ApplicationHealthMetrics] = []
        self.max_history_size = 500  # Keep last 500 health checks
        
        # Health thresholds
        self.thresholds = {
            "api_response_time_ms": 500.0,
            "api_error_rate_percent": 5.0,
            "session_success_rate_percent": 95.0,
            "agent_success_rate_percent": 90.0,
            "database_response_time_ms": 1000.0,
            "coordination_conflict_rate": 10.0,  # conflicts per hour
        }
        
        # Session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10.0)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _check_daemon_health(self) -> ServiceHealth:
        """Check Khive daemon health."""
        try:
            start_time = time.time()
            
            if self.daemon_client.is_running():
                health_data = self.daemon_client.health()
                response_time = (time.time() - start_time) * 1000
                
                # Check daemon stats
                stats_data = self.daemon_client.get_stats() if hasattr(self.daemon_client, 'get_stats') else {}
                
                return ServiceHealth(
                    name="daemon",
                    status="UP",
                    response_time_ms=response_time,
                    last_check=datetime.now(),
                    metadata={
                        "health_data": health_data,
                        "stats": stats_data,
                        "uptime_seconds": health_data.get("uptime_seconds", 0)
                    }
                )
            else:
                return ServiceHealth(
                    name="daemon",
                    status="DOWN",
                    last_check=datetime.now(),
                    error_message="Daemon is not running",
                    consecutive_failures=1
                )
                
        except Exception as e:
            return ServiceHealth(
                name="daemon",
                status="DOWN", 
                last_check=datetime.now(),
                error_message=str(e),
                consecutive_failures=1
            )
    
    async def _check_coordination_health(self) -> ServiceHealth:
        """Check coordination system health."""
        try:
            start_time = time.time()
            
            # Get coordination status from daemon
            session = await self._get_session()
            async with session.get("http://127.0.0.1:11634/api/coordinate/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    response_time = (time.time() - start_time) * 1000
                    
                    # Get coordination metrics
                    metrics_report = self.metrics_collector.generate_report()
                    effectiveness_score = metrics_report["summary"]["overall_effectiveness"]
                    
                    # Determine coordination health based on effectiveness
                    if effectiveness_score >= 80:
                        coord_status = "UP"
                    elif effectiveness_score >= 60:
                        coord_status = "DEGRADED"
                    else:
                        coord_status = "DOWN"
                    
                    return ServiceHealth(
                        name="coordination",
                        status=coord_status,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        metadata={
                            "status_data": status_data,
                            "effectiveness_score": effectiveness_score,
                            "metrics_report": metrics_report
                        }
                    )
                else:
                    return ServiceHealth(
                        name="coordination",
                        status="DOWN",
                        last_check=datetime.now(),
                        error_message=f"HTTP {response.status}",
                        consecutive_failures=1
                    )
                    
        except Exception as e:
            return ServiceHealth(
                name="coordination",
                status="DOWN",
                last_check=datetime.now(), 
                error_message=str(e),
                consecutive_failures=1
            )
    
    async def _check_api_health(self) -> ServiceHealth:
        """Check API endpoints health."""
        try:
            endpoints = [
                "http://127.0.0.1:11634/health",
                "http://127.0.0.1:11634/api/stats",
                "http://127.0.0.1:11634/api/coordination/metrics"
            ]
            
            session = await self._get_session()
            total_response_time = 0
            successful_checks = 0
            failed_checks = 0
            
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    async with session.get(endpoint) as response:
                        response_time = (time.time() - start_time) * 1000
                        total_response_time += response_time
                        
                        if response.status == 200:
                            successful_checks += 1
                        else:
                            failed_checks += 1
                            
                except Exception:
                    failed_checks += 1
            
            total_checks = successful_checks + failed_checks
            success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
            avg_response_time = total_response_time / successful_checks if successful_checks > 0 else 0
            
            # Determine API health status
            if success_rate >= 95 and avg_response_time < self.thresholds["api_response_time_ms"]:
                api_status = "UP"
            elif success_rate >= 80:
                api_status = "DEGRADED"
            else:
                api_status = "DOWN"
            
            return ServiceHealth(
                name="api",
                status=api_status,
                response_time_ms=avg_response_time,
                last_check=datetime.now(),
                metadata={
                    "endpoints_checked": total_checks,
                    "successful_checks": successful_checks,
                    "failed_checks": failed_checks,
                    "success_rate_percent": success_rate
                }
            )
            
        except Exception as e:
            return ServiceHealth(
                name="api",
                status="DOWN",
                last_check=datetime.now(),
                error_message=str(e),
                consecutive_failures=1
            )
    
    async def _check_database_health(self) -> ServiceHealth:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            
            # Import here to avoid circular imports
            from khive.services.claude.hooks.hook_event import HookEvent
            
            # Try to query recent events as a health check
            recent_events = await HookEvent.get_recent(limit=1)
            response_time = (time.time() - start_time) * 1000
            
            return ServiceHealth(
                name="database",
                status="UP",
                response_time_ms=response_time,
                last_check=datetime.now(),
                metadata={
                    "events_checked": len(recent_events),
                    "query_type": "recent_events"
                }
            )
            
        except Exception as e:
            return ServiceHealth(
                name="database",
                status="DOWN",
                last_check=datetime.now(),
                error_message=str(e),
                consecutive_failures=1
            )
    
    async def _check_websocket_health(self) -> ServiceHealth:
        """Check WebSocket server health."""
        try:
            import socket
            
            # Check if WebSocket port is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", 8767))
            sock.close()
            
            if result == 0:
                return ServiceHealth(
                    name="websocket",
                    status="UP",
                    last_check=datetime.now(),
                    metadata={"port": 8767}
                )
            else:
                return ServiceHealth(
                    name="websocket",
                    status="DOWN",
                    last_check=datetime.now(),
                    error_message="WebSocket port not accessible",
                    consecutive_failures=1
                )
                
        except Exception as e:
            return ServiceHealth(
                name="websocket",
                status="DOWN",
                last_check=datetime.now(),
                error_message=str(e),
                consecutive_failures=1
            )
    
    async def collect_health_metrics(self) -> ApplicationHealthMetrics:
        """Collect comprehensive application health metrics."""
        timestamp = datetime.now()
        
        # Check all services
        services_health = {}
        for service_name, service_config in self.services.items():
            health = await service_config["check_method"]()
            services_health[service_name] = health
        
        # Calculate overall status
        critical_services_down = any(
            health.status == "DOWN" and self.services[name]["critical"]
            for name, health in services_health.items()
        )
        any_service_degraded = any(
            health.status == "DEGRADED" 
            for health in services_health.values()
        )
        
        if critical_services_down:
            overall_status = "CRITICAL"
        elif any_service_degraded:
            overall_status = "DEGRADED"  
        else:
            overall_status = "HEALTHY"
        
        # Calculate API metrics
        api_health = services_health.get("api")
        if api_health and api_health.metadata:
            api_metadata = api_health.metadata
            api_endpoints_up = api_metadata.get("successful_checks", 0)
            api_endpoints_total = api_metadata.get("endpoints_checked", 0)
            api_response_time_avg = api_health.response_time_ms or 0.0
            api_error_rate = 100 - api_metadata.get("success_rate_percent", 100)
        else:
            api_endpoints_up = 0
            api_endpoints_total = 0
            api_response_time_avg = 0.0
            api_error_rate = 100.0
        
        # Get coordination metrics for agent health
        coordination_health = services_health.get("coordination")
        if coordination_health and coordination_health.metadata:
            coord_metadata = coordination_health.metadata
            metrics_report = coord_metadata.get("metrics_report", {})
            summary = metrics_report.get("summary", {})
            
            active_agents = summary.get("agents_coordinated", 0)
            agent_success_rate = coord_metadata.get("effectiveness_score", 100.0)
            coordination_conflicts = 0  # TODO: Extract from coordination metrics
            coord_status = coordination_health.status
        else:
            active_agents = 0
            agent_success_rate = 0.0
            coordination_conflicts = 0
            coord_status = "UNKNOWN"
        
        # Database health
        db_health = services_health.get("database")
        database_status = db_health.status if db_health else "UNKNOWN"
        database_response_time_ms = db_health.response_time_ms if db_health else None
        
        # WebSocket health
        ws_health = services_health.get("websocket")
        websocket_status = ws_health.status if ws_health else "UNKNOWN"
        websocket_connections = 0  # TODO: Get actual connection count
        
        # Session metrics (placeholder - would need session tracking)
        active_sessions = 0
        session_success_rate = 100.0
        avg_session_duration = 0.0
        
        metrics = ApplicationHealthMetrics(
            timestamp=timestamp,
            overall_status=overall_status,
            services=services_health,
            api_endpoints_up=api_endpoints_up,
            api_endpoints_total=api_endpoints_total,
            api_response_time_avg=api_response_time_avg,
            api_error_rate=api_error_rate,
            active_sessions=active_sessions,
            session_success_rate=session_success_rate,
            avg_session_duration=avg_session_duration,
            coordination_health=coord_status,
            active_agents=active_agents,
            agent_success_rate=agent_success_rate,
            coordination_conflicts=coordination_conflicts,
            database_status=database_status,
            database_response_time_ms=database_response_time_ms,
            websocket_status=websocket_status,
            websocket_connections=websocket_connections
        )
        
        # Add to history
        self.health_history.append(metrics)
        if len(self.health_history) > self.max_history_size:
            self.health_history.pop(0)
        
        return metrics
    
    def check_health_violations(self, metrics: ApplicationHealthMetrics) -> List[Dict[str, Any]]:
        """Check for health threshold violations."""
        violations = []
        
        # API response time threshold
        if metrics.api_response_time_avg > self.thresholds["api_response_time_ms"]:
            violations.append({
                "metric": "api_response_time",
                "current": metrics.api_response_time_avg,
                "threshold": self.thresholds["api_response_time_ms"],
                "severity": "WARNING"
            })
        
        # API error rate threshold
        if metrics.api_error_rate > self.thresholds["api_error_rate_percent"]:
            violations.append({
                "metric": "api_error_rate",
                "current": metrics.api_error_rate,
                "threshold": self.thresholds["api_error_rate_percent"],
                "severity": "CRITICAL" if metrics.api_error_rate > 20 else "WARNING"
            })
        
        # Agent success rate threshold
        if metrics.agent_success_rate < self.thresholds["agent_success_rate_percent"]:
            violations.append({
                "metric": "agent_success_rate",
                "current": metrics.agent_success_rate,
                "threshold": self.thresholds["agent_success_rate_percent"],
                "severity": "WARNING"
            })
        
        # Database response time threshold
        if (metrics.database_response_time_ms and 
            metrics.database_response_time_ms > self.thresholds["database_response_time_ms"]):
            violations.append({
                "metric": "database_response_time",
                "current": metrics.database_response_time_ms,
                "threshold": self.thresholds["database_response_time_ms"],
                "severity": "WARNING"
            })
        
        # Service availability violations
        for service_name, service_health in metrics.services.items():
            if service_health.status == "DOWN":
                severity = "CRITICAL" if self.services[service_name]["critical"] else "WARNING"
                violations.append({
                    "metric": f"{service_name}_availability",
                    "current": "DOWN",
                    "threshold": "UP",
                    "severity": severity,
                    "error_message": service_health.error_message
                })
            elif service_health.status == "DEGRADED":
                violations.append({
                    "metric": f"{service_name}_performance",
                    "current": "DEGRADED",
                    "threshold": "UP",
                    "severity": "WARNING"
                })
        
        return violations
    
    def get_uptime_statistics(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """Calculate uptime statistics for services."""
        if not self.health_history:
            return {}
        
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        recent_metrics = [
            m for m in self.health_history
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        uptime_stats = {}
        
        # Calculate uptime for each service
        for service_name in self.services.keys():
            uptime_checks = 0
            total_checks = 0
            
            for metrics in recent_metrics:
                if service_name in metrics.services:
                    total_checks += 1
                    if metrics.services[service_name].status == "UP":
                        uptime_checks += 1
            
            uptime_percentage = (uptime_checks / total_checks * 100) if total_checks > 0 else 0
            uptime_stats[service_name] = {
                "uptime_percentage": uptime_percentage,
                "total_checks": total_checks,
                "up_checks": uptime_checks
            }
        
        # Overall system uptime (based on critical services)
        critical_uptime_checks = 0
        total_uptime_checks = 0
        
        for metrics in recent_metrics:
            total_uptime_checks += 1
            critical_down = any(
                metrics.services.get(name, ServiceHealth("", "DOWN")).status == "DOWN"
                and self.services[name]["critical"]
                for name in self.services.keys()
            )
            if not critical_down:
                critical_uptime_checks += 1
        
        overall_uptime = (critical_uptime_checks / total_uptime_checks * 100) if total_uptime_checks > 0 else 0
        uptime_stats["overall"] = {
            "uptime_percentage": overall_uptime,
            "total_checks": total_uptime_checks,
            "up_checks": critical_uptime_checks
        }
        
        return uptime_stats
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        if not self.health_history:
            return {"status": "no_data", "checks_performed": 0}
        
        latest = self.health_history[-1]
        violations = self.check_health_violations(latest)
        uptime_stats = self.get_uptime_statistics()
        
        return {
            "overall_status": latest.overall_status,
            "timestamp": latest.timestamp.isoformat(),
            "checks_performed": len(self.health_history),
            "violations": violations,
            "services": {
                name: {
                    "status": health.status,
                    "response_time_ms": health.response_time_ms,
                    "last_check": health.last_check.isoformat() if health.last_check else None,
                    "error_message": health.error_message
                }
                for name, health in latest.services.items()
            },
            "api_health": {
                "endpoints_up": latest.api_endpoints_up,
                "endpoints_total": latest.api_endpoints_total,
                "response_time_avg": latest.api_response_time_avg,
                "error_rate_percent": latest.api_error_rate
            },
            "coordination_health": {
                "status": latest.coordination_health,
                "active_agents": latest.active_agents,
                "success_rate_percent": latest.agent_success_rate,
                "conflicts": latest.coordination_conflicts
            },
            "uptime_statistics": uptime_stats,
            "thresholds": self.thresholds
        }
    
    async def close(self):
        """Close monitoring resources."""
        if self._session and not self._session.closed:
            await self._session.close()