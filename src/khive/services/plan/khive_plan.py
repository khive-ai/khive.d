"""
CLI interface for Multi-Round Consensus Planning System.
Implements ChatGPT's design with no legacy fallbacks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional

from .models import PlannerRequest, PlannerResponse
from .service import ConsensusPlannerV3

# Try to import utilities
try:
    from khive.utils import get_logger

    logger = get_logger("khive.cli.plan")
except ImportError:
    import logging

    # COMPLETELY SUPPRESS ALL LOGS
    logging.getLogger().setLevel(logging.ERROR)
    logging.getLogger("root").setLevel(logging.ERROR)
    logging.getLogger("lionagi").setLevel(logging.ERROR)
    logging.getLogger("backoff").setLevel(logging.ERROR)
    # Disable all handlers
    logging.getLogger().handlers = []
    logging.getLogger("root").handlers = []
    logger = logging.getLogger("khive.cli.plan")


def fetch_github_issue(issue_num: str) -> Optional[Dict[str, Any]]:
    """
    Fetch GitHub issue data using gh CLI.

    Args:
        issue_num: Issue number to fetch

    Returns:
        Issue data as dictionary or None if failed
    """
    try:
        gh_path = shutil.which("gh")
        if not gh_path:
            print("❌ Error: GitHub CLI (gh) not found in PATH", file=sys.stderr)
            return None

        cmd = [
            gh_path,
            "issue",
            "view",
            issue_num,
            "--json",
            "title,body,labels,assignees,state",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"❌ Error fetching issue #{issue_num}: {result.stderr}",
                file=sys.stderr,
            )
            return None

        return json.loads(result.stdout)

    except Exception as e:
        print(f"❌ Error fetching GitHub issue: {e}", file=sys.stderr)
        return None


def format_issue_context(issue_data: Dict[str, Any]) -> str:
    """Format GitHub issue data into context string."""
    context_parts = [f"GitHub Issue: {issue_data.get('title', 'Untitled')}"]

    if issue_data.get("body"):
        context_parts.append(f"Description: {issue_data['body']}")

    if issue_data.get("labels"):
        labels = [label["name"] for label in issue_data["labels"]]
        context_parts.append(f"Labels: {', '.join(labels)}")

    return "\n".join(context_parts)


async def run_planning(
    task_description: str,
    context: Optional[str] = None,
    time_budget: float = 90.0,
    output_json: bool = False,
) -> PlannerResponse:
    """Execute multi-round consensus planning."""

    # Create planner instance
    planner = ConsensusPlannerV3()

    # Create request
    request = PlannerRequest(
        task_description=task_description,
        context=context,
        time_budget_seconds=time_budget,
    )

    # Execute planning
    response = await planner.plan(request)

    return response


def print_plan_summary(response: PlannerResponse, output_json: bool = False) -> None:
    """Print planning results in human-readable or JSON format."""

    if output_json:
        # JSON output for programmatic use
        output = {
            "success": response.success,
            "summary": response.summary,
            "complexity": response.complexity,
            "recommended_agents": response.recommended_agents,
            "phases": [phase.model_dump() for phase in response.phases],
            "coordination_id": response.coordination_id,
            "confidence": response.confidence,
            "spawn_commands": response.spawn_commands,
        }

        if response.error:
            output["error"] = response.error

        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        if not response.success:
            print(f"❌ Planning failed: {response.error}")
            return

        print(response.summary)

        if response.spawn_commands:
            print(f"\n🚀 Agent Spawn Commands:")
            for cmd in response.spawn_commands:
                print(f"   {cmd}")

        print(f"\n📊 Coordination: {response.coordination_id}")
        print(f"🎯 Confidence: {response.confidence:.1%}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for khive plan command."""
    parser = argparse.ArgumentParser(
        description="Multi-Round Consensus Planning System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  khive plan "Build a REST API"
  khive plan "Implement user auth" --issue 123
  khive plan "Add caching layer" --time-budget 120 --json
        """,
    )

    parser.add_argument(
        "task_description", nargs="?", help="Description of the task to plan"
    )

    parser.add_argument(
        "--issue", type=str, help="GitHub issue number to use as context"
    )

    parser.add_argument("--context", type=str, help="Additional context for planning")

    parser.add_argument(
        "--time-budget",
        type=float,
        default=90.0,
        help="Time budget in seconds (default: 90.0)",
    )

    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate required arguments
    if not args.task_description and not args.issue:
        print(
            "❌ Error: Either task description or --issue must be provided",
            file=sys.stderr,
        )
        parser.print_help()
        sys.exit(1)

    # Build context from GitHub issue if provided
    context = args.context
    task_description = args.task_description

    if args.issue:
        issue_data = fetch_github_issue(args.issue)
        if issue_data:
            issue_context = format_issue_context(issue_data)
            if context:
                context = f"{context}\n\n{issue_context}"
            else:
                context = issue_context

            # Use issue title as task description if none provided
            if not task_description:
                task_description = issue_data.get(
                    "title", f"Work on issue #{args.issue}"
                )
        else:
            print(
                f"⚠️  Could not fetch issue #{args.issue}, proceeding without issue context"
            )

    if not task_description:
        print("❌ Error: Could not determine task description", file=sys.stderr)
        sys.exit(1)

    try:
        # Run planning
        response = asyncio.run(
            run_planning(
                task_description=task_description,
                context=context,
                time_budget=args.time_budget,
                output_json=args.json,
            )
        )

        # Print results
        print_plan_summary(response, args.json)

        # Exit with appropriate code
        sys.exit(0 if response.success else 1)

    except KeyboardInterrupt:
        print("\n⏸️  Planning interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"💥 Unexpected error: {e}", file=sys.stderr)
        if not args.json:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
