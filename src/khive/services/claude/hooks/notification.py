"""
Claude Code notification hook for observability.

Called when Claude Code sends system notifications to monitor system events.
"""

import json
import sys
from typing import Any

import anyio

from khive.services.claude.hooks.hook_event import (HookEvent,
                                                    HookEventContent,
                                                    hook_event_logger, shield)


def handle_notification(message: str, session_id: str | None = None) -> dict[str, Any]:
    """Handle system notification hook event."""
    try:
        # Basic notification analysis
        message_length = len(message)
        is_error = any(
            error in message.lower()
            for error in ["error", "failed", "exception", "critical"]
        )
        is_warning = "warning" in message.lower() or "warn" in message.lower()
        is_info = not is_error and not is_warning

        # Notification categorization
        severity = "error" if is_error else "warning" if is_warning else "info"
        contains_file_path = "/" in message or "\\" in message
        contains_timestamp = any(char.isdigit() for char in message) and ":" in message

        event = HookEvent(
            content=HookEventContent(
                event_type="notification",
                tool_name="Notification",
                session_id=session_id,
                metadata={
                    "message": message,
                    "message_length": message_length,
                    "severity": severity,
                    "is_error": is_error,
                    "is_warning": is_warning,
                    "is_info": is_info,
                    "contains_file_path": contains_file_path,
                    "contains_timestamp": contains_timestamp,
                    "hook_type": "notification",
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
            "message_length": message_length,
            "severity": severity,
            "event_logged": True,
        }

    except Exception as e:
        return {"error": str(e), "event_logged": False}


def main():
    """Main entry point for notification hook."""
    try:
        # Read JSON input from stdin
        hook_input = json.load(sys.stdin)

        # Extract session information
        session_id = hook_input.get("session_id", None)

        # Extract notification message from hook input
        message = hook_input.get("message", "")

        result = handle_notification(message, session_id)

        # Always output JSON for Claude Code
        print(json.dumps(result))

        sys.exit(0)

    except Exception as e:
        print(f"Error in notification hook: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
