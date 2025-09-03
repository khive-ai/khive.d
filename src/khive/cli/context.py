"""
Workspace context injection for agent coordination.

Since environment variables don't work in multi-agent isolated settings,
we use workspace context files to pass agent_id and coordination_id.
"""

import json
import os
from pathlib import Path

CONTEXT_FILE = ".khive_context.json"


def write_context(
    agent_id: str, coordination_id: str, workspace_dir: str | None = None
) -> None:
    """Write agent context to workspace file."""
    workspace = Path(workspace_dir) if workspace_dir else Path.cwd()
    context_file = workspace / CONTEXT_FILE

    context = {
        "agent_id": agent_id,
        "coordination_id": coordination_id,
        "created_at": os.environ.get("DATE", "unknown"),
    }

    context_file.write_text(json.dumps(context, indent=2))


def load_context() -> dict[str, str] | None:
    """Load agent context from current workspace."""
    context_file = Path.cwd() / CONTEXT_FILE

    if not context_file.exists():
        # Try parent directories up to 3 levels
        for parent in Path.cwd().parents[:3]:
            context_file = parent / CONTEXT_FILE
            if context_file.exists():
                break
        else:
            return None

    try:
        return json.loads(context_file.read_text())
    except Exception:
        return None


def get_agent_id() -> str | None:
    """Get agent ID from workspace context file only."""
    context = load_context()
    if context and context.get("agent_id"):
        return context["agent_id"]

    return None  # NO env var fallback - only workspace context


def get_coordination_id() -> str | None:
    """Get coordination ID from workspace context file only."""
    context = load_context()
    if context and context.get("coordination_id"):
        return context["coordination_id"]

    return None  # NO env var fallback - only workspace context
