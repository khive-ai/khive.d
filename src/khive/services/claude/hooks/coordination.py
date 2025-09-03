"""
Real coordination for LLM agents - solving actual problems.

Key problems this solves:
1. File edit conflicts - Multiple agents editing same file
2. Duplicate work - Agents unknowingly doing same task
3. Missing context - Agents can't see what others did
4. No handoffs - Agents can't pass artifacts

Clean, honest coordination - only features that actually work.
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any

# Stopwords for duplicate detection
STOP = {
    "the",
    "a",
    "an",
    "to",
    "for",
    "and",
    "or",
    "api",
    "endpoint",
    "add",
    "fix",
    "create",
    "update",
}


def _sig(t: str) -> set[str]:
    """Extract signature tokens from task description."""
    toks = re.findall(r"[a-z0-9]+", t.lower())
    return {w for w in toks if w not in STOP and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Calculate Jaccard similarity between two token sets."""
    u = len(a | b)
    return 0.0 if u == 0 else len(a & b) / u


@dataclass
class AgentWork:
    """What an agent is currently working on."""

    agent_id: str
    task: str
    files_editing: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    status: str = "active"  # active, completed, failed

    def duration_seconds(self) -> float:
        return time.time() - self.started_at


@dataclass
class FileEdit:
    """Track who's editing what file."""

    file_path: str
    agent_id: str
    locked_at: float = field(default_factory=time.time)
    lock_duration_seconds: float = 300  # 5 minute default

    def is_expired(self) -> bool:
        return time.time() > (self.locked_at + self.lock_duration_seconds)


@dataclass
class Artifact:
    """Simple artifact passing between agents."""

    artifact_id: str
    created_by: str
    content: str
    file_path: str | None = None
    created_at: float = field(default_factory=time.time)


def _norm(path: str) -> str:
    """Normalize path to resolved absolute path."""
    try:
        return Path(path).resolve().as_posix()
    except Exception:
        return str(PurePath(path))


def _key(path: str) -> tuple[int, int] | str:
    """Get file key based on device+inode or normalized path."""
    p = Path(path)
    try:
        st = p.stat()
        return (st.st_dev, st.st_ino)  # OS-true identity via device + inode
    except Exception:
        return _norm(path)  # Fallback to normalized path


