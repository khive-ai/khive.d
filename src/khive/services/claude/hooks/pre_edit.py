"""
Claude Code pre-edit hook - PREVENTS file conflicts between agents.

This hook actually works with Claude Code to prevent multiple agents
from editing the same file simultaneously.
"""

import json
import sys
import os
from typing import Any
from pathlib import Path

from khive.daemon.client import get_daemon_client


def handle_pre_edit(
    file_paths: list[str], tool_name: str, session_id: str | None = None
) -> dict[str, Any]:
    """Check if files can be edited - PREVENTS CONFLICTS."""
    
    # Get agent ID from session or environment
    agent_id = session_id[:8] if session_id else os.environ.get("CLAUDE_AGENT_ID", "agent_unknown")
    
    # Check daemon for file locks
    try:
        client = get_daemon_client()
        if not client.is_running():
            # Daemon not running - allow edit but warn
            return {
                "proceed": True,
                "warning": "Coordination daemon not running - file conflicts possible"
            }
        
        # Check each file for locks
        blocked_files = []
        for file_path in file_paths:
            # Request file lock via daemon
            response = client._request("POST", "/api/coordinate/file-register", {
                "file_path": file_path,
                "agent_id": agent_id
            })
            
            if response.get("status") == "locked":
                blocked_files.append({
                    "file": file_path,
                    "locked_by": response.get("locked_by"),
                    "expires_in": response.get("expires_in_seconds", 0)
                })
        
        if blocked_files:
            # Some files are locked - block the edit
            return {
                "proceed": False,
                "blocked_files": blocked_files,
                "message": f"Cannot edit - {len(blocked_files)} file(s) locked by other agents",
                "suggestion": "Try different files or wait for locks to expire"
            }
        
        # All files available - proceed
        return {
            "proceed": True,
            "message": f"File locks acquired for {len(file_paths)} file(s)",
            "agent_id": agent_id
        }
        
    except Exception as e:
        # On error, allow edit but warn
        return {
            "proceed": True,
            "error": str(e),
            "warning": "Coordination check failed - proceeding without lock protection"
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
