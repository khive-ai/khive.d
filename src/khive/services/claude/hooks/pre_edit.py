"""
Claude Code pre-edit hook for observability.

Called before Claude Code edits files to log and monitor file modification events.
"""

import json
import sys
from typing import Any

import anyio

from khive.services.claude.hooks.hook_event import (HookEvent,
                                                    HookEventContent,
                                                    hook_event_logger, shield)


def handle_pre_edit(
    file_paths: list[str], tool_name: str, session_id: str | None = None
) -> dict[str, Any]:
    """Handle pre-edit hook event."""
    try:
        event = HookEvent(
            content=HookEventContent(
                event_type="pre_edit",
                tool_name=tool_name,
                file_paths=file_paths,
                session_id=session_id,
                metadata={"file_count": len(file_paths), "hook_type": "pre_edit"},
            )
        )

        try:
            anyio.run(shield, event.save)
        except Exception as e:
            hook_event_logger.error(
                f"Failed to save event: {e}",
                exc_info=True,
            )

        return {"proceed": True, "file_count": len(file_paths), "event_logged": True}

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
