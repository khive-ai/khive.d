"""
Claude Code post-edit hook for observability.

Called after Claude Code successfully edits files to log results and analyze patterns.
Requires daemon for coordination.
"""

import json
import sys
from typing import Any

import anyio
from khive.services.claude.hooks.hook_event import (
    HookEvent,
    HookEventContent,
    hook_event_logger,
    shield,
)

# Try to import daemon client for auto-detection
try:
    from khive.daemon.client import get_daemon_client

    DAEMON_AVAILABLE = True
except ImportError:
    DAEMON_AVAILABLE = False


def handle_post_edit(
    file_paths: list[str],
    output: str,
    tool_name: str = "Edit",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Handle post-edit hook event with coordination and persistence."""

    # Basic pattern analysis
    lines_changed = output.count("\n") if output else 0
    success = "Error" not in output and "failed" not in output.lower()

    # Create and save hook event for persistence
    event = HookEvent(
        content=HookEventContent(
            event_type="post_edit",
            tool_name=tool_name,
            file_paths=file_paths,
            output=output,
            session_id=session_id,
            metadata={
                "file_count": len(file_paths),
                "lines_changed": lines_changed,
                "success": success,
                "hook_type": "post_edit",
            },
        )
    )

    try:
        anyio.run(shield, event.save)
        event_logged = True
    except Exception as e:
        hook_event_logger.error(f"Failed to save event: {e}", exc_info=True)
        event_logged = False

    # Try coordination via daemon (optional)
    coordination_result = {}
    if DAEMON_AVAILABLE:
        try:
            client = get_daemon_client()
            if client.is_running():
                hook_data = {
                    "file_paths": file_paths,
                    "output": output,
                    "tool_name": tool_name,
                    "session_id": session_id,
                }
                coordination_result = client.process_hook("post_edit", hook_data)
        except Exception as e:
            hook_event_logger.debug(f"Daemon coordination failed: {e}")

    # Combine results
    result = {
        "file_count": len(file_paths),
        "lines_changed": lines_changed,
        "success": success,
        "event_logged": event_logged,
        "coordination_active": bool(coordination_result),
    }

    # Add coordination insights if available
    if coordination_result:
        result.update({k: v for k, v in coordination_result.items()})

    return result


def main():
    """Main entry point for post-edit hook."""
    try:
        # Read JSON input from stdin
        hook_input = json.load(sys.stdin)

        # Extract session information
        session_id = hook_input.get("session_id", None)

        # Extract tool information from hook input
        tool_input = hook_input.get("tool_input", {})
        tool_name = hook_input.get("tool_name", "Edit")
        tool_output = hook_input.get("tool_output", "")

        # Extract file paths from tool input
        file_paths = []
        if "file_path" in tool_input:
            file_paths = [tool_input["file_path"]]
        elif "file_paths" in tool_input:
            file_paths = tool_input["file_paths"]

        result = handle_post_edit(file_paths, tool_output, tool_name, session_id)

        # Always output JSON for Claude Code
        print(json.dumps(result))

        sys.exit(0)

    except Exception as e:
        print(f"Error in post-edit hook: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
