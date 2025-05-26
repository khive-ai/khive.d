# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP server for Khive Development Service.

Provides intelligent development capabilities to agents without
requiring them to understand specific CLI commands.
"""

from fastmcp import FastMCP

from khive.services.dev.dev_service import DevServiceGroup
from khive.services.dev.parts import DevMode, DevRequest, StackType

# Agent-friendly description that emphasizes enhancement
instruction = """
Khive Dev enhances your development capabilities with intelligent automation.

This service understands what you want to achieve and handles the complexity:
- Automatically sets up new projects with the right tools
- Fixes code quality issues without manual intervention
- Runs comprehensive tests and provides actionable insights
- Diagnoses problems and suggests solutions

You describe your intent, the service figures out the implementation.
No need to remember specific commands or tools.
"""

mcp = FastMCP(
    name="khive_dev",
    instructions=instruction,
    tags=["development", "automation", "testing", "quality", "setup"],
)


@mcp.tool(
    name="dev_assist",
    description="Intelligent development assistance - describe what you want to achieve",
    tags=["development", "automation", "intelligent"],
)
async def dev_assist(
    intent: str,
    context: str | None = None,
    fix_issues: bool = True,
    project_path: str | None = None,
):
    """
    Get intelligent development assistance.

    Just describe what you want to achieve - the service figures out how.

    Args:
        intent: What you want to do (e.g., "fix all code issues", "run tests", "set up new Python project")
        context: Additional context about your needs
        fix_issues: Automatically fix issues when possible (default: True)
        project_path: Project directory (auto-detected if not specified)

    Returns:
        Actionable insights and results, not raw command output

    Examples:
        - "Set up a new Python project with testing"
        - "Fix all code quality issues"
        - "Run all tests and tell me what's wrong"
        - "Check if my project is ready for deployment"
        - "Clean up and optimize my codebase"
    """
    service = DevServiceGroup()

    try:
        request = DevRequest(
            intent=intent,
            context=context,
            fix_issues=fix_issues,
            project_root=project_path,
            time_budget=30.0,
        )

        response = await service.handle_request(request)

        if response.success:
            result = {
                "summary": response.summary,
                "actions_taken": response.actions_taken,
                "mode": response.mode_used.value,
            }

            # Add issues if found
            if response.issues_found:
                result["issues"] = [
                    {
                        "type": issue.type.value,
                        "severity": issue.severity.value,
                        "description": issue.summary,
                        "fixed": issue.fix_applied,
                        "recommendation": issue.recommendation,
                    }
                    for issue in response.issues_found[:10]  # Top 10
                ]
                result["issues_fixed"] = response.issues_fixed

            # Add test results if available
            if response.test_results:
                result["tests"] = [
                    {
                        "stack": tr.stack.value,
                        "passed": tr.passed,
                        "failed": tr.failed,
                        "total": tr.total_tests,
                        "coverage": f"{tr.coverage:.1f}%" if tr.coverage else "unknown",
                    }
                    for tr in response.test_results
                ]

            # Add project health
            if response.project_health:
                result["project_health"] = {
                    "score": f"{response.project_health.score:.0f}/100",
                    "status": response.project_health.status,
                    "strengths": response.project_health.strengths,
                    "concerns": response.project_health.concerns,
                }

            # Add actionable next steps
            result["next_steps"] = response.next_steps

            # Add key insights
            if response.insights:
                result["insights"] = [
                    {
                        "category": insight.category,
                        "finding": insight.summary,
                        "impact": insight.impact,
                    }
                    for insight in response.insights[:5]
                ]

            return result
        else:
            return {
                "error": response.error or "Operation failed",
                "summary": response.summary,
            }

    except Exception as e:
        return {
            "error": str(e),
            "summary": "Failed to process development request",
        }
    finally:
        await service.close()


@mcp.tool(
    name="check_project_health",
    description="Get a comprehensive health check of your project",
    tags=["testing", "quality", "diagnostics"],
)
async def check_project_health(
    project_path: str | None = None,
    detailed: bool = False,
):
    """
    Run a comprehensive project health check.

    This combines code quality checks, test execution, and analysis
    to give you a complete picture of your project's state.

    Args:
        project_path: Project directory (auto-detected if not specified)
        detailed: Include detailed diagnostic analysis

    Returns:
        Overall health score, issues found, test results, and recommendations
    """
    service = DevServiceGroup()

    try:
        mode = DevMode.DIAGNOSTIC if detailed else DevMode.FULL_CHECK

        request = DevRequest(
            intent="check everything and tell me what needs attention",
            mode=mode,
            fix_issues=False,  # Just check, don't modify
            project_root=project_path,
            detailed_analysis=detailed,
            time_budget=60.0,  # More time for comprehensive check
        )

        response = await service.handle_request(request)

        result = {
            "project_path": project_path or "auto-detected",
            "success": response.success,
            "summary": response.summary,
        }

        # Always include health score
        if response.project_health:
            result["health"] = {
                "score": f"{response.project_health.score:.0f}/100",
                "status": response.project_health.status,
                "grade": _score_to_grade(response.project_health.score),
            }

            if response.project_health.strengths:
                result["strengths"] = response.project_health.strengths

            if response.project_health.concerns:
                result["concerns"] = response.project_health.concerns

        # Summarize issues by severity
        if response.issues_found:
            issue_summary = {}
            for issue in response.issues_found:
                severity = issue.severity.value
                issue_summary[severity] = issue_summary.get(severity, 0) + 1

            result["issue_summary"] = issue_summary

            # Include critical issues
            critical = [
                i for i in response.issues_found if i.severity.value == "critical"
            ]
            if critical:
                result["critical_issues"] = [
                    {
                        "type": i.type.value,
                        "description": i.summary,
                        "recommendation": i.recommendation,
                    }
                    for i in critical
                ]

        # Test summary
        if response.test_results:
            total_tests = sum(tr.total_tests for tr in response.test_results)
            total_passed = sum(tr.passed for tr in response.test_results)

            result["test_summary"] = {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "pass_rate": f"{(total_passed / total_tests * 100):.1f}%"
                if total_tests > 0
                else "N/A",
            }

        # Key insights
        if detailed and response.insights:
            result["insights"] = [insight.summary for insight in response.insights[:5]]

        # Always provide actionable next steps
        result["recommended_actions"] = response.next_steps or [
            "No immediate actions required"
        ]

        return result

    except Exception as e:
        return {
            "error": str(e),
            "summary": "Failed to check project health",
        }
    finally:
        await service.close()


@mcp.tool(
    name="quick_fix",
    description="Quickly fix common development issues",
    tags=["automation", "fixes", "quality"],
)
async def quick_fix(
    what: str = "all",
    project_path: str | None = None,
):
    """
    Quickly fix common development issues.

    Args:
        what: What to fix - "all", "formatting", "imports", etc.
        project_path: Project directory (auto-detected if not specified)

    Returns:
        Summary of what was fixed

    Examples:
        - quick_fix("all") - Fix all auto-fixable issues
        - quick_fix("formatting") - Just fix code formatting
        - quick_fix("imports") - Fix import ordering
    """
    service = DevServiceGroup()

    try:
        # Build intent based on what to fix
        intent_map = {
            "all": "fix all code quality issues",
            "formatting": "fix code formatting",
            "format": "fix code formatting",
            "imports": "fix import ordering",
            "style": "fix code style issues",
        }

        intent = intent_map.get(what.lower(), f"fix {what}")

        request = DevRequest(
            intent=intent,
            mode=DevMode.QUICK_FIX,
            fix_issues=True,
            project_root=project_path,
            time_budget=20.0,
        )

        response = await service.handle_request(request)

        if response.success:
            result = {
                "summary": response.summary,
                "fixed": response.issues_fixed,
                "actions": response.actions_taken,
            }

            # List what was fixed
            if response.issues_found:
                fixed_items = [
                    issue.summary
                    for issue in response.issues_found
                    if issue.fix_applied
                ]
                if fixed_items:
                    result["fixed_items"] = fixed_items

            # Next steps
            unfixed = len(response.issues_found) - response.issues_fixed
            if unfixed > 0:
                result["remaining_issues"] = unfixed
                result["note"] = "Some issues require manual intervention"

            return result
        else:
            return {
                "error": response.error or "Fix operation failed",
                "summary": response.summary,
            }

    except Exception as e:
        return {
            "error": str(e),
            "summary": "Failed to apply fixes",
        }
    finally:
        await service.close()


@mcp.tool(
    name="setup_project",
    description="Set up a new project with best practices",
    tags=["setup", "initialization", "bootstrap"],
)
async def setup_project(
    project_type: str,
    project_path: str | None = None,
    extras: list[str] | None = None,
):
    """
    Set up a new project with everything configured.

    Args:
        project_type: Type of project - "python", "rust", "node", "typescript"
        project_path: Where to create project (defaults to current directory)
        extras: Additional features to set up (e.g., ["testing", "ci", "docker"])

    Returns:
        Summary of what was set up

    Examples:
        - setup_project("python", extras=["testing", "ci"])
        - setup_project("rust", project_path="./my-rust-app")
        - setup_project("typescript", extras=["react", "testing"])
    """
    service = DevServiceGroup()

    try:
        # Map project type to stack
        stack_map = {
            "python": StackType.PYTHON,
            "rust": StackType.RUST,
            "node": StackType.NODE,
            "nodejs": StackType.NODE,
            "typescript": StackType.NODE,
            "ts": StackType.NODE,
            "javascript": StackType.NODE,
            "js": StackType.NODE,
        }

        stack = stack_map.get(project_type.lower(), StackType.AUTO)

        # Build context from extras
        context = None
        if extras:
            context = f"Include support for: {', '.join(extras)}"

        request = DevRequest(
            intent=f"set up a new {project_type} project",
            context=context,
            mode=DevMode.SETUP,
            stack=stack,
            project_root=project_path,
            time_budget=60.0,  # Setup can take time
        )

        response = await service.handle_request(request)

        if response.success:
            result = {
                "summary": response.summary,
                "project_type": project_type,
                "actions": response.actions_taken,
            }

            # Add detected configuration
            if response.insights:
                configs = [
                    i.summary for i in response.insights if i.category == "setup"
                ]
                if configs:
                    result["configured"] = configs

            # Provide clear next steps
            result["next_steps"] = response.next_steps or [
                "Start coding!",
                "Configure your IDE",
                "Review generated configuration files",
            ]

            return result
        else:
            return {
                "error": response.error or "Setup failed",
                "summary": response.summary,
            }

    except Exception as e:
        return {
            "error": str(e),
            "summary": "Failed to set up project",
        }
    finally:
        await service.close()


def _score_to_grade(score: float) -> str:
    """Convert health score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


if __name__ == "__main__":
    mcp.run()
