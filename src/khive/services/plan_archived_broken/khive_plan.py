"""
CLI interface for khive planning system.

Provides the command-line interface for generating orchestration plans.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from typing import Optional, Dict, Any

from .models import PlannerRequest, PlannerResponse
from .service import PlannerService

# Try to import utilities
try:
    from khive.utils import get_logger
    logger = get_logger("khive.cli.plan")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
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
            "number,title,body,labels,author,assignees,milestone",
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, shell=False
        )
        return json.loads(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"❌ Error fetching issue #{issue_num}: {e.stderr}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("❌ Error: GitHub CLI (gh) command not found.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Unexpected error fetching issue: {e}", file=sys.stderr)
        return None


def extract_issue_context(issue_data: Dict[str, Any]) -> tuple[str, str]:
    """
    Extract task description and context from GitHub issue data.
    
    Args:
        issue_data: Issue data from GitHub
        
    Returns:
        Tuple of (task_description, context)
    """
    title = issue_data.get("title", "")
    body = issue_data.get("body", "")
    labels = issue_data.get("labels", [])
    author = issue_data.get("author", {}).get("login", "unknown")
    assignees = issue_data.get("assignees", [])
    milestone = issue_data.get("milestone", {}).get("title", "")

    task_description = f"GitHub Issue #{issue_data['number']}: {title}"

    context_parts = []
    context_parts.append(f"Created by: {author}")
    
    if assignees:
        assignee_names = [a.get("login", "") for a in assignees]
        context_parts.append(f"Assigned to: {', '.join(assignee_names)}")
    
    if milestone:
        context_parts.append(f"Milestone: {milestone}")

    if labels:
        label_names = [label.get("name", "") for label in labels]
        context_parts.append(f"Labels: {', '.join(label_names)}")

    if body:
        # Clean and truncate body if too long
        clean_body = " ".join(body.split())
        if len(clean_body) > 1000:
            clean_body = clean_body[:1000] + "..."
        context_parts.append(f"Issue description: {clean_body}")

    context = "\n".join(context_parts)

    return task_description, context


async def run_planning(
    task_description: str,
    context: Optional[str],
    time_budget: float,
    json_output: bool,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    evaluators: int = 5
) -> None:
    """
    Execute planning and print results.
    
    Args:
        task_description: Description of the task to plan
        context: Additional context
        time_budget: Maximum time for planning
        json_output: Whether to output raw JSON
        provider: LLM provider override
        model: Model name override
        evaluators: Number of parallel evaluators
    """
    # Initialize the planner service
    service = PlannerService(
        provider=provider,
        model=model,
        parallel_evaluators=evaluators
    )

    try:
        # Build request
        request = PlannerRequest(
            task_description=task_description,
            context=context,
            time_budget_seconds=time_budget,
        )

        print("🚀 Initiating Adaptive Orchestration Planning...")
        print(f"   Provider: {service.provider}")
        print(f"   Model: {service.model_name}")
        print(f"   Evaluators: {service.parallel_evaluators}")
        print()
        
        # Get plan
        response = await service.plan(request)

        # Output results
        if json_output:
            # Output the structured data
            output_dict = response.model_dump(exclude_none=True)
            print(json.dumps(output_dict, indent=2))
        else:
            # The summary field contains the human-readable output
            print(response.summary)
        
        # Show spawn commands if present
        if response.spawn_commands and not json_output:
            print("\n🚀 Spawn Commands:")
            print("-" * 40)
            for cmd in response.spawn_commands:
                print(cmd)
        
        if not response.success:
            sys.exit(1)

    except Exception as e:
        print(f"❌ Planning failed: {e}", file=sys.stderr)
        logger.error(f"Planning error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await service.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="khive plan",
        description="Generate adaptive orchestration plans using lionagi",
        epilog="Provide a task description to generate a detailed execution plan with agent recommendations.",
    )

    parser.add_argument(
        "task_description",
        nargs="?",
        help="Description of the task to plan (optional when using --issue)",
    )

    parser.add_argument(
        "--issue",
        help="GitHub issue number to extract task from",
    )

    parser.add_argument(
        "--context", "-c",
        help="Additional context about the task"
    )

    parser.add_argument(
        "--time-budget", "-t",
        type=float,
        default=45.0,
        help="Maximum seconds for planning (default: 45)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response"
    )
    
    parser.add_argument(
        "--provider", "-p",
        help="LLM provider (e.g., nvidia_nim, openai)",
        default=None
    )
    
    parser.add_argument(
        "--model", "-m",
        help="Model name (e.g., gpt-4o-mini, nvidia/nemotron)",
        default=None
    )
    
    parser.add_argument(
        "--evaluators", "-e",
        type=int,
        default=5,
        help="Number of parallel evaluators for consensus (3-10, default: 5)"
    )
    
    # Hidden/deprecated arguments
    parser.add_argument(
        "--json-format",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    # Handle issue-based planning
    if args.issue:
        print(f"🔍 Fetching GitHub issue #{args.issue}...")

        issue_data = fetch_github_issue(args.issue)
        if not issue_data:
            sys.exit(1)

        task_description, issue_context = extract_issue_context(issue_data)

        if args.context:
            context = f"{issue_context}\n\nAdditional context: {args.context}"
        else:
            context = issue_context

        print(f"📋 Task: {task_description}")
        print()

    else:
        # Regular planning
        if not args.task_description:
            print("❌ Error: task_description is required when not using --issue")
            parser.print_help()
            sys.exit(1)

        task_description = args.task_description
        context = args.context

    # Validate evaluators
    evaluators = max(3, min(10, args.evaluators))
    if evaluators != args.evaluators:
        print(f"⚠️  Evaluators adjusted to {evaluators} (valid range: 3-10)")

    # Run the planning
    try:
        asyncio.run(
            run_planning(
                task_description,
                context,
                args.time_budget,
                args.json or args.json_format,
                provider=args.provider,
                model=args.model,
                evaluators=evaluators
            )
        )
    except KeyboardInterrupt:
        print("\n⚠️  Planning interrupted by user")
        sys.exit(1)
    except RuntimeError as e:
        # Handle common asyncio runtime errors
        if "Event loop is closed" not in str(e):
            raise


if __name__ == "__main__":
    main()