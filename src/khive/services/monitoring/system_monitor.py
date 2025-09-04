"""
Enhanced system performance monitoring for production deployment.

Extends the existing monitoring infrastructure with comprehensive system metrics
including CPU, memory, disk, network, and API response time monitoring.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import aiohttp
import psutil
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Comprehensive system performance metrics."""
    timestamp: datetime
    
    # CPU Metrics
    cpu_percent: float
    cpu_count: int
    cpu_freq: Optional[Dict[str, float]] = None
    load_average: Optional[List[float]] = None
    
    # Memory Metrics
    memory_total: int
    memory_available: int
    memory_percent: float
    memory_used: int
    memory_free: int
    swap_total: int
    swap_used: int
    swap_percent: float
    
    # Disk Metrics
    disk_usage: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    disk_io: Optional[Dict[str, Any]] = None
    
    # Network Metrics
    network_io: Optional[Dict[str, Any]] = None
    network_connections: int = 0
    
    # API Response Time Metrics
    api_response_times: Dict[str, float] = field(default_factory=dict)
    
    # WebSocket Health
    websocket_connections: int = 0
    websocket_errors: int = 0


class SystemPerformanceMonitor:
    """
    Production-grade system performance monitoring.
    
    Provides comprehensive monitoring of system resources and API performance
    with thresholds and alerting capabilities.
    """
    
    def __init__(
        self, 
        api_endpoints: Optional[List[str]] = None,
        websocket_ports: Optional[List[int]] = None,
        disk_paths: Optional[List[str]] = None
    ):
        self.api_endpoints = api_endpoints or [
            "http://127.0.0.1:11634/health",
            "http://127.0.0.1:11634/api/stats"
        ]
        self.websocket_ports = websocket_ports or [8767]
        self.disk_paths = disk_paths or ["/", "/tmp"]
        
        # Performance thresholds
        self.thresholds = {
            "cpu_percent": 85.0,
            "memory_percent": 90.0,
            "disk_usage_percent": 90.0,
            "api_response_time_ms": 1000.0,  # 1 second
            "swap_percent": 50.0,
            "load_average_1m": psutil.cpu_count() * 2.0,  # 2x CPU cores
        }
        
        # Metrics history for trend analysis
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1000  # Keep last 1000 measurements
        
        # Performance baselines (calculated from history)
        self.baselines: Dict[str, float] = {}
        
        # Session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for API monitoring."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=5.0)  # 5 second timeout
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _monitor_api_endpoints(self) -> Dict[str, float]:
        """Monitor API endpoint response times."""
        response_times = {}
        session = await self._get_session()
        
        for endpoint in self.api_endpoints:
            try:
                start_time = time.time()
                async with session.get(endpoint) as response:
                    await response.read()  # Ensure full response is received
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    response_times[endpoint] = response_time
            except Exception as e:
                logger.warning(f"Failed to monitor API endpoint {endpoint}: {e}")
                response_times[endpoint] = -1.0  # Indicate failure
        
        return response_times
    
    def _monitor_websocket_health(self) -> Dict[str, int]:
        """Monitor WebSocket connection health."""
        websocket_stats = {"connections": 0, "errors": 0}
        
        for port in self.websocket_ports:
            try:
                # Count connections on WebSocket ports
                connections = [
                    conn for conn in psutil.net_connections() 
                    if conn.laddr.port == port and conn.status == psutil.CONN_ESTABLISHED
                ]
                websocket_stats["connections"] += len(connections)
            except (psutil.AccessDenied, Exception) as e:
                logger.debug(f"Could not check WebSocket port {port}: {e}")
                websocket_stats["errors"] += 1
        
        return websocket_stats
    
    def _get_disk_usage(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive disk usage statistics."""
        disk_stats = {}
        
        for path in self.disk_paths:
            if Path(path).exists():
                try:
                    usage = psutil.disk_usage(path)
                    disk_stats[path] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    }
                except Exception as e:
                    logger.warning(f"Failed to get disk usage for {path}: {e}")
        
        return disk_stats
    
    def _get_network_stats(self) -> Optional[Dict[str, Any]]:
        """Get network I/O statistics."""
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                return {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errors_in": net_io.errin,
                    "errors_out": net_io.errout,
                    "dropped_in": net_io.dropin,
                    "dropped_out": net_io.dropout
                }
        except Exception as e:
            logger.warning(f"Failed to get network statistics: {e}")
        
        return None
    
    def _get_disk_io_stats(self) -> Optional[Dict[str, Any]]:
        """Get disk I/O statistics."""
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                return {
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_time": disk_io.read_time,
                    "write_time": disk_io.write_time
                }
        except Exception as e:
            logger.warning(f"Failed to get disk I/O statistics: {e}")
        
        return None
    
    async def collect_metrics(self) -> SystemMetrics:
        """Collect comprehensive system performance metrics."""
        timestamp = datetime.now()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)  # 1 second interval for accuracy
        cpu_count = psutil.cpu_count()
        
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_freq_dict = {
                "current": cpu_freq.current,
                "min": cpu_freq.min,
                "max": cpu_freq.max
            } if cpu_freq else None
        except Exception:
            cpu_freq_dict = None
        
        # Load average (Unix systems)
        try:
            load_avg = psutil.getloadavg()
            load_average = list(load_avg)
        except (AttributeError, OSError):
            load_average = None
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk_usage = self._get_disk_usage()
        disk_io = self._get_disk_io_stats()
        
        # Network metrics
        network_io = self._get_network_stats()
        network_connections = len(psutil.net_connections())
        
        # API response times
        api_response_times = await self._monitor_api_endpoints()
        
        # WebSocket health
        websocket_stats = self._monitor_websocket_health()
        
        metrics = SystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            cpu_freq=cpu_freq_dict,
            load_average=load_average,
            memory_total=memory.total,
            memory_available=memory.available,
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_free=memory.free,
            swap_total=swap.total,
            swap_used=swap.used,
            swap_percent=swap.percent,
            disk_usage=disk_usage,
            disk_io=disk_io,
            network_io=network_io,
            network_connections=network_connections,
            api_response_times=api_response_times,
            websocket_connections=websocket_stats["connections"],
            websocket_errors=websocket_stats["errors"]
        )
        
        # Add to history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
        
        return metrics
    
    def check_thresholds(self, metrics: SystemMetrics) -> List[Dict[str, Any]]:
        """Check if any metrics exceed defined thresholds."""
        violations = []
        
        # CPU threshold
        if metrics.cpu_percent > self.thresholds["cpu_percent"]:
            violations.append({
                "metric": "cpu_percent",
                "current": metrics.cpu_percent,
                "threshold": self.thresholds["cpu_percent"],
                "severity": "WARNING" if metrics.cpu_percent < 95 else "CRITICAL"
            })
        
        # Memory threshold
        if metrics.memory_percent > self.thresholds["memory_percent"]:
            violations.append({
                "metric": "memory_percent", 
                "current": metrics.memory_percent,
                "threshold": self.thresholds["memory_percent"],
                "severity": "CRITICAL"
            })
        
        # Swap threshold
        if metrics.swap_percent > self.thresholds["swap_percent"]:
            violations.append({
                "metric": "swap_percent",
                "current": metrics.swap_percent, 
                "threshold": self.thresholds["swap_percent"],
                "severity": "WARNING"
            })
        
        # Disk usage thresholds
        for path, usage in metrics.disk_usage.items():
            if usage["percent"] > self.thresholds["disk_usage_percent"]:
                violations.append({
                    "metric": f"disk_usage_{path}",
                    "current": usage["percent"],
                    "threshold": self.thresholds["disk_usage_percent"],
                    "severity": "WARNING" if usage["percent"] < 95 else "CRITICAL"
                })
        
        # API response time thresholds
        for endpoint, response_time in metrics.api_response_times.items():
            if response_time < 0:  # Failed request
                violations.append({
                    "metric": f"api_availability_{endpoint}",
                    "current": "DOWN",
                    "threshold": "UP", 
                    "severity": "CRITICAL"
                })
            elif response_time > self.thresholds["api_response_time_ms"]:
                violations.append({
                    "metric": f"api_response_time_{endpoint}",
                    "current": response_time,
                    "threshold": self.thresholds["api_response_time_ms"],
                    "severity": "WARNING"
                })
        
        # Load average threshold (if available)
        if metrics.load_average and len(metrics.load_average) > 0:
            if metrics.load_average[0] > self.thresholds["load_average_1m"]:
                violations.append({
                    "metric": "load_average_1m",
                    "current": metrics.load_average[0],
                    "threshold": self.thresholds["load_average_1m"],
                    "severity": "WARNING"
                })
        
        return violations
    
    def calculate_baseline_metrics(self, lookback_minutes: int = 60) -> Dict[str, float]:
        """Calculate baseline metrics from recent history."""
        if not self.metrics_history:
            return {}
        
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        baselines = {}
        
        # Calculate average CPU usage
        cpu_values = [m.cpu_percent for m in recent_metrics]
        baselines["cpu_percent_avg"] = sum(cpu_values) / len(cpu_values)
        
        # Calculate average memory usage
        memory_values = [m.memory_percent for m in recent_metrics]
        baselines["memory_percent_avg"] = sum(memory_values) / len(memory_values)
        
        # Calculate average API response times
        for endpoint in self.api_endpoints:
            response_times = [
                m.api_response_times.get(endpoint, 0) 
                for m in recent_metrics 
                if m.api_response_times.get(endpoint, -1) > 0
            ]
            if response_times:
                baselines[f"api_response_time_{endpoint}_avg"] = sum(response_times) / len(response_times)
        
        self.baselines = baselines
        return baselines
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a comprehensive performance summary."""
        if not self.metrics_history:
            return {"status": "no_data", "metrics_collected": 0}
        
        latest = self.metrics_history[-1]
        violations = self.check_thresholds(latest)
        baselines = self.calculate_baseline_metrics()
        
        # Determine overall health status
        if any(v["severity"] == "CRITICAL" for v in violations):
            health_status = "CRITICAL"
        elif any(v["severity"] == "WARNING" for v in violations):
            health_status = "WARNING"
        else:
            health_status = "HEALTHY"
        
        # API availability summary
        api_availability = {}
        for endpoint, response_time in latest.api_response_times.items():
            api_availability[endpoint] = {
                "status": "UP" if response_time > 0 else "DOWN",
                "response_time_ms": response_time if response_time > 0 else None
            }
        
        return {
            "status": health_status,
            "timestamp": latest.timestamp.isoformat(),
            "metrics_collected": len(self.metrics_history),
            "violations": violations,
            "current_metrics": {
                "cpu_percent": latest.cpu_percent,
                "memory_percent": latest.memory_percent,
                "swap_percent": latest.swap_percent,
                "disk_usage": latest.disk_usage,
                "network_connections": latest.network_connections,
                "websocket_connections": latest.websocket_connections,
            },
            "api_availability": api_availability,
            "baselines": baselines,
            "thresholds": self.thresholds
        }
    
    async def close(self):
        """Close monitoring resources."""
        if self._session and not self._session.closed:
            await self._session.close()