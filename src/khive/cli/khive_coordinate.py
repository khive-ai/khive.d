"""
Khive Coordination CLI - Explicit coordination commands for agents.

This provides the explicit coordination protocol that agents must follow
instead of relying on hooks that don't integrate properly with Claude Code.

Examples:
    # Before starting work
    uv run khive coordinate pre-task --description "Implement auth system" --agent-id researcher_security
    
    # During work
    uv run khive coordinate post-edit --file "/path/to/file.py" --agent-id researcher_security
    
    # After completing work  
    uv run khive coordinate post-task --agent-id researcher_security
"""

import argparse
import asyncio
import json
import sys
import time
from typing import Optional

from khive.daemon.client import get_daemon_client


def pre_task(agent_id: str, description: str, coordination_id: Optional[str] = None) -> dict:
    """Initialize task coordination - BEFORE starting work."""
    try:
        client = get_daemon_client()
        if not client.is_running():
            return {
                "success": False,
                "error": "Coordination daemon not running. Start with: uv run khive daemon start"
            }
        
        # Register agent work with coordination system
        response = client.coordinate_start(
            task_id=coordination_id or f"task_{agent_id}_{int(time.time())}",
            task_description=description,
            agent_id=agent_id
        )
        
        # Check for duplicate work
        if response.get("status") == "duplicate":
            print(f"⚠️  WARNING: Similar work already in progress: {response.get('existing_task')}")
            return {
                "success": True,
                "warning": "Duplicate work detected",
                "existing_task": response.get("existing_task"),
                "coordination_active": True
            }
        
        print(f"✅ Task coordination initialized for {agent_id}")
        return {
            "success": True,
            "message": f"Coordination active for {agent_id}",
            "coordination_active": True,
            "task_id": response.get("task_id", f"task_{agent_id}_{int(time.time())}")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "coordination_active": False
        }


