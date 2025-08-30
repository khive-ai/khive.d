"""
Khive Daemon Client - Lightweight client for daemon communication.

Handles communication with the khive daemon for stateful operations.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

from khive.utils import get_logger

logger = get_logger("KhiveClient", "📡 [KHIVE-CLIENT]")

# Client configuration
DAEMON_URL = os.getenv("KHIVE_DAEMON_URL", "http://127.0.0.1:11434")
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
    
    def health(self) -> Dict[str, Any]:
        """Get daemon health status."""
        try:
            response = self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get daemon health: {e}")
            return {"status": "error", "error": str(e)}
    
    def plan(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate orchestration plan."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/plan",
                json={"task_description": task_description, "context": context},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError("Khive daemon is not running. Start it with: khive daemon start")
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise
    
    def coordinate_start(self, task_description: str, agent_id: str) -> Dict[str, Any]:
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
    
    def coordinate_complete(self, task_id: str, output: str, artifacts: list[str] = None) -> bool:
        """Register task completion."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/coordinate/complete",
                json={
                    "task_id": task_id,
                    "output": output,
                    "artifacts": artifacts or [],
                },
            )
            response.raise_for_status()
            return True
        except httpx.ConnectError:
            logger.debug("Daemon not running, skipping coordination")
            return False
        except Exception as e:
            logger.error(f"Failed to coordinate complete: {e}")
            return False
    
    def get_insights(self, task_description: str) -> Dict[str, Any]:
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
    
    def session_init(self, resume: bool = False) -> Dict[str, Any]:
        """Initialize or resume session."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/session/init",
                json={"resume": resume},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError("Khive daemon is not running. Start it with: khive daemon start")
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            raise
    
    def session_end(self) -> Dict[str, Any]:
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
    
    def session_status(self) -> Dict[str, Any]:
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
    
    def process_hook(self, hook_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def shutdown(self) -> bool:
        """Request daemon shutdown."""
        try:
            response = self.client.post(f"{self.base_url}/api/shutdown")
            response.raise_for_status()
            return True
        except Exception:
            return False


# Global client instance for easy access
_global_client: Optional[KhiveDaemonClient] = None


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