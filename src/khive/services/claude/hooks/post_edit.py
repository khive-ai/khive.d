#!/usr/bin/env python3
# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: MIT

"""
Claude Code post-edit hook for observability.

Called after Claude Code successfully edits files to log results and analyze patterns.
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


def handle_post_edit(
    file_paths: list[str],
    output: str,
    tool_name: str = "Edit",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Handle post-edit hook event."""
    try:
        # Basic pattern analysis
        lines_changed = output.count("\n") if output else 0
        success = "Error" not in output and "failed" not in output.lower()

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
        except Exception as e:
            hook_event_logger.error(
                f"Failed to save event: {e}",
                exc_info=True,
            )

        return {
            "file_count": len(file_paths),
            "lines_changed": lines_changed,
            "success": success,
            "event_logged": True,
        }

    except Exception as e:
        return {"error": str(e), "event_logged": False}


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
