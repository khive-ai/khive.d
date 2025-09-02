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
from khive.services.claude.hooks.coordination import get_registry


def handle_pre_edit(
    file_paths: list[str], tool_name: str, session_id: str | None = None
) -> dict[str, Any]:
    """Check if files can be edited - PREVENTS CONFLICTS."""
    
    # Get agent ID from session mapping in coordination registry
    try:
        registry = get_registry() 
        agent_id = registry.get_agent_id_from_session(session_id) if session_id else None
        
        if not agent_id and session_id:
            # Try to auto-map this session to an unmapped agent
            # Find agents that don't have session mappings yet
            unmapped_agents = []
            for active_agent_id in registry.active_agents.keys():
                # Check if this agent already has a session mapping
                has_mapping = any(mapped_agent == active_agent_id 
                                for mapped_agent in registry.session_to_agent.values())
                if not has_mapping:
                    unmapped_agents.append(active_agent_id)
            
            if unmapped_agents:
                # Map to the most recently registered unmapped agent
                agent_id = unmapped_agents[-1]  # Last registered
                registry.register_session_mapping(session_id, agent_id)
                print(f"🔗 Auto-mapped session {session_id[:8]}... to {agent_id}", file=sys.stderr)
        
        if not agent_id:
            # Fallback to session-based ID if no mapping exists
            agent_id = f"session_{session_id[:8]}" if session_id else os.environ.get("CLAUDE_AGENT_ID", "agent_unknown")
    except Exception:
        # Fallback if registry not available
        agent_id = f"session_{session_id[:8]}" if session_id else os.environ.get("CLAUDE_AGENT_ID", "agent_unknown")
    
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
            # Request file lock via daemon using proper client method
            try:
                response = client.client.post(
                    f"{client.base_url}/api/coordinate/file-register",
                    json={"file_path": file_path, "agent_id": agent_id}
                )
                
                if response.status_code == 409:  # Conflict - file is locked
                    error_detail = response.json().get("detail", {})
                    blocked_files.append({
                        "file": file_path,
                        "locked_by": error_detail.get("locked_by", "unknown"),
                        "expires_in": error_detail.get("expires_in_seconds", 0)
                    })
                elif response.status_code != 200:
                    # Other error - log but don't block
                    print(f"Warning: File lock check failed for {file_path}: {response.status_code}", file=sys.stderr)
                    
            except Exception as e:
                print(f"Warning: Could not check file lock for {file_path}: {e}", file=sys.stderr)
        
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
        elif "edits" in tool_input:  # MultiEdit tool
            file_paths = [tool_input.get("file_path", "")]

        result = handle_pre_edit(file_paths, tool_name, session_id)

        if not result.get("proceed", True):
            # Block the edit - output reason to stderr and exit with code 2
            reason = result.get("message", "File locked by another agent")
            print(reason, file=sys.stderr)
            
            # Optional: structured JSON output for Claude
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                    "blocked_files": result.get("blocked_files", [])
                }
            }))
            sys.exit(2)  # EXIT CODE 2 TO BLOCK!
        
        # Proceed - output success and exit 0
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        print(f"Error in pre-edit hook: {e}", file=sys.stderr)
        # Default to proceed on error (don't block on failures)
        print(json.dumps({"proceed": True, "error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
