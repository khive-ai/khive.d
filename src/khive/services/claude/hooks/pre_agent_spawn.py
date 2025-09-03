"""
Claude Code pre-agent-spawn hook for observability and coordination.

Called before Claude Code spawns Task agents to monitor task coordination patterns
and enable intelligent task deduplication and context sharing.
"""

import json
import sys
from typing import Any

import anyio

from khive.services.claude.hooks.coordination import check_duplicate_work
from khive.services.claude.hooks.hook_event import (
    HookEvent,
    HookEventContent,
    hook_event_logger,
    shield,
)


def handle_pre_agent_spawn(
    task_description: str, session_id: str | None = None
) -> dict[str, Any]:
    """Handle pre-agent-spawn hook event with coordination."""
    try:
        # Basic task analysis
        task_length = len(task_description)
        has_complex_keywords = any(
            keyword in task_description.lower()
            for keyword in [
                "analyze",
                "architect",
                "implement",
                "refactor",
                "optimize",
                "research",
            ]
        )
        estimated_complexity = (
            "high" if task_length > 500 else "medium" if task_length > 100 else "low"
        )
        word_count = len(task_description.split())

        # Get proper agent ID - usually this will be fallback since agent spawn is first hook called
        try:
            from khive.services.claude.hooks.coordination import get_registry

            registry = get_registry()
            agent_id = (
                registry.get_agent_id_from_session(session_id) if session_id else None
            )
            if not agent_id:
                agent_id = f"session_{session_id[:8] if session_id else 'unknown'}"
        except Exception:
            agent_id = f"session_{session_id[:8] if session_id else 'unknown'}"

        # Check for duplicate work
        duplicate = check_duplicate_work(agent_id, task_description)

        # Build coordination dict with all required fields
        coordination = {
            "duplicate_detected": duplicate is not None,
            "existing_task": duplicate,
            "should_proceed": duplicate is None,  # Proceed if no duplicate
            "task_id": f"task_{session_id[:8] if session_id else 'new'}",  # Generate task ID
            "relevant_contexts": [],  # Empty for now, could be populated from daemon
        }

        # Prepare coordination insights
        coordination_metadata = {
            "duplicate_detected": coordination["duplicate_detected"],
            "existing_task": coordination.get("existing_task"),
        }

        # Add suggestions to response if duplicate detected
        suggestions_text = ""
        if coordination["duplicate_detected"]:
            suggestions_text = (
                f"Similar task already in progress: {coordination['existing_task']}"
            )

        event = HookEvent(
            content=HookEventContent(
                event_type="pre_agent_spawn",
                tool_name="Task",
                session_id=session_id,
                metadata={
                    "task_description": task_description,
                    "task_length": task_length,
                    "word_count": word_count,
                    "has_complex_keywords": has_complex_keywords,
                    "estimated_complexity": estimated_complexity,
                    "hook_type": "pre_agent_spawn",
                    "coordination": coordination_metadata,
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
            "proceed": coordination["should_proceed"],
            "task_length": task_length,
            "estimated_complexity": estimated_complexity,
            "event_logged": True,
            "task_id": coordination["task_id"],
            "context_available": len(coordination["relevant_contexts"]) > 0,
        }

        # Add coordination message if relevant
        if suggestions_text:
            result["coordination_message"] = suggestions_text

        # Include relevant context summaries
        if coordination["relevant_contexts"]:
            result["inherit_context"] = coordination["relevant_contexts"][
                :2
            ]  # Top 2 contexts

        return result

    except Exception as e:
        return {
            "proceed": True,  # Don't block on error
            "error": str(e),
            "event_logged": False,
        }


def main():
    """Main entry point for pre-agent-spawn hook."""
    try:
        # Read JSON input from stdin
        hook_input = json.load(sys.stdin)

        # Extract session information
        session_id = hook_input.get("session_id", None)

        # Extract task description from tool input
        tool_input = hook_input.get("tool_input", {})
        task_description = tool_input.get("prompt", "") or tool_input.get(
            "description", ""
        )

        result = handle_pre_agent_spawn(task_description, session_id)

        # Always output JSON for Claude Code
        print(json.dumps(result))

        # Exit with 0 for proceed, 2 for block (exit code 2 blocks tool execution)
        if not result.get("proceed", True):
            # Output reason to stderr for Claude to see
            reason = result.get("coordination_message", "Duplicate task detected")
            print(reason, file=sys.stderr)
            sys.exit(2)  # EXIT CODE 2 TO BLOCK!

        sys.exit(0)

    except Exception as e:
        print(f"Error in pre-agent-spawn hook: {e}", file=sys.stderr)
        # Default to proceed on error
        print(json.dumps({"proceed": True, "error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
