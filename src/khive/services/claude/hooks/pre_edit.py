"""
Claude Code pre-edit hook for observability and coordination.

Called before Claude Code edits files to log events and coordinate with other agents
to prevent conflicts and enable inter-agent awareness.
"""

import json
import sys
from typing import Any

import anyio

from khive.services.claude.hooks.coordination import get_registry
from khive.services.claude.hooks.hook_event import (
    HookEvent,
    HookEventContent,
    hook_event_logger,
    shield,
)


def handle_pre_edit(
    file_paths: list[str], tool_name: str, session_id: str | None = None
) -> dict[str, Any]:
    """Handle pre-edit hook event with inter-agent coordination."""
    try:
        registry = get_registry()
        agent_id = f"agent_{session_id[:8] if session_id else 'unknown'}"

        # Subscribe agent if not already subscribed
        if agent_id not in registry.agent_subscriptions:
            registry.subscribe_agent(agent_id, ["file_edit", "task_complete", "all"])

        # Check for coordination messages from other agents
        coordination_msgs = registry.get_coordination_messages(agent_id)

        # Check if any other agent is editing these files
        conflicts = []
        for file_path in file_paths:
            for conflict in coordination_msgs.get("file_conflicts", []):
                if conflict["file"] == file_path:
                    conflicts.append(conflict)

        # Create and save the hook event
        event = HookEvent(
            content=HookEventContent(
                event_type="pre_edit",
                tool_name=tool_name,
                file_paths=file_paths,
                session_id=session_id,
                metadata={
                    "file_count": len(file_paths),
                    "hook_type": "pre_edit",
                    "agent_id": agent_id,
                    "conflicts_detected": len(conflicts),
                    "coordination_messages": coordination_msgs["message_count"],
                },
            )
        )

        try:
            anyio.run(shield, event.save)
            # Event will be broadcast to other agents via HookEventBroadcaster
        except Exception as e:
            hook_event_logger.error(
                f"Failed to save event: {e}",
                exc_info=True,
            )

        result = {
            "proceed": len(conflicts) == 0,  # Don't proceed if conflicts
            "file_count": len(file_paths),
            "event_logged": True,
            "coordination_active": True,
        }

        # Add conflict warnings
        if conflicts:
            result["conflicts"] = [
                f"{c['agent']} is editing {c['file']}" for c in conflicts
            ]
            result["suggestion"] = "Coordinate with other agents or wait"

        # Add insights from other agents
        if coordination_msgs["related_completions"]:
            result["related_work"] = [
                f"{c['agent']}: {c['output']}"
                for c in coordination_msgs["related_completions"][:2]
            ]

        return result

    except Exception as e:
        return {
            "proceed": True,  # Don't block on error
            "error": str(e),
            "event_logged": False,
        }


def main():
    """Main entry point for pre-edit hook."""
    try:
        # Read JSON input from stdin
        hook_input = json.load(sys.stdin)

        # Extract session information
        session_id = hook_input.get("session_id", None)

        # Extract tool information from hook input
        tool_input = hook_input.get("tool_input", {})
        tool_name = hook_input.get("tool_name", "unknown")

        # Extract file paths from tool input
        file_paths = []
        if "file_path" in tool_input:
            file_paths = [tool_input["file_path"]]
        elif "file_paths" in tool_input:
            file_paths = tool_input["file_paths"]

        result = handle_pre_edit(file_paths, tool_name, session_id)

        # Always output JSON for Claude Code
        print(json.dumps(result))

        # Exit with 0 for proceed, 1 for block
        sys.exit(0 if result.get("proceed", True) else 1)

    except Exception as e:
        print(f"Error in pre-edit hook: {e}", file=sys.stderr)
        # Default to proceed on error
        print(json.dumps({"proceed": True, "error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
