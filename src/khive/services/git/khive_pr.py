# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_pr.py - push branch & create GitHub PR with enhanced agent-driven workflow support.

Highlights
----------
* Auto-detects repo root, branch, default base branch (via `gh repo view`).
* If a PR already exists, prints URL (and `--web` opens browser) - **no dupes**.
* Infers title/body from last Conventional Commit; CLI overrides available.
* Supports configuration via `.khive/pr.toml` for default settings.
* Enhanced PR metadata: reviewers, assignees, labels, draft status.
* AI-powered PR description generation using Git Service.
* Structured JSON output for agent consumption.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from khive.cli.base import CLIResult, GitBasedCLICommand, cli_command
from khive.utils import (
    BaseConfig,
    CommandResult,
    check_tool_available,
    git_run,
    info_msg,
    log_msg,
    run_command,
    warn_msg,
)


# --- Configuration ---
@dataclass
class PRConfig(BaseConfig):
    """Configuration for the PR command."""

    default_base_branch: str = "main"
    default_to_draft: bool = False
    default_reviewers: list[str] = field(default_factory=list)
    default_assignees: list[str] = field(default_factory=list)
    default_labels: list[str] = field(default_factory=list)
    prefer_github_template: bool = True
    auto_push_branch: bool = True
    enable_ai_description: bool = True
    ai_provider: str = "auto"

    # CLI-specific fields
    title: str | None = None
    body: str | None = None
    body_from_file: Path | None = None
    base: str | None = None
    draft: bool | None = None
    reviewers: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    web: bool = False
    no_push: bool | None = None
    ai: bool = False  # Explicitly request AI description


