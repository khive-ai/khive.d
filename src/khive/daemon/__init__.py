"""
Khive Daemon - Ollama-style persistent service for stateful operations.

The daemon handles:
- Coordination registry (task deduplication, file locks)
- Planning service (pattern caching, learning)
- Session management (state across commands)
- Artifact tracking (shared context)
- Hook processing (for coordination)

Usage:
  khive daemon start    # Start daemon in background
  khive daemon stop     # Stop daemon
  khive daemon status   # Check status
  khive daemon logs     # View logs
"""

from .client import KhiveDaemonClient, ensure_daemon_running, get_daemon_client
from .server import KhiveDaemonServer

__all__ = [
    "KhiveDaemonServer",
    "KhiveDaemonClient", 
    "get_daemon_client",
    "ensure_daemon_running",
]
