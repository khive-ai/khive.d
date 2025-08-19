# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Simplified CLI for Khive Session Management Service.

Examples:
    # Initialize a session
    khive session init
    khive session init --issue 123 --resume

    # End a session (diary writing)
    khive session end

    # Check session status
    khive session status

    # JSON output for scripts
    khive session init --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .parts import SessionRequest
from .session_service import SessionService


async def run_session_command(
    action: str,
    issue: int | None,
    resume: bool,
    depth: int,
    continue_session: bool,
    json_output: bool,
) -> None:
    """Execute session command and print results."""
    service = SessionService()

    try:
        # Build request
        request = SessionRequest(
            action=action,
            issue=issue,
            resume=resume,
            depth=depth,
            continue_session=continue_session,
        )

        # Execute command
        response = await service.handle_request(request)

        # Output results
        if json_output:
            print(json.dumps(response.model_dump(exclude_none=True), indent=2))
        elif response.success:
            if action == "init":
                if response.session_output:
                    print(response.session_output)
                else:
                    print(f"✅ {response.summary}")

                    if response.pending_tasks:
                        print(f"\n📋 Pending Tasks ({len(response.pending_tasks)}):")
                        for task in response.pending_tasks[:5]:  # Show first 5
                            priority = task.get("priority", "low")
                            description = task.get("description", "Unknown task")
                            print(f"  • [{priority.upper()}] {description}")
                        if len(response.pending_tasks) > 5:
                            print(
                                f"  ... and {len(response.pending_tasks) - 5} more tasks"
                            )

                    if response.git_status:
                        git = response.git_status
                        print("\n📊 Git Status:")
                        print(f"  Branch: {git.get('branch', 'unknown')}")
                        print(f"  Modified files: {git.get('modified_files', 0)}")
                        if git.get("recent_commits"):
                            print(f"  Recent commits: {len(git['recent_commits'])}")

                    if response.unprocessed_summaries > 0:
                        print(
                            f"\n📝 Unprocessed Summaries: {response.unprocessed_summaries}"
                        )

            elif action == "end":
                print(f"✅ {response.summary}")
                print(
                    "\n📔 Diary processing completed. Check .khive/notes/diaries/ for results."
                )

            elif action == "status":
                print(f"📊 {response.summary}")

                if response.pending_tasks:
                    print(f"\n📋 Pending Tasks ({len(response.pending_tasks)}):")
                    for task in response.pending_tasks[:3]:  # Show first 3
                        priority = task.get("priority", "low")
                        description = task.get("description", "Unknown task")
                        print(f"  • [{priority.upper()}] {description}")
                    if len(response.pending_tasks) > 3:
                        print(f"  ... and {len(response.pending_tasks) - 3} more tasks")

                if response.git_status:
                    git = response.git_status
                    print("\n📊 Git Status:")
                    print(f"  Branch: {git.get('branch', 'unknown')}")
                    print(f"  Modified files: {git.get('modified_files', 0)}")

                if response.unprocessed_summaries > 0:
                    print(
                        f"\n📝 Unprocessed Summaries: {response.unprocessed_summaries}"
                    )
                    print(
                        "  Run 'khive session end' to process them into diary entries."
                    )

        else:
            print(f"❌ {response.summary}")
            if response.error:
                print(f"Error: {response.error}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await service.close()


def main():
    parser = argparse.ArgumentParser(
        prog="khive session",
        description="Manage orchestrator sessions with intelligent context loading",
        epilog="Initialize sessions, end with diary writing, or check status.",
    )

    subparsers = parser.add_subparsers(dest="action", help="Session action")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new session")
    init_parser.add_argument(
        "--issue", type=int, help="GitHub issue number to focus on"
    )
    init_parser.add_argument(
        "--resume", action="store_true", help="Resume from previous session"
    )
    init_parser.add_argument(
        "--depth", type=int, default=7, help="Memory depth for context (default: 7)"
    )
    init_parser.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue current session",
    )
    init_parser.add_argument(
        "--json", action="store_true", help="Output raw JSON response"
    )

    # End command
    end_parser = subparsers.add_parser("end", help="End session and process diaries")
    end_parser.add_argument(
        "--json", action="store_true", help="Output raw JSON response"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Check session status")
    status_parser.add_argument(
        "--json", action="store_true", help="Output raw JSON response"
    )

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    # Extract common arguments
    issue = getattr(args, "issue", None)
    resume = getattr(args, "resume", False)
    depth = getattr(args, "depth", 7)
    continue_session = getattr(args, "continue_session", False)
    json_output = getattr(args, "json", False)

    # Run the session command
    asyncio.run(
        run_session_command(
            args.action, issue, resume, depth, continue_session, json_output
        )
    )


if __name__ == "__main__":
    main()