class CoordinationRegistry:
    """
    Real coordination that actually helps LLM agents.
    No fake features - just what works.
    """

    def __init__(self):
        # Core tracking
        self.active_agents: dict[str, AgentWork] = {}
        self.file_locks: dict[tuple[int, int] | str, FileEdit] = {}  # inode-based keys
        self.artifacts: dict[str, Artifact] = {}

        # Session mapping - Claude session ID -> agent ID
        self.session_to_agent: dict[str, str] = {}

        # Simple metrics
        self.conflicts_prevented = 0
        self.duplicates_avoided = 0
        self.artifacts_shared = 0

    def register_agent_work(
        self, agent_id: str, task: str, files: list[str] = None
    ) -> dict[str, Any]:
        """
        Register what an agent is working on.
        This provides VISIBILITY to other agents.
        """
        # Check for duplicate work using token-Jaccard similarity
        sig = _sig(task)
        for existing_agent, work in self.active_agents.items():
            if existing_agent != agent_id:
                if _jaccard(sig, _sig(work.task)) >= 0.7:
                    self.duplicates_avoided += 1
                    return {
                        "status": "duplicate_detected",
                        "message": f"Agent {existing_agent} already working on similar task",
                        "existing_task": work.task,
                        "suggestion": "Consider different task or coordinate with existing agent",
                    }

        # Register the work
        self.active_agents[agent_id] = AgentWork(
            agent_id=agent_id, task=task, files_editing=files or []
        )

        return {
            "status": "registered",
            "message": "Work registered successfully",
            "agent_id": agent_id,
        }

    def request_file_lock(self, agent_id: str, file_path: str) -> dict[str, Any]:
        """
        Request exclusive lock on a file.
        This PREVENTS file edit conflicts - the #1 problem for multi-agent work.
        """
        # Use normalized key for locks
        k = _key(file_path)

        # Clean expired locks
        expired = [f for f, lock in self.file_locks.items() if lock.is_expired()]
        for f in expired:
            del self.file_locks[f]

        # Check if file is locked
        if k in self.file_locks:
            lock = self.file_locks[k]
            if lock.agent_id != agent_id:
                self.conflicts_prevented += 1
                return {
                    "status": "locked",
                    "message": f"File locked by {lock.agent_id}",
                    "locked_by": lock.agent_id,
                    "expires_in_seconds": max(
                        0, lock.lock_duration_seconds - (time.time() - lock.locked_at)
                    ),
                    "suggestion": "Wait for lock to expire or work on different file",
                }

        # Grant the lock
        self.file_locks[k] = FileEdit(file_path=file_path, agent_id=agent_id)

        # Update agent's file list
        if agent_id in self.active_agents:
            if file_path not in self.active_agents[agent_id].files_editing:
                self.active_agents[agent_id].files_editing.append(file_path)

        return {
            "status": "granted",
            "message": "File lock granted",
            "expires_in_seconds": 300,
        }

    def release_file_lock(self, agent_id: str, file_path: str) -> dict[str, Any]:
        """Release file lock when done editing."""
        k = _key(file_path)
        if k in self.file_locks:
            if self.file_locks[k].agent_id == agent_id:
                del self.file_locks[k]

                # Update agent's file list
                if agent_id in self.active_agents:
                    if file_path in self.active_agents[agent_id].files_editing:
                        self.active_agents[agent_id].files_editing.remove(file_path)

                return {"status": "released", "message": "Lock released"}

        return {"status": "not_found", "message": "No lock found"}

    def renew_file_lock(self, agent_id: str, file_path: str) -> dict[str, Any]:
        """Renew file lock to extend TTL without releasing."""
        k = _key(file_path)
        if k in self.file_locks:
            lock = self.file_locks[k]
            if lock.agent_id == agent_id:
                lock.locked_at = time.time()
                return {
                    "status": "renewed",
                    "expires_in_seconds": lock.lock_duration_seconds,
                }
        return {"status": "not_owner", "message": "Cannot renew - not lock owner"}

    def share_artifact(
        self, agent_id: str, content: str, file_path: str | None = None
    ) -> str:
        """
        Share an artifact for other agents to use.
        Simple but effective handoff mechanism.
        """
        artifact_id = f"artifact_{agent_id}_{int(time.time())}"

        self.artifacts[artifact_id] = Artifact(
            artifact_id=artifact_id,
            created_by=agent_id,
            content=content,
            file_path=file_path,
        )

        self.artifacts_shared += 1
        return artifact_id

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        """Retrieve a shared artifact."""
        return self.artifacts.get(artifact_id)

    def get_status(self) -> dict[str, Any]:
        """
        Get current coordination status.
        This is what agents need to see to coordinate effectively.
        """
        return {
            "active_agents": len(self.active_agents),
            "active_work": [
                {
                    "agent": work.agent_id,
                    "task": work.task[:100],  # First 100 chars
                    "files": work.files_editing,
                    "duration_seconds": work.duration_seconds(),
                }
                for work in self.active_agents.values()
            ],
            "locked_files": [
                {
                    "file": lock.file_path,
                    "locked_by": lock.agent_id,
                    "expires_in": max(
                        0, lock.lock_duration_seconds - (time.time() - lock.locked_at)
                    ),
                }
                for lock in self.file_locks.values()
            ],
            "available_artifacts": [
                {
                    "id": artifact.artifact_id,
                    "created_by": artifact.created_by,
                    "has_file": artifact.file_path is not None,
                }
                for artifact in self.artifacts.values()
            ],
            "metrics": {
                "conflicts_prevented": self.conflicts_prevented,
                "duplicates_avoided": self.duplicates_avoided,
                "artifacts_shared": self.artifacts_shared,
            },
        }

    def complete_work(self, agent_id: str) -> dict[str, Any]:
        """Mark agent's work as complete and release all locks."""
        if agent_id not in self.active_agents:
            return {"status": "not_found", "message": "Agent not found"}

        work = self.active_agents[agent_id]

        # Release all file locks
        files_released = []
        for file_path in list(work.files_editing):
            if (
                file_path in self.file_locks
                and self.file_locks[file_path].agent_id == agent_id
            ):
                del self.file_locks[file_path]
                files_released.append(file_path)

        # Mark as completed
        work.status = "completed"
        del self.active_agents[agent_id]

        return {
            "status": "completed",
            "message": "Work completed",
            "files_released": files_released,
            "duration_seconds": work.duration_seconds(),
        }

    def register_session_mapping(self, session_id: str, agent_id: str):
        """Map Claude session ID to agent ID."""
        self.session_to_agent[session_id] = agent_id

    def get_agent_id_from_session(self, session_id: str) -> str | None:
        """Get agent ID from Claude session ID."""
        return self.session_to_agent.get(session_id)

    def cleanup_session(self, session_id: str):
        """Clean up session mapping when agent completes."""
        if session_id in self.session_to_agent:
            del self.session_to_agent[session_id]


# Global registry instance
_registry: CoordinationRegistry | None = None


def get_registry() -> CoordinationRegistry:
    """Get the global registry instance."""
    global _registry
    if _registry is None:
        _registry = CoordinationRegistry()
    return _registry


# High-level convenience functions that agents actually use
def before_file_edit(agent_id: str, file_path: str) -> bool:
    """
    Call before editing a file. Returns True if ok to proceed.
    THIS IS THE MOST IMPORTANT FUNCTION - prevents edit conflicts.
    """
    registry = get_registry()
    result = registry.request_file_lock(agent_id, file_path)
    return result["status"] == "granted"


def after_file_edit(agent_id: str, file_path: str):
    """Call after editing a file to release lock."""
    registry = get_registry()
    registry.release_file_lock(agent_id, file_path)


def check_duplicate_work(agent_id: str, task: str) -> str | None:
    """Check if another agent is already doing this task."""
    registry = get_registry()
    result = registry.register_agent_work(agent_id, task)
    if result["status"] == "duplicate_detected":
        return result["existing_task"]
    return None


def share_result(agent_id: str, content: str, file_path: str | None = None) -> str:
    """Share a result/artifact for other agents."""
    registry = get_registry()
    return registry.share_artifact(agent_id, content, file_path)


def get_shared_result(artifact_id: str) -> str | None:
    """Get a shared result/artifact from another agent."""
    registry = get_registry()
    artifact = registry.get_artifact(artifact_id)
    return artifact.content if artifact else None


def whats_happening() -> dict[str, Any]:
    """See what all agents are working on - provides visibility."""
    registry = get_registry()
    return registry.get_status()
