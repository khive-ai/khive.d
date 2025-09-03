"""
Claude Code post-agent-spawn hook for observability and coordination.

Called after Claude Code spawns Task agents to analyze task completion, share results,
and enable context inheritance for future agents.
"""

import json
import sys
from typing import Any

import anyio

from khive.services.claude.hooks.coordination import get_registry, share_result
from khive.services.claude.hooks.hook_event import (
    HookEvent,
    HookEventContent,
    hook_event_logger,
    shield,
)


def extract_artifacts_from_output(output: str) -> list[str]:
    """Extract artifacts from agent output (file paths, function names, etc.)."""
    artifacts = []

    # Look for file paths
    import re

    file_patterns = [
        r"(?:created|modified|wrote|saved)\s+(?:file\s+)?([/\w\-\.]+\.(?:py|md|json|yaml|yml|txt))",
        r"File:\s*([/\w\-\.]+\.(?:py|md|json|yaml|yml|txt))",
        r"`([/\w\-\.]+\.(?:py|md|json|yaml|yml|txt))`",
    ]

    for pattern in file_patterns:
        matches = re.findall(pattern, output, re.IGNORECASE)
        artifacts.extend(matches)

    # Look for function/class definitions
    code_patterns = [
        r"def\s+(\w+)\s*\(",
        r"class\s+(\w+)[\(:]",
        r"function\s+(\w+)\s*\(",
    ]

    for pattern in code_patterns:
        matches = re.findall(pattern, output)
        artifacts.extend([f"function:{name}" for name in matches])

    # Deduplicate and return
    return list(set(artifacts))


def handle_post_agent_spawn(
    output: str, session_id: str | None = None, task_id: str | None = None
) -> dict[str, Any]:
    """Handle post-agent-spawn hook event with result sharing."""
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

        # Extract artifacts from output (files created, functions defined, etc.)
        artifacts = extract_artifacts_from_output(output)

        # Share the context if task was successful and cleanup agent
        coordination_result = None
        if success and output:
            # Get proper agent ID from session mapping
            registry = get_registry()
            agent_id = (
                registry.get_agent_id_from_session(session_id) if session_id else None
            )
            if not agent_id:
                agent_id = f"session_{session_id[:8] if session_id else 'unknown'}"
            # Share the result for other agents
            artifact_id = share_result(
                agent_id=agent_id,
                content=output[:1000],  # Share first 1000 chars for context
            )

            # Clean up completed agent from active registry
            registry = get_registry()
            if agent_id in registry.active_agents:
                # Release any file locks held by this agent
                agent_work = registry.active_agents[agent_id]
                for file_path in agent_work.files_editing.copy():
                    registry.release_file_lock(agent_id, file_path)

                # Remove agent from active registry
                del registry.active_agents[agent_id]

            coordination_result = {"artifact_id": artifact_id, "agent_cleaned_up": True}

        # Also cleanup failed agents to prevent phantom entries
        elif not success:
            # Get proper agent ID from session mapping
            registry = get_registry()
            agent_id = (
                registry.get_agent_id_from_session(session_id) if session_id else None
            )
            if not agent_id:
                agent_id = f"session_{session_id[:8] if session_id else 'unknown'}"
            if agent_id in registry.active_agents:
                # Release locks and remove failed agent
                agent_work = registry.active_agents[agent_id]
                for file_path in agent_work.files_editing.copy():
                    registry.release_file_lock(agent_id, file_path)
                del registry.active_agents[agent_id]

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
                    "task_id": task_id,
                    "context_shared": coordination_result is not None,
                    "artifacts_count": len(artifacts),
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

        result = {
            "output_length": output_length,
            "success": success,
            "contains_deliverable": contains_deliverable,
            "event_logged": True,
        }

        # Add coordination results
        if coordination_result:
            result["context_shared"] = True
            result["context_key"] = coordination_result.get("context_key")
            result["artifacts_registered"] = coordination_result.get(
                "artifacts_registered", 0
            )

        return result

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
