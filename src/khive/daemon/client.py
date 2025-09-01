"""
Khive Daemon Client - Lightweight client for daemon communication.

Handles communication with the khive daemon for stateful operations.
"""

import os
import time
from typing import Any, Optional

import httpx

from khive.utils import get_logger

logger = get_logger("KhiveClient", "📡 [KHIVE-CLIENT]")

# Client configuration
DAEMON_URL = os.getenv("KHIVE_DAEMON_URL", "http://127.0.0.1:11634")
CLIENT_TIMEOUT = 30.0  # seconds


class KhiveDaemonClient:
    """Client for communicating with khive daemon."""

    def __init__(self, base_url: str = DAEMON_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=CLIENT_TIMEOUT)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def is_running(self) -> bool:
        """Check if daemon is running."""
        try:
            response = self.client.get(f"{self.base_url}/")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def health(self) -> dict[str, Any]:
        """Get daemon health status."""
        try:
            response = self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get daemon health: {e}")
            return {"status": "error", "error": str(e)}

    def plan(
        self, task_description: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate orchestration plan."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/plan",
                json={"task_description": task_description, "context": context},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                "Khive daemon is not running. Start it with: khive daemon start"
            )
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise

    def coordinate_start(self, task_description: str, agent_id: str) -> dict[str, Any]:
        """Register task start with coordination."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/coordinate/start",
                json={"task_description": task_description, "agent_id": agent_id},
            )
            response.raise_for_status()
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
        """Get active file operations (file_path -> agent_id mapping)."""
        try:
            response = self.client.get(
                f"{self.base_url}/api/coordinate/file-operations"
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, no file coordination available")
            return {}
        except Exception as e:
            logger.error(f"Failed to get active file operations: {e}")
            return {}

    def register_file_operation(self, file_path: str, agent_id: str) -> dict[str, Any]:
        """Register file operation with conflict detection."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/coordinate/file-operations/register",
                json={"file_path": file_path, "agent_id": agent_id},
            )
            response.raise_for_status()
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
        """Initialize or resume session."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/session/init",
                json={"resume": resume},
            )
            response.raise_for_status()
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
        context: Optional[str] = None,
        pattern: str = "fanout", 
        max_agents: int = 8, 
        visualize: bool = False
    ) -> dict[str, Any]:
        """Execute orchestration for a task description."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/orchestrate/task",
                json={
                    "task_description": task_description,
                    "context": context,
                    "pattern": pattern,
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
            logger.error(f"Failed to orchestrate task: {e}")
            raise

    def orchestrate_issue(
        self, 
        issue_num: int, 
        max_agents: int = 8, 
        visualize: bool = False
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

    def get_orchestration_session_status(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get status of specific orchestration session."""
        try:
            response = self.client.get(f"{self.base_url}/api/orchestrate/sessions/{session_id}")
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
            response = self.client.post(f"{self.base_url}/api/orchestrate/sessions/{session_id}/stop")
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
        """Get comprehensive coordination metrics report."""
        try:
            response = self.client.get(f"{self.base_url}/api/metrics/report")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.debug("Daemon not running, returning empty metrics")
            return {
                "summary": {"overall_effectiveness": 0, "total_events": 0},
                "detailed_metrics": {},
                "recommendations": ["Daemon not running - start with 'khive daemon start'"],
            }
        except Exception as e:
            logger.error(f"Failed to get metrics report: {e}")
            return {"error": str(e)}

    def get_metrics_status(self) -> dict[str, Any]:
        """Get live metrics status for real-time monitoring."""
        try:
            response = self.client.get(f"{self.base_url}/api/metrics/status")
            response.raise_for_status()
            return response.json()
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
                "daemon_status": "not_running",
            }
        except Exception as e:
            logger.error(f"Failed to get metrics status: {e}")
            return {"error": str(e)}

    def shutdown(self) -> bool:
        """Request daemon shutdown."""
        try:
            response = self.client.post(f"{self.base_url}/api/shutdown")
            response.raise_for_status()
            return True
        except Exception:
            return False


# Global client instance for easy access
_global_client: KhiveDaemonClient | None = None


def get_daemon_client() -> KhiveDaemonClient:
    """Get or create global daemon client."""
    global _global_client
    if _global_client is None:
        _global_client = KhiveDaemonClient()
    return _global_client


def ensure_daemon_running():
    """Ensure daemon is running, with helpful message if not."""
    client = get_daemon_client()
    if not client.is_running():
        logger.warning("⚠️  Khive daemon is not running")
        logger.info("Start it with: khive daemon start")
        logger.info("Running in degraded mode (no coordination/caching)")
        return False
    return True
