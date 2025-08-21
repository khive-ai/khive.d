from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys

from .parts import PlannerRequest
from .planner_service import PlannerService

__all__ = ("main",)


def fetch_github_issue(issue_num: str) -> dict | None:
    """Fetch GitHub issue data using gh CLI."""
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
            "number,title,body,labels,assignees,state,createdAt,updatedAt,author",
        ]

        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, check=True, shell=False
        )
        return json.loads(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"❌ Error fetching issue #{issue_num}: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing issue data: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Unexpected error fetching issue: {e}", file=sys.stderr)
        return None


def extract_issue_context(issue_data: dict) -> tuple[str, str]:
    """Extract task description and context from GitHub issue data."""
    title = issue_data.get("title", "")
    body = issue_data.get("body", "")
    labels = issue_data.get("labels", [])
    author = issue_data.get("author", {}).get("login", "unknown")

    # Build task description from title
    task_description = f"GitHub Issue #{issue_data['number']}: {title}"

    # Build rich context from issue metadata and body
    context_parts = []

    # Add author info
    context_parts.append(f"Created by: {author}")

    # Add labels as context
    if labels:
        label_names = [label.get("name", "") for label in labels]
        context_parts.append(f"Labels: {', '.join(label_names)}")

    # Add body content (truncated if too long)
    if body:
        # Clean up body - remove excessive whitespace and limit length
        clean_body = " ".join(body.split())
        if len(clean_body) > 1000:
            clean_body = clean_body[:1000] + "... (truncated)"
        context_parts.append(f"Issue description: {clean_body}")

    context = "\n".join(context_parts)

    return task_description, context


async def run_planning(
    task_description: str,
    context: str | None,
    time_budget: float,
    json_output: bool,
    _issue_num: str | None = None,
) -> None:
    """Execute planning and print results.

    Args:
        task_description: Description of task to plan
        context: Additional context for planning
        time_budget: Time budget in seconds
        json_output: Whether to output results as JSON
        _issue_num: GitHub issue number (reserved for future issue tracking integration)
    """
    service = PlannerService()

    try:
        # Build request
        request = PlannerRequest(
            task_description=task_description,
            context=context,
            time_budget_seconds=time_budget,
        )

        # Get plan
        response = await service.handle_request(request)

        # Output results
        if json_output:
            print(json.dumps(response.model_dump(exclude_none=True), indent=2))
        elif response.success:
            # Print summary
            print(f"\n🎯 {response.summary}")
            print(
                f"📊 Complexity: {getattr(response.complexity, 'value', response.complexity)}"
            )
            print(f"👥 Recommended Agents: {response.recommended_agents}")
            print(f"🔗 Session ID: {response.session_id}")
            print(f"✨ Confidence: {response.confidence:.0%}")

            if response.phases:
                print(f"\n📋 Execution Phases ({len(response.phases)}):")
                for i, phase in enumerate(response.phases, 1):
                    print(f"\n{i}. {phase.name.replace('_', ' ').title()}")
                    print(f"   Description: {phase.description}")
                    print(f"   Agents: {len(phase.agents)}")
                    print(
                        f"   Quality Gate: {getattr(phase.quality_gate, 'value', phase.quality_gate)}"
                    )
                    print(
                        f"   Pattern: {getattr(phase.coordination_pattern, 'value', phase.coordination_pattern)}"
                    )
                    if phase.dependencies:
                        print(f"   Dependencies: {', '.join(phase.dependencies)}")

                    # Show agent details
                    if phase.agents:
                        print("   Agent Details:")
                        for agent in phase.agents:
                            print(
                                f"     • {agent.role} ({agent.domain}) - Priority: {agent.priority:.1f}"
                            )
                            print(f"       Reasoning: {agent.reasoning}")
                        if len(phase.agents) > 3:
                            print(f"     ... and {len(phase.agents) - 3} more agents")
        else:
            print(f"❌ Planning failed: {response.summary}")
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
        prog="khive plan",
        description="Get intelligent orchestration plans for complex tasks",
        epilog="Provide a task description and get a detailed execution plan with agent recommendations.",
    )

    # Make task_description optional when using --issue
    parser.add_argument(
        "task_description",
        nargs="?",
        help="Description of the task to plan (optional when using --issue)",
    )

    parser.add_argument(
        "--issue",
        help="GitHub issue number to extract task description and context from",
    )

    parser.add_argument(
        "--context", "-c", help="Additional context about the task or environment"
    )

    parser.add_argument(
        "--time-budget",
        "-t",
        type=float,
        default=45.0,
        help="Maximum seconds to spend on planning (default: 45)",
    )

    parser.add_argument("--json", action="store_true", help="Output raw JSON response")

    args = parser.parse_args()

    # Handle issue-based planning
    if args.issue:
        print(f"🔍 Fetching GitHub issue #{args.issue}...")

        issue_data = fetch_github_issue(args.issue)
        if not issue_data:
            print(f"❌ Failed to fetch issue #{args.issue}")
            sys.exit(1)

        task_description, issue_context = extract_issue_context(issue_data)

        # Combine issue context with user-provided context
        if args.context:
            context = f"{issue_context}\n\nAdditional context: {args.context}"
        else:
            context = issue_context

        print(f"📋 Task: {task_description}")
        print("🎯 Planning orchestration strategy...")

    else:
        # Regular planning with user-provided task description
        if not args.task_description:
            print("❌ Error: task_description is required when not using --issue")
            parser.print_help()
            sys.exit(1)

        task_description = args.task_description
        context = args.context

    # Run the planning
    asyncio.run(run_planning(task_description, context, args.time_budget, args.json))


if __name__ == "__main__":
    main()
