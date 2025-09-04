"""
Khive Daemon Client - Lightweight client for daemon communication.

Handles communication with the khive daemon for stateful operations.
"""

import os
import time
import asyncio
from typing import Any, Optional
from contextlib import asynccontextmanager
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx

from khive.utils import get_logger

logger = get_logger("KhiveClient", "📡 [KHIVE-CLIENT]")

# Client configuration with performance optimizations
DAEMON_URL = os.getenv("KHIVE_DAEMON_URL", "http://127.0.0.1:11634")
CLIENT_TIMEOUT = 30.0  # seconds
CONNECTION_POOL_SIZE = 10  # Maximum connections in pool
MAX_KEEPALIVE_CONNECTIONS = 5  # Keep-alive connections
KEEPALIVE_EXPIRY = 30.0  # Keep-alive timeout
MAX_RETRIES = 3  # Maximum retry attempts
BACKOFF_FACTOR = 0.3  # Exponential backoff factor


class KhiveDaemonClient:
    """High-performance client for communicating with khive daemon with async optimizations."""

    def __init__(self, base_url: str = DAEMON_URL, enable_async: bool = False):
        self.base_url = base_url.rstrip("/")
        self.enable_async = enable_async
        
        # Connection pooling configuration for better performance
        limits = httpx.Limits(
            max_connections=CONNECTION_POOL_SIZE,
            max_keepalive_connections=MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=KEEPALIVE_EXPIRY
        )
        
        # Optimized transport with retries
        transport = httpx.HTTPTransport(
            limits=limits,
            retries=MAX_RETRIES,
            # Enable HTTP/2 for multiplexing if available
            http2=True
        )
        
        self.client = httpx.Client(
            timeout=httpx.Timeout(CLIENT_TIMEOUT),
            limits=limits,
            transport=transport
        )
        
        # Async client for high-performance operations
        if enable_async:
            self.async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(CLIENT_TIMEOUT),
                limits=limits,
                transport=httpx.AsyncHTTPTransport(
                    limits=limits,
                    retries=MAX_RETRIES,
                    http2=True
                )
            )
            self._async_lock = asyncio.Lock()
        else:
            self.async_client = None
            self._async_lock = None
        
        # Thread pool for async-to-sync bridging
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Performance tracking
        self._request_count = 0
        self._total_request_time = 0.0
        self._failed_requests = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()
        if self.async_client:
            # Use thread pool to handle async cleanup
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            
            if loop:
                loop.create_task(self.async_client.aclose())
            else:
                asyncio.run(self.async_client.aclose())
        
        self._thread_pool.shutdown(wait=False)
    
    async def __aenter__(self):
        if not self.async_client:
            raise RuntimeError("Async client not initialized. Set enable_async=True")
        return self
    
    async def __aexit__(self, *args):
        if self.async_client:
            await self.async_client.aclose()
        self.client.close()
        self._thread_pool.shutdown(wait=False)

    async def _make_async_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make async HTTP request with error handling and retries."""
        if not self.async_client:
            raise RuntimeError("Async client not initialized")
        
        start_time = time.time()
        self._request_count += 1
        
        try:
            async with self._async_lock:
                response = await self.async_client.request(method, url, **kwargs)
                response.raise_for_status()
                
                self._total_request_time += time.time() - start_time
                return response
        except Exception as e:
            self._failed_requests += 1
            self._total_request_time += time.time() - start_time
            raise e
    
    def _make_sync_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make synchronous HTTP request with performance tracking."""
        start_time = time.time()
        self._request_count += 1
        
        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            
            self._total_request_time += time.time() - start_time
            return response
        except Exception as e:
            self._failed_requests += 1
            self._total_request_time += time.time() - start_time
            raise e
    
    def is_running(self) -> bool:
        """Check if daemon is running with optimized health check."""
        try:
            response = self._make_sync_request("GET", f"{self.base_url}/health")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return False
    
    async def is_running_async(self) -> bool:
        """Async version of daemon health check."""
        if not self.async_client:
            # Fallback to sync version
            return await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, self.is_running
            )
        
        try:
            await self._make_async_request("GET", f"{self.base_url}/health")
            return True
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return False

    def health(self) -> dict[str, Any]:
        """Get daemon health status with performance metrics."""
        try:
            response = self._make_sync_request("GET", f"{self.base_url}/health")
            health_data = response.json()
            
            # Add client performance metrics
            if self._request_count > 0:
                health_data["client_metrics"] = self.get_performance_metrics()
            
            return health_data
        except Exception as e:
            logger.error(f"Failed to get daemon health: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_performance_metrics(self) -> dict[str, Any]:
        """Get client performance metrics."""
        if self._request_count == 0:
            return {"no_requests": True}
        
        avg_request_time = self._total_request_time / self._request_count
        success_rate = 1.0 - (self._failed_requests / self._request_count)
        
        return {
            "total_requests": self._request_count,
            "avg_request_time_ms": avg_request_time * 1000,
            "success_rate": success_rate,
            "failed_requests": self._failed_requests,
            "connection_pool_size": CONNECTION_POOL_SIZE,
            "keepalive_connections": MAX_KEEPALIVE_CONNECTIONS,
            "async_enabled": self.async_client is not None
        }

    def plan(
        self, task_description: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate orchestration plan with optimized request handling."""
        try:
            response = self._make_sync_request(
                "POST",
                f"{self.base_url}/api/plan",
                json={"task_description": task_description, "context": context}
            )
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise
    
    async def plan_async(
        self, task_description: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Async version of plan generation for better performance."""
        if not self.async_client:
            # Fallback to sync version in thread pool
            return await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, self.plan, task_description, context
            )
        
        try:
            response = await self._make_async_request(
                "POST",
                f"{self.base_url}/api/plan",
                json={"task_description": task_description, "context": context}
            )
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise

    def coordinate_start(
        self, task_id: str, task_description: str, agent_id: str
    ) -> dict[str, Any]:
        """Register task start with coordination using optimized requests."""
        try:
            response = self._make_sync_request(
                "POST",
                f"{self.base_url}/api/coordinate/start",
                json={
                    "task_id": task_id,
                    "description": task_description,
                    "agent_id": agent_id,
                }
            )
            return response.json()
        except httpx.ConnectError:
            # Coordination is optional - just log and continue
            logger.debug("Daemon not running, skipping coordination")
            return {"task_id": "local-" + str(time.time()), "is_duplicate": False}
        except Exception as e:
            logger.error(f"Failed to coordinate start: {e}")
            return {"task_id": "error", "is_duplicate": False}

    def coordinate_complete(
        self, task_id: str, agent_id: str, output: str, artifacts: list[str] = None
    ) -> dict[str, Any]:
        """Register task completion."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/coordinate/complete",
                json={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "output": output,
                    "artifacts": artifacts or [],
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, skipping coordination")
            return {"context_shared": False, "error": "daemon_not_running"}
        except Exception as e:
            logger.error(f"Failed to coordinate complete: {e}")
            return {"context_shared": False, "error": str(e)}

    def get_insights(self, task_description: str) -> dict[str, Any]:
        """Get coordination insights."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/coordinate/insights",
                json={"task_description": task_description},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, no insights available")
            return {}
        except Exception as e:
            logger.error(f"Failed to get insights: {e}")
            return {}

    def get_active_file_operations(self) -> dict[str, str]:
        """Get active file operations with optimized performance."""
        try:
            response = self._make_sync_request(
                "GET",
                f"{self.base_url}/api/coordinate/file-operations"
            )
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, no file coordination available")
            return {}
        except Exception as e:
            logger.error(f"Failed to get active file operations: {e}")
            return {}
    
    async def get_active_file_operations_async(self) -> dict[str, str]:
        """Async version for better performance in high-throughput scenarios."""
        if not self.async_client:
            return await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, self.get_active_file_operations
            )
        
        try:
            response = await self._make_async_request(
                "GET",
                f"{self.base_url}/api/coordinate/file-operations"
            )
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, no file coordination available")
            return {}
        except Exception as e:
            logger.error(f"Failed to get active file operations: {e}")
            return {}

    def register_file_operation(self, file_path: str, agent_id: str) -> dict[str, Any]:
        """Register file operation with optimized conflict detection."""
        try:
            # Use path normalization for better cache hits
            normalized_path = os.path.normpath(file_path)
            response = self._make_sync_request(
                "POST",
                f"{self.base_url}/api/coordinate/file-operations/register",
                json={"file_path": normalized_path, "agent_id": agent_id}
            )
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, allowing file operation")
            return {"status": "granted", "can_proceed": True}
        except Exception as e:
            logger.error(f"Failed to register file operation: {e}")
            return {"status": "error", "can_proceed": True, "error": str(e)}
    
    async def register_file_operation_async(self, file_path: str, agent_id: str) -> dict[str, Any]:
        """Async file operation registration for better performance."""
        if not self.async_client:
            return await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, self.register_file_operation, file_path, agent_id
            )
        
        try:
            normalized_path = os.path.normpath(file_path)
            response = await self._make_async_request(
                "POST",
                f"{self.base_url}/api/coordinate/file-operations/register",
                json={"file_path": normalized_path, "agent_id": agent_id}
            )
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, allowing file operation")
            return {"status": "granted", "can_proceed": True}
        except Exception as e:
            logger.error(f"Failed to register file operation: {e}")
            return {"status": "error", "can_proceed": True, "error": str(e)}

    def unregister_file_operation(self, file_path: str) -> dict[str, Any]:
        """Unregister file operation and release lock."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/coordinate/file-operations/unregister",
                json={"file_path": file_path},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, file operation cleanup skipped")
            return {"status": "not_running"}
        except Exception as e:
            logger.error(f"Failed to unregister file operation: {e}")
            return {"status": "error", "error": str(e)}

    def get_file_coordination_status(self) -> dict[str, Any]:
        """Get file coordination status and metrics."""
        try:
            response = self.client.get(f"{self.base_url}/api/coordinate/file-status")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, no file coordination status available")
            return {"active_file_operations": 0, "status": "daemon_not_running"}
        except Exception as e:
            logger.error(f"Failed to get file coordination status: {e}")
            return {"status": "error", "error": str(e)}

    def session_init(self, resume: bool = False) -> dict[str, Any]:
        """Initialize or resume session with optimized performance."""
        try:
            response = self._make_sync_request(
                "POST",
                f"{self.base_url}/api/session/init",
                json={"resume": resume}
            )
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            raise
    
    async def session_init_async(self, resume: bool = False) -> dict[str, Any]:
        """Async session initialization for better responsiveness."""
        if not self.async_client:
            return await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, self.session_init, resume
            )
        
        try:
            response = await self._make_async_request(
                "POST",
                f"{self.base_url}/api/session/init",
                json={"resume": resume}
            )
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            raise

    def session_end(self) -> dict[str, Any]:
        """End current session."""
        try:
            response = self.client.post(f"{self.base_url}/api/session/end")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, cannot end session")
            return {"success": False}
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return {"success": False}

    def session_status(self) -> dict[str, Any]:
        """Get session status."""
        try:
            response = self.client.get(f"{self.base_url}/api/session/status")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {"status": "daemon not running"}
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return {"status": "error", "error": str(e)}

    def process_hook(self, hook_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Process a hook through daemon."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/hooks/process",
                json={"hook_type": hook_type, "data": data},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            # Hooks should work without daemon - return sensible defaults
            logger.debug(f"Daemon not running, skipping {hook_type} hook")
            return {"proceed": True} if "pre_" in hook_type else {"success": True}
        except Exception as e:
            logger.error(f"Failed to process hook: {e}")
            return {"proceed": True} if "pre_" in hook_type else {"success": True}

    def orchestrate_task(
        self,
        task_description: str,
        context: str | None = None,
        pattern: str = "fanout",
        max_agents: int = 8,
        visualize: bool = False,
    ) -> dict[str, Any]:
        """Execute orchestration with optimized request handling."""
        try:
            response = self._make_sync_request(
                "POST",
                f"{self.base_url}/api/orchestrate/task",
                json={
                    "task_description": task_description,
                    "context": context,
                    "pattern": pattern,
                    "max_agents": max_agents,
                    "visualize": visualize,
                }
            )
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to orchestrate task: {e}")
            raise
    
    async def orchestrate_task_async(
        self,
        task_description: str,
        context: str | None = None,
        pattern: str = "fanout",
        max_agents: int = 8,
        visualize: bool = False,
    ) -> dict[str, Any]:
        """Async orchestration for high-performance scenarios."""
        if not self.async_client:
            return await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, self.orchestrate_task, task_description, context, pattern, max_agents, visualize
            )
        
        try:
            response = await self._make_async_request(
                "POST",
                f"{self.base_url}/api/orchestrate/task",
                json={
                    "task_description": task_description,
                    "context": context,
                    "pattern": pattern,
                    "max_agents": max_agents,
                    "visualize": visualize,
                }
            )
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to orchestrate task: {e}")
            raise

    def orchestrate_issue(
        self, issue_num: int, max_agents: int = 8, visualize: bool = False
    ) -> dict[str, Any]:
        """Execute orchestration for a GitHub issue."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/orchestrate/issue/{issue_num}",
                json={
                    "max_agents": max_agents,
                    "visualize": visualize,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to orchestrate issue #{issue_num}: {e}")
            raise

    def list_orchestration_sessions(self) -> list[dict[str, Any]]:
        """List active orchestration sessions."""
        try:
            response = self.client.get(f"{self.base_url}/api/orchestrate/sessions")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, no orchestration sessions available")
            return []
        except Exception as e:
            logger.error(f"Failed to list orchestration sessions: {e}")
            return []

    def get_orchestration_session_status(
        self, session_id: str
    ) -> dict[str, Any] | None:
        """Get status of specific orchestration session."""
        try:
            response = self.client.get(
                f"{self.base_url}/api/orchestrate/sessions/{session_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except httpx.ConnectError:
            logger.debug("Daemon not running, session status unavailable")
            return None
        except Exception as e:
            logger.error(f"Failed to get orchestration session status: {e}")
            return None

    def stop_orchestration_session(self, session_id: str) -> bool:
        """Stop a running orchestration session."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/orchestrate/sessions/{session_id}/stop"
            )
            response.raise_for_status()
            result = response.json()
            return result.get("success", False)
        except httpx.ConnectError:
            logger.debug("Daemon not running, cannot stop orchestration session")
            return False
        except Exception as e:
            logger.error(f"Failed to stop orchestration session: {e}")
            return False

    def get_metrics_report(self) -> dict[str, Any]:
        """Get comprehensive coordination metrics with client performance data."""
        try:
            response = self._make_sync_request("GET", f"{self.base_url}/api/metrics/report")
            metrics = response.json()
            
            # Add client performance metrics
            metrics["client_performance"] = self.get_performance_metrics()
            
            return metrics
        except httpx.ConnectError:
            logger.debug("Daemon not running, returning empty metrics")
            return {
                "summary": {"overall_effectiveness": 0, "total_events": 0},
                "detailed_metrics": {},
                "client_performance": self.get_performance_metrics(),
                "recommendations": [
                    "Daemon not running - start with 'khive daemon start'"
                ],
            }
        except Exception as e:
            logger.error(f"Failed to get metrics report: {e}")
            return {"error": str(e), "client_performance": self.get_performance_metrics()}

    def get_metrics_status(self) -> dict[str, Any]:
        """Get live metrics status with enhanced performance monitoring."""
        try:
            response = self._make_sync_request("GET", f"{self.base_url}/api/metrics/status")
            metrics = response.json()
            
            # Enhance with real-time client performance
            metrics["client_performance"] = self.get_performance_metrics()
            metrics["daemon_status"] = "running"
            
            return metrics
        except httpx.ConnectError:
            logger.debug("Daemon not running, returning empty metrics status")
            return {
                "overall_score": 0,
                "scores": {
                    "deduplication": 0,
                    "context_sharing": 0,
                    "conflict_prevention": 0,
                    "task_success": 0,
                    "communication": 0,
                },
                "metrics_summary": {
                    "total_tasks": 0,
                    "duplicates_detected": 0,
                    "contexts_shared": 0,
                    "contexts_inherited": 0,
                    "file_conflicts": 0,
                    "conflicts_prevented": 0,
                    "tasks_completed": 0,
                    "tasks_failed": 0,
                },
                "client_performance": self.get_performance_metrics(),
                "daemon_status": "not_running",
            }
        except Exception as e:
            logger.error(f"Failed to get metrics status: {e}")
            return {"error": str(e), "client_performance": self.get_performance_metrics()}

    def shutdown(self) -> bool:
        """Request daemon shutdown with optimized request."""
        try:
            response = self._make_sync_request("POST", f"{self.base_url}/api/shutdown")
            return True
        except Exception:
            return False
    
    async def shutdown_async(self) -> bool:
        """Async daemon shutdown for better performance."""
        if not self.async_client:
            return await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, self.shutdown
            )
        
        try:
            await self._make_async_request("POST", f"{self.base_url}/api/shutdown")
            return True
        except Exception:
            return False


# Global client instances with performance optimizations
_global_client: Optional[KhiveDaemonClient] = None
_global_async_client: Optional[KhiveDaemonClient] = None
_client_lock = threading.Lock()


def get_daemon_client(async_enabled: bool = False) -> KhiveDaemonClient:
    """Get or create global daemon client with performance optimizations."""
    global _global_client, _global_async_client
    
    with _client_lock:
        if async_enabled:
            if _global_async_client is None:
                _global_async_client = KhiveDaemonClient(enable_async=True)
            return _global_async_client
        else:
            if _global_client is None:
                _global_client = KhiveDaemonClient(enable_async=False)
            return _global_client

@asynccontextmanager
async def get_async_daemon_client():
    """Context manager for async daemon client with proper cleanup."""
    client = KhiveDaemonClient(enable_async=True)
    try:
        async with client:
            yield client
    finally:
        pass  # Cleanup handled by context manager


def ensure_daemon_running(use_async: bool = False) -> bool:
    """Ensure daemon is running with optimized health check."""
    if use_async:
        # Use async version if requested
        async def _check_async():
            async with get_async_daemon_client() as client:
                return await client.is_running_async()
        
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(_check_async())
            # Don't wait indefinitely
            running = loop.run_until_complete(asyncio.wait_for(task, timeout=5.0))
        except (RuntimeError, asyncio.TimeoutError):
            # Fallback to sync check
            client = get_daemon_client()
            running = client.is_running()
    else:
        client = get_daemon_client()
        running = client.is_running()
    
    if not running:
        logger.warning("⚠️  Khive daemon is not running")
        logger.info("Start it with: khive daemon start")
        logger.info("Running in degraded mode (no coordination/caching)")
        return False
    return True

def cleanup_global_clients():
    """Clean up global client instances for graceful shutdown."""
    global _global_client, _global_async_client
    
    with _client_lock:
        if _global_client:
            try:
                _global_client.client.close()
            except Exception:
                pass
            _global_client = None
        
        if _global_async_client:
            try:
                if _global_async_client.async_client:
                    asyncio.create_task(_global_async_client.async_client.aclose())
            except Exception:
                pass
            _global_async_client = None
