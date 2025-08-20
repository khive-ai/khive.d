"""
Claude Code post-agent-spawn hook for observability.

Called after Claude Code spawns Task agents to analyze task completion and results.
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


def handle_post_agent_spawn(
    output: str, session_id: str | None = None
) -> dict[str, Any]:
    """Handle post-agent-spawn hook event."""
    try:
        # Basic output analysis
        output_length = len(output)
        has_error = any(
            error in output.lower()
            for error in ["error", "failed", "exception", "traceback"]
        )
        success = not has_error and output_length > 0
        line_count = output.count("\n")

        # Agent task completion analysis
        contains_deliverable = any(
            keyword in output.lower()
            for keyword in ["completed", "finished", "delivered", "summary", "result"]
        )
        contains_code = any(
            marker in output for marker in ["```", "def ", "class ", "function"]
        )

        event = HookEvent(
            content=HookEventContent(
                event_type="post_agent_spawn",
                tool_name="Task",
                output=output,
                session_id=session_id,
                metadata={
                    "output_length": output_length,
                    "has_error": has_error,
                    "success": success,
                    "line_count": line_count,
                    "contains_deliverable": contains_deliverable,
                    "contains_code": contains_code,
                    "hook_type": "post_agent_spawn",
                },
            )
        )

        try:
            anyio.run(shield, event.save)
        except Exception as e:
            hook_event_logger.error(
                f"Failed to save event: {e}",
                exc_info=True,
            )

        return {
            "output_length": output_length,
            "success": success,
            "contains_deliverable": contains_deliverable,
            "event_logged": True,
        }

    except Exception as e:
        return {"error": str(e), "event_logged": False}


def main():
    """Main entry point for post-agent-spawn hook."""
    try:
        # Read JSON input from stdin
        hook_input = json.load(sys.stdin)

        # Extract session information
        session_id = hook_input.get("session_id", None)

        # Extract output from hook input
        tool_output = hook_input.get("tool_output", "")

        result = handle_post_agent_spawn(tool_output, session_id)

        # Always output JSON for Claude Code
        print(json.dumps(result))

        sys.exit(0)

    except Exception as e:
        print(f"Error in post-agent-spawn hook: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
