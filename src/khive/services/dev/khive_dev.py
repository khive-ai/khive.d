# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Simplified CLI for Khive Development Service.

Examples:
    # Natural language requests
    khive dev "fix all code issues"
    khive dev "run tests and show me what's wrong"
    khive dev "set up a new Python project"

    # Quick operations
    khive dev --check                 # Run full project check
    khive dev --fix                   # Fix all auto-fixable issues
    khive dev --setup python          # Set up Python project
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from khive.services.dev.dev_service import DevServiceGroup
from khive.services.dev.parts import DevMode, DevRequest, StackType


async def run_dev_operation(args) -> None:
    """Execute development operation and print results."""
    service = DevServiceGroup()

    try:
        # Determine the request based on arguments
        if args.check:
            request = DevRequest(
                intent="run comprehensive project check",
                mode=DevMode.FULL_CHECK,
                fix_issues=False,
                project_root=args.project,
                detailed_analysis=args.detailed,
            )
        elif args.fix:
            request = DevRequest(
                intent="fix all code quality issues",
                mode=DevMode.QUICK_FIX,
                fix_issues=True,
                project_root=args.project,
            )
        elif args.setup:
            request = DevRequest(
                intent=f"set up new {args.setup} project",
                mode=DevMode.SETUP,
                stack=_parse_stack(args.setup),
                project_root=args.project,
            )
        else:
            # Natural language request
            request = DevRequest(
                intent=args.request,
                context=args.context,
                fix_issues=not args.no_fix,
                project_root=args.project,
                detailed_analysis=args.detailed,
                time_budget=args.timeout,
            )

        # Execute request
        response = await service.handle_request(request)

        # Output results
        if response.success:
            # Print summary with appropriate emoji
            emoji = _get_status_emoji(response)
            print(f"\n{emoji} {response.summary}\n")

            # Print actions taken
            if response.actions_taken and not args.quiet:
                print("📋 Actions taken:")
                for action in response.actions_taken:
                    print(f"   {action}")
                print()

            # Print issues if found
            if response.issues_found:
                fixed = sum(1 for i in response.issues_found if i.fix_applied)
                total = len(response.issues_found)

                print(f"🔍 Issues: {fixed}/{total} fixed")

                if not args.quiet:
                    # Group by severity
                    by_severity = {}
                    for issue in response.issues_found:
                        sev = issue.severity.value
                        if sev not in by_severity:
                            by_severity[sev] = []
                        by_severity[sev].append(issue)

                    # Print by severity
                    for severity in ["critical", "high", "medium", "low", "info"]:
                        if severity in by_severity:
                            print(
                                f"\n   {_severity_emoji(severity)} {severity.upper()}:"
                            )
                            for issue in by_severity[severity]:
                                status = "✓" if issue.fix_applied else "○"
                                print(f"      {status} {issue.summary}")
                                if issue.recommendation and not issue.fix_applied:
                                    print(f"         → {issue.recommendation}")

            # Print test results
            if response.test_results:
                print("\n🧪 Test Results:")
                for tr in response.test_results:
                    status = "✅" if tr.failed == 0 else "❌"
                    print(
                        f"   {status} {tr.stack}: {tr.passed}/{tr.total_tests} passed",
                        end="",
                    )
                    if tr.coverage:
                        print(f" (coverage: {tr.coverage:.1f}%)")
                    else:
                        print()

                    if tr.failed > 0 and tr.failures and not args.quiet:
                        print(f"      Failed: {', '.join(tr.failures[:3])}")
                        if len(tr.failures) > 3:
                            print(f"      ... and {len(tr.failures) - 3} more")

            # Print project health
            if response.project_health:
                health = response.project_health
                health_emoji = _health_emoji(health.status)
                print(
                    f"\n{health_emoji} Project Health: {health.score:.0f}/100 ({health.status})"
                )

                if not args.quiet:
                    if health.strengths:
                        print("   💪 Strengths:")
                        for strength in health.strengths:
                            print(f"      • {strength}")

                    if health.concerns:
                        print("   ⚠️  Concerns:")
                        for concern in health.concerns:
                            print(f"      • {concern}")

            # Print insights
            if response.insights and args.detailed:
                print("\n💡 Insights:")
                for insight in response.insights[:5]:
                    print(f"   • {insight.summary}")
                    if insight.impact:
                        print(f"     Impact: {insight.impact}")

            # Print next steps
            if response.next_steps:
                print("\n📌 Next steps:")
                for i, step in enumerate(response.next_steps, 1):
                    print(f"   {i}. {step}")

            # JSON output for scripts
            if args.json:
                print(
                    "\n" + json.dumps(response.model_dump(exclude_none=True), indent=2)
                )

        else:
            print(f"❌ {response.summary}")
            if response.error:
                print(f"Error: {response.error}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.json:
            print(json.dumps({"error": str(e), "success": False}))
        sys.exit(1)
    finally:
        await service.close()


def _parse_stack(stack_str: str) -> StackType:
    """Parse stack type from string."""
    stack_map = {
        "python": StackType.PYTHON,
        "py": StackType.PYTHON,
        "rust": StackType.RUST,
        "rs": StackType.RUST,
        "node": StackType.NODE,
        "nodejs": StackType.NODE,
        "npm": StackType.NODE,
        "typescript": StackType.NODE,
        "ts": StackType.NODE,
        "javascript": StackType.NODE,
        "js": StackType.NODE,
        "deno": StackType.DENO,
    }
    return stack_map.get(stack_str.lower(), StackType.AUTO)


def _get_status_emoji(response) -> str:
    """Get appropriate emoji for response status."""
    if response.mode_used == DevMode.SETUP:
        return "🚀"
    elif response.mode_used == DevMode.QUICK_FIX:
        return "🔧" if response.issues_fixed > 0 else "✅"
    elif response.mode_used == DevMode.DIAGNOSTIC:
        return "🔬"
    elif response.mode_used == DevMode.MAINTENANCE:
        return "🧹"
    else:
        return "✅" if response.success else "❌"


def _severity_emoji(severity: str) -> str:
    """Get emoji for issue severity."""
    return {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
        "info": "ℹ️",
    }.get(severity, "•")


def _health_emoji(status: str) -> str:
    """Get emoji for health status."""
    return {
        "healthy": "💚",
        "needs_attention": "💛",
        "unhealthy": "❤️",
    }.get(status, "🩺")


def main():
    parser = argparse.ArgumentParser(
        prog="khive dev",
        description="Intelligent development assistance",
        epilog="Just describe what you want to do - the service handles the complexity.",
    )

    # Main argument
    parser.add_argument(
        "request",
        nargs="?",
        help="What you want to do in natural language",
    )

    # Quick operations
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run comprehensive project check",
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix all auto-fixable issues",
    )

    parser.add_argument(
        "--setup",
        metavar="TYPE",
        help="Set up new project (python/rust/node/typescript)",
    )

    # Options
    parser.add_argument(
        "--context",
        "-c",
        help="Additional context about what you're doing",
    )

    parser.add_argument(
        "--project",
        "-p",
        type=Path,
        help="Project directory (auto-detected if not specified)",
    )

    parser.add_argument(
        "--no-fix",
        action="store_true",
        help="Don't automatically fix issues, just report them",
    )

    parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        help="Include detailed analysis and insights",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Minimal output - just summary and next steps",
    )

    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=30.0,
        help="Maximum seconds to spend (default: 30)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.request, args.check, args.fix, args.setup]):
        parser.error("No operation specified. Use --help for usage.")

    if sum([bool(args.request), args.check, args.fix, bool(args.setup)]) > 1:
        parser.error("Specify only one operation at a time.")

    # Run the operation
    asyncio.run(run_dev_operation(args))


if __name__ == "__main__":
    main()