# --- Main Command Class ---
@cli_command("pr")
class PRCommand(GitBasedCLICommand):
    """GitHub PR command with AI-powered description generation."""

    def __init__(self):
        super().__init__(
            command_name="pr",
            description="Create GitHub pull requests with enhanced workflow support",
        )
        self._git_service = None

    @property
    def config_filename(self) -> str:
        return "pr.toml"

    @property
    def default_config(self) -> Dict[str, Any]:
        return {
            "default_base_branch": "main",
            "default_to_draft": False,
            "default_reviewers": [],
            "default_assignees": [],
            "default_labels": [],
            "prefer_github_template": True,
            "auto_push_branch": True,
            "enable_ai_description": True,
            "ai_provider": "auto",
        }

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add PR-specific arguments."""
        # PR content
        parser.add_argument("--title", help="Pull request title.")
        body_group = parser.add_mutually_exclusive_group()
        body_group.add_argument("--body", help="Pull request body text.")
        body_group.add_argument(
            "--body-from-file", type=Path, help="Path to a file containing the PR body."
        )

        # PR settings
        parser.add_argument(
            "--base", help="Base branch for the PR (e.g., main, develop)."
        )
        parser.add_argument(
            "--draft",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="Create as a draft PR. (--draft / --no-draft)",
        )

        # Assignees/Reviewers/Labels
        parser.add_argument(
            "--reviewer",
            action="append",
            dest="reviewers",
            help="Add a reviewer (user or team). Can be repeated.",
        )
        parser.add_argument(
            "--assignee",
            action="append",
            dest="assignees",
            help="Add an assignee. Can be repeated.",
        )
        parser.add_argument(
            "--label",
            action="append",
            dest="labels",
            help="Add a label. Can be repeated.",
        )

        # Actions
        parser.add_argument(
            "--web",
            action="store_true",
            help="Open the PR in a web browser after creating or if it exists.",
        )
        push_group = parser.add_mutually_exclusive_group()
        push_group.add_argument(
            "--push",
            dest="no_push",
            action="store_false",
            default=None,
            help="Force push current branch before PR creation.",
        )
        push_group.add_argument(
            "--no-push",
            dest="no_push",
            action="store_true",
            help="Do not push branch before PR creation.",
        )

        parser.add_argument(
            "--ai",
            action="store_true",
            help="Use AI to generate PR description based on commits and changes.",
        )

    def _create_config(self, args: argparse.Namespace) -> PRConfig:
        """Create and return the PR configuration."""
        # Load configuration from file
        file_config = self._load_command_config(args.project_root)

        # Create config object
        config = PRConfig(
            project_root=args.project_root,
            default_base_branch=file_config.get("default_base_branch", "main"),
            default_to_draft=file_config.get("default_to_draft", False),
            default_reviewers=file_config.get("default_reviewers", []),
            default_assignees=file_config.get("default_assignees", []),
            default_labels=file_config.get("default_labels", []),
            prefer_github_template=file_config.get("prefer_github_template", True),
            auto_push_branch=file_config.get("auto_push_branch", True),
            enable_ai_description=file_config.get("enable_ai_description", True),
            ai_provider=file_config.get("ai_provider", "auto"),
            # CLI arguments
            title=args.title,
            body=args.body,
            body_from_file=args.body_from_file,
            base=args.base,
            draft=args.draft,
            reviewers=args.reviewers or [],
            assignees=args.assignees or [],
            labels=args.labels or [],
            web=args.web,
            no_push=args.no_push,
            ai=args.ai,
        )

        # Update from CLI args
        config.update_from_cli_args(args)

        return config

    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate PR-specific arguments."""
        super()._validate_args(args)

        # Check if git and gh are available
        if not check_tool_available("git"):
            raise RuntimeError("Git command not found. Is Git installed and in PATH?")

        if not check_tool_available("gh"):
            raise RuntimeError(
                "GitHub CLI (gh) not found. Please install it from https://cli.github.com/"
            )

    def _execute(self, args: argparse.Namespace, config: PRConfig) -> CLIResult:
        """Execute the PR command."""
        try:
            # Change to project root
            os.chdir(config.project_root)

            # Get current branch
            current_branch = self._get_current_branch(config.project_root)
            if current_branch == "HEAD":
                return CLIResult(
                    status="failure",
                    message="Cannot create PR from a detached HEAD. Checkout a branch first.",
                    exit_code=1,
                )

            # Get target base branch
            target_base = config.base or self._get_default_base_branch(config)

            if current_branch == target_base:
                return CLIResult(
                    status="failure",
                    message=f"Current branch ('{current_branch}') is the same as the base branch ('{target_base}'). Checkout a feature branch.",
                    exit_code=1,
                )

            # Push branch if needed
            should_push = (
                not config.no_push
                if config.no_push is not None
                else config.auto_push_branch
            )
            if should_push:
                push_result = self._push_branch(current_branch, config)
                if not push_result["success"]:
                    return CLIResult(
                        status="failure",
                        message=push_result["message"],
                        data=push_result,
                        exit_code=1,
                    )

            # Check for existing PR
            existing_pr = self._get_existing_pr(current_branch, config)
            if existing_pr:
                info_msg(
                    f"Pull request already exists: {existing_pr['pr_url']}",
                    console=not config.json_output,
                )

                if config.web:
                    self._open_pr_in_browser(existing_pr["pr_number"], config)

                return CLIResult(
                    status="exists",
                    message=f"Pull request for branch '{current_branch}' already exists.",
                    data=existing_pr,
                )

            # Get PR title and body
            pr_title, pr_body = self._prepare_pr_content(
                current_branch, target_base, config
            )

            # Create PR
            pr_result = self._create_pr(
                current_branch=current_branch,
                target_base=target_base,
                title=pr_title,
                body=pr_body,
                config=config,
            )

            if not pr_result["success"]:
                return CLIResult(
                    status="failure",
                    message=pr_result["message"],
                    data=pr_result,
                    exit_code=1,
                )

            if config.web and pr_result.get("pr_url"):
                self._open_pr_in_browser(pr_result.get("pr_url"), config)

            return CLIResult(
                status="success",
                message="Pull request created successfully.",
                data=pr_result,
            )

        except Exception as e:
            return CLIResult(
                status="failure",
                message=f"PR creation failed: {e}",
                exit_code=1,
            )

    def _get_default_base_branch(self, config: PRConfig) -> str:
        """Get the default base branch from GitHub or config."""
        if config.dry_run:
            return config.default_base_branch

        # Try gh first
        result = run_command(
            [
                "gh",
                "repo",
                "view",
                "--json",
                "defaultBranchRef",
                "-q",
                ".defaultBranchRef.name",
            ],
            capture=True,
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
            tool_name="gh",
        )

        if (
            isinstance(result, CommandResult)
            and result.success
            and result.stdout.strip()
        ):
            return result.stdout.strip()

        # Fallback to config
        return config.default_base_branch

    def _push_branch(self, branch: str, config: PRConfig) -> Dict[str, Any]:
        """Push the current branch to origin."""
        info_msg(
            f"Pushing branch '{branch}' to origin...", console=not config.json_output
        )

        result = git_run(
            ["push", "--set-upstream", "origin", branch],
            capture=True,
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        if (isinstance(result, int) and result == 0) or (
            isinstance(result, CommandResult) and result.success
        ):
            info_msg(
                f"Branch '{branch}' pushed successfully.",
                console=not config.json_output,
            )
            return {
                "success": True,
                "message": f"Branch '{branch}' pushed successfully.",
            }
        else:
            stderr = (
                result.stderr if isinstance(result, CommandResult) else "Unknown error"
            )
            return {"success": False, "message": f"Failed to push branch: {stderr}"}

    def _get_existing_pr(
        self, branch: str, config: PRConfig
    ) -> Optional[Dict[str, Any]]:
        """Check if a PR already exists for the branch."""
        if config.dry_run:
            return None

        json_fields = "url,number,title,baseRefName,headRefName,isDraft,state"
        result = run_command(
            ["gh", "pr", "view", branch, "--json", json_fields],
            capture=True,
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
            tool_name="gh",
        )

        if isinstance(result, CommandResult) and result.success:
            try:
                pr_data = json.loads(result.stdout)
                return {
                    "pr_url": pr_data.get("url"),
                    "pr_number": pr_data.get("number"),
                    "pr_title": pr_data.get("title"),
                    "pr_base_branch": pr_data.get("baseRefName"),
                    "pr_head_branch": pr_data.get("headRefName"),
                    "is_draft": pr_data.get("isDraft"),
                    "pr_state": pr_data.get("state"),
                }
            except json.JSONDecodeError:
                log_msg(f"Could not parse JSON from 'gh pr view {branch}'")

        return None

    def _prepare_pr_content(
        self, current_branch: str, target_base: str, config: PRConfig
    ) -> tuple[str, str]:
        """Prepare PR title and body, using AI if requested."""
        # Get last commit details
        commit_subject, commit_body = self._get_last_commit_details(config)

        # Determine title
        pr_title = config.title or commit_subject or f"PR for branch {current_branch}"

        # Determine body
        pr_body = ""

        # Check if we should use AI
        use_ai = config.ai or (
            not config.body
            and not config.body_from_file
            and config.enable_ai_description
            and not self._has_pr_template(config)
        )

        if use_ai:
            info_msg(
                "Generating PR description with AI...", console=not config.json_output
            )
            ai_result = asyncio.run(
                self._generate_ai_pr_description(current_branch, target_base, config)
            )

            if ai_result:
                pr_title = ai_result.get("title", pr_title)
                pr_body = ai_result.get("description", "")

        # If no AI or AI failed, use other sources
        if not pr_body:
            if config.body_from_file:
                try:
                    pr_body = config.body_from_file.read_text()
                except OSError as e:
                    warn_msg(f"Could not read PR body from file: {e}")
                    pr_body = config.body or commit_body or "Pull Request Body"
            elif config.body:
                pr_body = config.body
            elif config.prefer_github_template:
                template_body = self._load_pr_template(config)
                if template_body:
                    pr_body = template_body

        # Final fallback
        if not pr_body:
            pr_body = commit_body or f"Changes from branch {current_branch}."

        return pr_title, pr_body

    def _get_last_commit_details(self, config: PRConfig) -> tuple[str, str]:
        """Get the last commit subject and body."""
        if config.dry_run:
            return "Dry run commit subject", "Dry run commit body"

        result = git_run(
            ["log", "-1", "--pretty=%B"],
            capture=True,
            check=True,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        if isinstance(result, CommandResult):
            full_message = result.stdout.strip()
            parts = full_message.split("\n\n", 1)
            subject = parts[0].strip()
            body = parts[1].strip() if len(parts) > 1 else ""
            return subject, body

        return "Error fetching commit", ""

    def _has_pr_template(self, config: PRConfig) -> bool:
        """Check if a PR template exists."""
        template_paths = [
            config.project_root / ".github" / "pull_request_template.md",
            config.project_root / ".github" / "PULL_REQUEST_TEMPLATE.md",
            config.project_root / "pull_request_template.md",
            config.project_root / "PULL_REQUEST_TEMPLATE.md",
        ]

        return any(path.exists() for path in template_paths)

    def _load_pr_template(self, config: PRConfig) -> Optional[str]:
        """Load PR template if it exists."""
        template_paths = [
            config.project_root / ".github" / "pull_request_template.md",
            config.project_root / ".github" / "PULL_REQUEST_TEMPLATE.md",
            config.project_root / "pull_request_template.md",
            config.project_root / "PULL_REQUEST_TEMPLATE.md",
        ]

        for path in template_paths:
            if path.exists():
                try:
                    return path.read_text()
                except OSError:
                    pass

        return None

    async def _generate_ai_pr_description(
        self, source_branch: str, target_branch: str, config: PRConfig
    ) -> Optional[Dict[str, Any]]:
        """Generate PR description using Git Service."""
        try:
            # Import Git Service
            from khive.services.git import GitServiceGroup
            from khive.services.git.parts import (
                GitAction,
                GitRequest,
                PRDescriptionParams,
            )

            # Get commits
            commits_result = git_run(
                ["log", f"{target_branch}..{source_branch}", "--oneline"],
                capture=True,
                check=False,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            commits = []
            if isinstance(commits_result, CommandResult) and commits_result.stdout:
                commits = commits_result.stdout.strip().split("\n")

            # Get diff summary
            diff_result = git_run(
                ["diff", f"{target_branch}...{source_branch}", "--stat"],
                capture=True,
                check=False,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            diff_summary = ""
            if isinstance(diff_result, CommandResult) and diff_result.stdout:
                diff_summary = diff_result.stdout.strip()

            # Initialize Git Service
            if not self._git_service:
                self._git_service = GitServiceGroup(default_provider=config.ai_provider)

            # Load template if exists
            template = (
                self._load_pr_template(config)
                if config.prefer_github_template
                else None
            )

            # Create request
            request = GitRequest(
                action=GitAction.GENERATE_PR_DESCRIPTION,
                params=PRDescriptionParams(
                    title=config.title,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    commits=commits,
                    diff_summary=diff_summary,
                    template=template,
                    include_checklist=True,
                    repo_path=config.project_root,
                ),
            )

            # Call service
            response = await self._git_service.handle_request(request)

            if response.success and response.content:
                return response.content
            else:
                warn_msg(f"Git Service failed: {response.error}")
                return None

        except ImportError:
            warn_msg("Git Service not available for AI description generation.")
            return None
        except Exception as e:
            log_msg(f"Failed to generate AI PR description: {e}")
            return None

    def _create_pr(
        self,
        current_branch: str,
        target_base: str,
        title: str,
        body: str,
        config: PRConfig,
    ) -> Dict[str, Any]:
        """Create the pull request."""
        # Create PR command
        gh_cmd = [
            "gh",
            "pr",
            "create",
            "--base",
            target_base,
            "--head",
            current_branch,
            "--title",
            title,
        ]

        # Use temp file for body (more robust for multiline)
        with tempfile.NamedTemporaryFile(
            "w+", delete=False, encoding="utf-8", suffix=".md"
        ) as tf:
            tf.write(body)
            body_file_path = tf.name

        gh_cmd.extend(["--body-file", body_file_path])

        # Add draft flag
        is_draft = config.draft if config.draft is not None else config.default_to_draft
        if is_draft:
            gh_cmd.append("--draft")

        # Add reviewers
        reviewers = config.reviewers or config.default_reviewers
        for reviewer in reviewers:
            gh_cmd.extend(["--reviewer", reviewer])

        # Add assignees
        assignees = config.assignees or config.default_assignees
        for assignee in assignees:
            gh_cmd.extend(["--assignee", assignee])

        # Add labels
        labels = config.labels or config.default_labels
        for label in labels:
            gh_cmd.extend(["--label", label])

        info_msg("Creating pull request...", console=not config.json_output)

        result = run_command(
            gh_cmd,
            capture=True,
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
            tool_name="gh",
        )

        # Clean up temp file
        try:
            os.unlink(body_file_path)
        except OSError:
            pass

        if (isinstance(result, int) and result == 0) or (
            isinstance(result, CommandResult) and result.success
        ):
            pr_url = (
                result.stdout.strip()
                if isinstance(result, CommandResult)
                else "DRY_RUN_URL"
            )

            # Get full PR details
            if not config.dry_run:
                pr_details = self._get_existing_pr(current_branch, config)
                if pr_details:
                    pr_details["pr_url"] = pr_url
                    return {"success": True, **pr_details}

            return {
                "success": True,
                "pr_url": pr_url,
                "pr_title": title,
                "pr_base_branch": target_base,
                "pr_head_branch": current_branch,
                "is_draft": is_draft,
            }
        else:
            stderr = (
                result.stderr if isinstance(result, CommandResult) else "Unknown error"
            )
            return {"success": False, "message": f"Failed to create PR: {stderr}"}

    def _open_pr_in_browser(self, pr_identifier: str | int, config: PRConfig) -> None:
        """Open PR in web browser."""
        info_msg("Opening PR in browser...", console=not config.json_output)

        run_command(
            ["gh", "pr", "view", str(pr_identifier), "--web"],
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
            tool_name="gh",
        )

    async def _cleanup(self):
        """Cleanup resources."""
        if self._git_service:
            await self._git_service.close()


# --- CLI Entry Point ---
def cli_entry() -> None:
    """Entry point for khive CLI integration."""
    command = PRCommand()
    exit_code = command.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    cli_entry()
