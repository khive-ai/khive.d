"""
khive_flow.py - Intelligent flow router for automated issue resolution.

Features
========
* **Intelligent Flow Routing** - Automatically selects appropriate flow based on issue analysis
* **GitHub Integration** - Reads issue details directly from GitHub for context gathering
* **Multi-Pattern Support** - Supports architectural, TDD, bug fix, documentation, and git workflows
* **Quality Gates** - Built-in quality validation and conditional refinement
* **Agent Orchestration** - Uses lionagi orchestration with specialized agent compositions
* **Dry-run Support** - Preview flow execution without making changes
* **JSON Output** - Machine-readable results for automation

Supported Flow Types:
- architectural: System design and scaffolding flows
- tdd_implementation: Test-driven development flows
- bug_fix: Bug investigation and resolution flows
- documentation: Documentation creation and improvement flows
- git_cycle: Git workflow and release management flows

Synopsis
--------
```bash
khive flow --issue 123                           # Auto-route based on issue analysis
khive flow --issue 123 --flow-type architectural # Force specific flow type
khive flow --issue 123 --dry-run                # Preview without execution
khive flow --issue 123 --visualize              # Enable flow visualization
khive flow --json-output --issue 123            # Machine-readable output
```
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..flows.architectural.flow_script import run_architectural_flow
from ..flows.bug_fix.flow_script import run_bug_fix_flow
from ..flows.documentation.flow_script import run_documentation_flow
from ..flows.git_cycle.flow_script import run_git_cycle_flow
from ..flows.tdd_implementation.flow_script import run_tdd_flow
from ..utils import BaseConfig, die, info_msg
from .base import BaseCLICommand, CLIResult


# --- Configuration ---
@dataclass
class FlowConfig(BaseConfig):
    """Configuration for khive flow command."""

    project_root: Path
    issue_number: int | None = None
    flow_type: str | None = None
    force_flow_type: bool = False
    visualize: bool = False
    github_token: str | None = None

    # CLI state
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False


# --- Flow Type Detection ---
async def detect_flow_type_from_issue(issue_number: int, config: FlowConfig) -> str:
    """
    Analyze GitHub issue to determine appropriate flow type.

    This is a simplified implementation - in practice, you'd use
    the GitHub API to fetch issue details and analyze content.
    """
    # For now, return architectural as default
    # TODO: Implement actual GitHub API integration and intelligent analysis
    return "architectural"


# --- Flow Execution ---
async def execute_flow(
    flow_type: str, issue_details: dict[str, Any], config: FlowConfig
) -> dict[str, Any]:
    """Execute the specified flow type with issue details."""

    if config.dry_run:
        info_msg(
            f"[DRY-RUN] Would execute {flow_type} flow for issue #{config.issue_number}"
        )
        return {
            "flow_type": flow_type,
            "status": "dry_run",
            "message": f"Would execute {flow_type} flow",
            "issue_number": config.issue_number,
        }

    # Extract common parameters
    issue_title = issue_details.get("title", f"Issue #{config.issue_number}")
    issue_description = issue_details.get("description", "No description provided")

    try:
        if flow_type == "architectural":
            result = await run_architectural_flow(
                issue_title=issue_title,
                issue_description=issue_description,
                project_context=f"khive project at {config.project_root}",
                visualize=config.visualize,
            )
        elif flow_type == "tdd_implementation":
            # Extract acceptance criteria or use description
            acceptance_criteria = issue_details.get(
                "acceptance_criteria", issue_description
            )
            result = await run_tdd_flow(
                feature_description=issue_title,
                acceptance_criteria=acceptance_criteria,
                existing_code_context=f"khive codebase at {config.project_root}",
                visualize=config.visualize,
            )
        elif flow_type == "bug_fix":
            # Extract reproduction steps and error logs
            reproduction_steps = issue_details.get("reproduction_steps", "")
            error_logs = issue_details.get("error_logs", "")
            result = await run_bug_fix_flow(
                bug_description=issue_description,
                reproduction_steps=reproduction_steps,
                system_environment=f"khive development environment at {config.project_root}",
                error_logs=error_logs,
                visualize=config.visualize,
            )
        elif flow_type == "documentation":
            # Extract documentation scope
            target_audience = issue_details.get("target_audience", "developers")
            result = await run_documentation_flow(
                documentation_scope=issue_title,
                target_audience=target_audience,
                existing_documentation=f"khive docs in {config.project_root}",
                technical_context=issue_description,
                visualize=config.visualize,
            )
        elif flow_type == "git_cycle":
            result = await run_git_cycle_flow(
                changes_description=issue_description,
                target_branch="main",
                deployment_target="development",
                quality_requirements="standard",
                visualize=config.visualize,
            )
        else:
            return {
                "status": "error",
                "message": f"Unsupported flow type: {flow_type}",
            }

        # Add metadata to result
        result["issue_number"] = config.issue_number
        result["detected_flow_type"] = flow_type

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": f"Flow execution failed: {str(e)}",
            "flow_type": flow_type,
            "issue_number": config.issue_number,
        }


# --- GitHub Integration Placeholder ---
def fetch_issue_details(issue_number: int, config: FlowConfig) -> dict[str, Any]:
    """
    Fetch issue details from GitHub.

    This is a placeholder implementation. In practice, you'd use
    the GitHub API to fetch actual issue details.
    """
    # TODO: Implement actual GitHub API integration
    return {
        "title": f"Issue #{issue_number}",
        "description": "Issue description from GitHub",
        "labels": [],
        "assignees": [],
        "milestone": None,
    }


# --- CLI Command Class ---
class FlowCommand(BaseCLICommand):
    """CLI command for intelligent flow routing and execution."""

    def __init__(self):
        super().__init__(
            command_name="flow",
            description="Intelligent flow router for automated issue resolution",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments."""

        # Core arguments
        parser.add_argument(
            "--issue", type=int, required=True, help="GitHub issue number to process"
        )

        parser.add_argument(
            "--flow-type",
            choices=[
                "architectural",
                "tdd_implementation",
                "bug_fix",
                "documentation",
                "git_cycle",
            ],
            help="Force specific flow type (skips auto-detection)",
        )

        parser.add_argument(
            "--visualize",
            action="store_true",
            help="Enable flow visualization and detailed logging",
        )

        parser.add_argument(
            "--github-token",
            help="GitHub API token for issue fetching (or use GITHUB_TOKEN env var)",
        )

    def _create_config(self, args: argparse.Namespace) -> FlowConfig:
        """Create and return the configuration object."""

        # Get GitHub token from args or environment
        import os

        github_token = args.github_token or os.getenv("GITHUB_TOKEN")

        return FlowConfig(
            project_root=args.project_root,
            issue_number=args.issue,
            flow_type=args.flow_type,
            force_flow_type=bool(args.flow_type),
            visualize=args.visualize,
            github_token=github_token,
            json_output=args.json_output,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate command-line arguments."""
        super()._validate_args(args)

        if args.issue <= 0:
            die(f"Issue number must be positive: {args.issue}")

    async def _execute(self, args: argparse.Namespace, config: FlowConfig) -> CLIResult:
        """Execute the flow routing and execution logic."""

        try:
            # Step 1: Fetch issue details
            info_msg(f"Fetching details for issue #{config.issue_number}...")
            issue_details = fetch_issue_details(config.issue_number, config)

            # Step 2: Determine flow type
            if config.force_flow_type and config.flow_type:
                flow_type = config.flow_type
                info_msg(f"Using forced flow type: {flow_type}")
            else:
                info_msg("Analyzing issue to determine optimal flow type...")
                flow_type = await detect_flow_type_from_issue(
                    config.issue_number, config
                )
                info_msg(f"Detected flow type: {flow_type}")

            # Step 3: Execute flow
            info_msg(f"Executing {flow_type} flow for issue #{config.issue_number}...")
            result = await execute_flow(flow_type, issue_details, config)

            # Step 4: Process results
            if result.get("status") in [
                "completed",
                "ready_for_integration",
                "dry_run",
            ]:
                return CLIResult(
                    status="success",
                    message=f"Flow execution completed successfully for issue #{config.issue_number}",
                    data=result,
                )
            else:
                return CLIResult(
                    status="failure",
                    message=result.get("message", "Flow execution failed"),
                    data=result,
                    exit_code=1,
                )

        except Exception as e:
            return CLIResult(
                status="error",
                message=f"Unexpected error during flow execution: {str(e)}",
                exit_code=1,
            )


# --- Entry Point ---
def main() -> None:
    """Main entry point for khive_flow command."""
    command = FlowCommand()
    exit_code = command.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