def post_edit(agent_id: str, file_path: str, operation: str = "edit") -> dict:
    """Report file operation - DURING work after editing files."""
    try:
        client = get_daemon_client()
        if not client.is_running():
            return {
                "success": False,
                "error": "Coordination daemon not running"
            }
        
        # Release file lock after edit
        response = client.client.post(
            f"{client.base_url}/api/coordinate/file-unregister",
            json={"file_path": file_path, "agent_id": agent_id}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"📝 File operation completed: {file_path}")
            return {
                "success": True,
                "message": f"File operation registered: {operation}",
                "file": file_path,
                "lock_released": True
            }
        else:
            return {
                "success": False,
                "error": f"Failed to release file lock: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def check_conflicts(agent_id: str, file_path: str) -> dict:
    """Check for file conflicts before editing - DURING work."""
    try:
        client = get_daemon_client()
        if not client.is_running():
            return {
                "success": False,
                "error": "Coordination daemon not running"
            }
        
        # Request file lock before edit
        response = client.client.post(
            f"{client.base_url}/api/coordinate/file-register",
            json={"file_path": file_path, "agent_id": agent_id}
        )
        
        if response.status_code == 409:  # Conflict
            conflict_info = response.json().get("detail", {})
            print(f"🚫 CONFLICT: File {file_path} is locked by {conflict_info.get('locked_by', 'unknown')}")
            return {
                "success": False,
                "conflict": True,
                "locked_by": conflict_info.get("locked_by"),
                "expires_in": conflict_info.get("expires_in_seconds"),
                "message": f"File locked by {conflict_info.get('locked_by')} - wait or choose different file"
            }
        elif response.status_code == 200:
            print(f"🔓 File lock acquired: {file_path}")
            return {
                "success": True,
                "conflict": False,
                "lock_acquired": True,
                "message": f"Safe to edit {file_path}"
            }
        else:
            return {
                "success": False,
                "error": f"Lock check failed: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def post_task(agent_id: str, summary: str = "") -> dict:
    """Complete task coordination - AFTER finishing work."""
    try:
        client = get_daemon_client()
        if not client.is_running():
            return {
                "success": False,
                "error": "Coordination daemon not running"
            }
        
        # Get coordination status
        status_response = client.client.get(f"{client.base_url}/api/coordinate/status")
        if status_response.status_code != 200:
            return {
                "success": False,
                "error": "Failed to get coordination status"
            }
        
        status = status_response.json()
        
        # Complete task coordination
        task_id = f"task_{agent_id}"
        complete_response = client.coordinate_complete(
            task_id=task_id,
            agent_id=agent_id,
            output=summary or f"Task completed by {agent_id}"
        )
        
        print(f"✅ Task coordination completed for {agent_id}")
        return {
            "success": True,
            "message": f"Task completed: {agent_id}",
            "coordination_stats": {
                "active_agents": status.get("active_agents", 0),
                "conflicts_prevented": status.get("metrics", {}).get("conflicts_prevented", 0),
                "duplicates_avoided": status.get("metrics", {}).get("duplicates_avoided", 0)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_status() -> dict:
    """Get current coordination status."""
    try:
        client = get_daemon_client()
        if not client.is_running():
            return {
                "success": False,
                "error": "Coordination daemon not running"
            }
        
        response = client.client.get(f"{client.base_url}/api/coordinate/status")
        if response.status_code == 200:
            return {
                "success": True,
                "status": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"Status check failed: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Khive coordination commands for agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Before starting work
    uv run khive coordinate pre-task --description "Implement auth" --agent-id researcher_security
    
    # Check for conflicts before editing
    uv run khive coordinate check-conflicts --file "/path/to/file.py" --agent-id researcher_security
    
    # After editing files
    uv run khive coordinate post-edit --file "/path/to/file.py" --agent-id researcher_security
    
    # After completing work
    uv run khive coordinate post-task --agent-id researcher_security --summary "Auth implementation completed"
    
    # Check coordination status
    uv run khive coordinate status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Coordination commands')
    
    # pre-task command
    pre_parser = subparsers.add_parser('pre-task', help='Initialize task coordination')
    pre_parser.add_argument('--description', required=True, help='Task description')
    pre_parser.add_argument('--agent-id', required=True, help='Agent identifier')
    pre_parser.add_argument('--coordination-id', help='Coordination session ID')
    
    # check-conflicts command
    conflicts_parser = subparsers.add_parser('check-conflicts', help='Check for file conflicts')
    conflicts_parser.add_argument('--file', required=True, help='File path to check')
    conflicts_parser.add_argument('--agent-id', required=True, help='Agent identifier')
    
    # post-edit command
    edit_parser = subparsers.add_parser('post-edit', help='Report file operation')
    edit_parser.add_argument('--file', required=True, help='File that was edited')
    edit_parser.add_argument('--agent-id', required=True, help='Agent identifier')
    edit_parser.add_argument('--operation', default='edit', help='Type of operation')
    
    # post-task command
    post_parser = subparsers.add_parser('post-task', help='Complete task coordination')
    post_parser.add_argument('--agent-id', required=True, help='Agent identifier')
    post_parser.add_argument('--summary', help='Task completion summary')
    
    # status command
    subparsers.add_parser('status', help='Get coordination status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute the appropriate command
    if args.command == 'pre-task':
        result = pre_task(args.agent_id, args.description, args.coordination_id)
    elif args.command == 'check-conflicts':
        result = check_conflicts(args.agent_id, args.file)
    elif args.command == 'post-edit':
        result = post_edit(args.agent_id, args.file, args.operation)
    elif args.command == 'post-task':
        result = post_task(args.agent_id, args.summary or "")
    elif args.command == 'status':
        result = get_status()
    else:
        print(f"Unknown command: {args.command}")
        return
    
    # Output result as JSON
    print(json.dumps(result, indent=2))
    
    # Exit with error code if operation failed
    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()