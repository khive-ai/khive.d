"""
Claude Code pre-command hook for observability.

Called before Claude Code executes bash commands to log and analyze command patterns.
Auto-detects running daemon and uses it when available for better performance.
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


def handle_pre_command(command: str, session_id: str | None = None) -> dict[str, Any]:
    """Handle pre-command hook event with coordination and persistence."""

    # Always do basic analysis and persistence
    dangerous_commands = ["rm -rf", "sudo rm", "format", "del /s", "> /dev/null"]
    is_dangerous = any(danger in command.lower() for danger in dangerous_commands)
    command_length = len(command)
    has_pipes = "|" in command
    has_redirects = ">" in command or "<" in command

    # Create and save hook event for persistence
    event = HookEvent(
        content=HookEventContent(
            event_type="pre_command",
            tool_name="Bash",
            command=command,
            session_id=session_id,
            metadata={
                "command_length": command_length,
                "is_dangerous": is_dangerous,
                "has_pipes": has_pipes,
                "has_redirects": has_redirects,
                "hook_type": "pre_command",
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
                    "command": command,
                    "session_id": session_id,
                }
                coordination_result = client.process_hook("pre_command", hook_data)
        except Exception as e:
            hook_event_logger.debug(f"Daemon coordination failed: {e}")

    # Combine results
    result = {
        "proceed": coordination_result.get("proceed", True),
        "command_length": command_length,
        "is_dangerous": is_dangerous,
        "event_logged": event_logged,
        "coordination_active": bool(coordination_result),
    }

    # Add coordination insights if available
    if coordination_result:
        result.update(
            {
                k: v
                for k, v in coordination_result.items()
                if k not in ["proceed", "event_logged"]
            }
        )

    return result


def main():
    """Main entry point for pre-command hook."""
    try:
        # Read JSON input from stdin
        hook_input = json.load(sys.stdin)

        # Extract session information
        session_id = hook_input.get("session_id", None)

        # Extract command from tool input
        tool_input = hook_input.get("tool_input", {})
        command = tool_input.get("command", "")

        result = handle_pre_command(command, session_id)

        # Always output JSON for Claude Code
        print(json.dumps(result))

        # Exit with 0 for proceed, 1 for block
        sys.exit(0 if result.get("proceed", True) else 1)

    except Exception as e:
        print(f"Error in pre-command hook: {e}", file=sys.stderr)
        # Default to proceed on error
        print(json.dumps({"proceed": True, "error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
