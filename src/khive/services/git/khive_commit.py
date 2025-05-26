# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_commit.py - one-stop commit helper for the khive mono-repo.

Features
========
* **Conventional-Commit enforcement** with helpful error hints.
* **Auto-stage** everything (or `--patch` to pick hunks).
* **Smart skip** - exits 0 when nothing to commit (useful for CI).
* **`--amend`** flag optionally rewrites last commit instead of creating new.
* **`--no-push`** for local-only commits (default pushes to `origin <branch>`).
* **Ensures Git identity** in headless containers (sets fallback name/email).
* **Dry-run** mode prints git commands without executing.
* **Verbose** mode echoes every git command.
* **Structured input** for commit message parts (--type, --scope, --subject, etc.)
* **Search ID injection** for evidence citation
* **Interactive mode** for guided commit creation
* **JSON output** option for machine-readable results
* **Configuration** via .khive/commit.toml
* **Auto-publish branch** if not already tracking a remote.
* **Mode Indication** via `--by` flag, adding a `Committed-by:` trailer.
* **AI-powered message generation** using Git Service

Synopsis
--------
```bash
khive commit "feat(ui): add dark-mode toggle"           # Auto-publishes new branch if needed
khive commit "fix: missing null-check" --patch --no-push
khive commit "chore!: bump API to v2" --amend -v
khive commit --type feat --scope ui --subject "add dark-mode toggle" --search-id pplx-abc
khive commit --interactive
khive commit --type feat --scope api --subject "new endpoint" --by khive-coder
khive commit --ai  # Generate message with AI
khive commit       # Auto-generates message if none provided
```
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
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
    warn_msg,
)


# --- Configuration ---
@dataclass
class CommitConfig(BaseConfig):
    """Configuration for the commit command."""

    default_push: bool = True
    allow_empty_commits: bool = False
    conventional_commit_types: list[str] = field(
        default_factory=lambda: [
            "feat",
            "fix",
            "build",
            "chore",
            "ci",
            "docs",
            "perf",
            "refactor",
            "revert",
            "style",
            "test",
        ]
    )
    conventional_commit_regex_pattern: str | None = None
    fallback_git_user_name: str = "khive-bot"
    fallback_git_user_email: str = "khive-bot@example.com"
    default_stage_mode: str = "all"  # 'all' or 'patch'

    # AI configuration
    enable_ai_messages: bool = True
    ai_provider: str = "auto"  # auto, openai, anthropic, ollama

    # CLI-specific fields
    message: str | None = None
    type: str | None = None
    scope: str | None = None
    subject: str | None = None
    body: str | None = None
    breaking_change_description: str | None = None
    closes: str | None = None
    search_id: str | None = None
    by: str | None = None
    interactive: bool = False
    patch_stage: str | None = None
    amend: bool = False
    allow_empty: bool = False
    push: bool | None = None
    ai: bool = False  # Explicitly request AI message

    @property
    def conventional_commit_regex(self) -> re.Pattern:
        """Get the compiled regex pattern for conventional commits."""
        if self.conventional_commit_regex_pattern:
            return re.compile(self.conventional_commit_regex_pattern)
        types_str = "|".join(map(re.escape, self.conventional_commit_types))
        # Basic Conventional Commit Regex: type(scope)!: subject
        # Allows for optional scope and breaking change indicator !
        return re.compile(rf"^(?:{types_str})(?:\([\w-]+\))?(?:!)?: .+")


# --- Main Command Class ---
@cli_command("commit")
class CommitCommand(GitBasedCLICommand):
    """Git commit command with conventional commit enforcement."""

    def __init__(self):
        super().__init__(
            command_name="commit",
            description="Git commit helper with Conventional Commit and auto branch publishing",
        )
        self._git_service = None

    @property
    def config_filename(self) -> str:
        return "commit.toml"

    @property
    def default_config(self) -> Dict[str, Any]:
        return {
            "default_push": True,
            "allow_empty_commits": False,
            "conventional_commit_types": [
                "feat",
                "fix",
                "build",
                "chore",
                "ci",
                "docs",
                "perf",
                "refactor",
                "revert",
                "style",
                "test",
            ],
            "fallback_git_user_name": "khive-bot",
            "fallback_git_user_email": "khive-bot@example.com",
            "default_stage_mode": "all",
            "enable_ai_messages": True,
            "ai_provider": "auto",
        }

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add commit-specific arguments."""
        # Message construction options
        group_msg = parser.add_argument_group(
            "Commit Message Construction (choose one style)"
        )
        group_msg.add_argument(
            "message",
            nargs="?",
            default=None,
            help="Full commit message (header + optional body). If used, structured flags below are ignored.",
        )

        group_struct = parser.add_argument_group(
            "Structured Commit Message Parts (used if positional 'message' is not given)"
        )
        group_struct.add_argument(
            "--type", help="Conventional commit type (e.g., feat, fix)."
        )
        group_struct.add_argument("--scope", help="Optional scope of the change.")
        group_struct.add_argument("--subject", help="Subject line of the commit.")
        group_struct.add_argument("--body", help="Detailed body of the commit message.")
        group_struct.add_argument(
            "--breaking-change-description",
            "--bc",
            help="Description of the breaking change. Implies '!' in header.",
        )
        group_struct.add_argument(
            "--closes", help="Issue number this commit closes (e.g., 123)."
        )
        group_struct.add_argument(
            "--search-id", help="Search ID for evidence (e.g., pplx-abc)."
        )
        group_struct.add_argument(
            "--by",
            help="Mode slug indicating the committer's 'persona' (e.g., khive-implementer, khive-researcher).",
        )

        parser.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            help="Interactively build commit message and stage files.",
        )

        parser.add_argument(
            "--ai",
            action="store_true",
            help="Use AI to generate commit message based on staged changes.",
        )

        # Staging options
        group_stage = parser.add_mutually_exclusive_group()
        group_stage.add_argument(
            "--patch-stage",
            "-p",
            action="store_const",
            const="patch",
            help="Use 'git add -p' for interactive staging. Overrides default_stage_mode.",
        )
        group_stage.add_argument(
            "--all-stage",
            "-A",
            action="store_const",
            const="all",
            dest="patch_stage",
            help="Use 'git add -A' to stage all. Overrides default_stage_mode.",
        )

        # Git command modifiers
        parser.add_argument(
            "--amend", action="store_true", help="Amend the previous commit."
        )
        parser.add_argument(
            "--allow-empty",
            action="store_true",
            help="Allow an empty commit (used with 'git commit --allow-empty').",
        )

        # Push control (mutually exclusive with explicit preference)
        group_push = parser.add_mutually_exclusive_group()
        group_push.add_argument(
            "--push",
            action="store_true",
            dest="push",
            default=None,
            help="Force push after commit (overrides config default_push=false).",
        )
        group_push.add_argument(
            "--no-push",
            action="store_false",
            dest="push",
            help="Prevent push after commit (overrides config default_push=true).",
        )

    def _create_config(self, args: argparse.Namespace) -> CommitConfig:
        """Create and return the commit configuration."""
        # Load configuration from file
        file_config = self._load_command_config(args.project_root)

        # Create config object
        config = CommitConfig(
            project_root=args.project_root,
            default_push=file_config.get("default_push", True),
            allow_empty_commits=file_config.get("allow_empty_commits", False),
            conventional_commit_types=file_config.get(
                "conventional_commit_types",
                self.default_config["conventional_commit_types"],
            ),
            conventional_commit_regex_pattern=file_config.get(
                "conventional_commit_regex_pattern"
            ),
            fallback_git_user_name=file_config.get(
                "fallback_git_user_name", "khive-bot"
            ),
            fallback_git_user_email=file_config.get(
                "fallback_git_user_email", "khive-bot@example.com"
            ),
            default_stage_mode=file_config.get("default_stage_mode", "all"),
            enable_ai_messages=file_config.get("enable_ai_messages", True),
            ai_provider=file_config.get("ai_provider", "auto"),
            # CLI arguments
            message=args.message,
            type=args.type,
            scope=args.scope,
            subject=args.subject,
            body=args.body,
            breaking_change_description=getattr(
                args, "breaking_change_description", None
            ),
            closes=args.closes,
            search_id=args.search_id,
            by=args.by,
            interactive=args.interactive,
            patch_stage=getattr(args, "patch_stage", None),
            amend=args.amend,
            allow_empty=args.allow_empty,
            push=args.push,
            ai=args.ai,
        )

        # Validate stage mode
        if config.default_stage_mode not in ["all", "patch"]:
            warn_msg(
                f"Invalid 'default_stage_mode' ('{config.default_stage_mode}') in config. Using 'all'."
            )
            config.default_stage_mode = "all"

        # Update from CLI args
        config.update_from_cli_args(args)

        return config

    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate commit-specific arguments."""
        super()._validate_args(args)

        # Check if git is available
        if not check_tool_available("git"):
            raise RuntimeError("Git command not found. Is Git installed and in PATH?")

        # Validate message strategy - now allows no input for AI generation
        has_message = args.message or (args.type and args.subject)
        has_strategy = args.interactive or args.ai

        if not has_message and not has_strategy:
            # No explicit strategy - will try AI if enabled
            pass

        # Warn about conflicting options
        if args.message and (args.type or args.scope or args.subject or args.body):
            warn_msg(
                "Positional 'message' provided along with structured flags "
                "(--type, --scope, etc.). Positional message will be used."
            )

    def _execute(self, args: argparse.Namespace, config: CommitConfig) -> CLIResult:
        """Execute the commit command."""
        try:
            # Change to project root
            os.chdir(config.project_root)

            # Ensure git identity
            self._ensure_git_identity(config)

            # Handle staging unless amending
            if not config.amend:
                stage_mode = config.patch_stage or config.default_stage_mode
                staged_something = self._stage_changes(stage_mode, config)

                if not staged_something:
                    if config.allow_empty_commits and config.allow_empty:
                        info_msg(
                            "No changes staged, but proceeding with empty commit as allowed.",
                            console=not config.json_output,
                        )
                    else:
                        return CLIResult(
                            status="skipped",
                            message="Nothing to commit (working tree clean or no changes staged).",
                        )

            # Build commit message
            commit_message = self._build_commit_message(config)
            if not commit_message:
                # Try AI generation if no message and AI is enabled
                if config.enable_ai_messages or config.ai:
                    info_msg(
                        "No commit message provided. Generating with AI...",
                        console=not config.json_output,
                    )
                    # Run async method synchronously
                    commit_message = asyncio.run(
                        self._generate_ai_commit_message(config)
                    )

                if not commit_message:
                    return CLIResult(
                        status="failure",
                        message="Failed to create commit message. Try --interactive or provide a message.",
                        exit_code=1,
                    )

            # Auto-detect mode if not explicitly set
            if not config.by:
                detected_mode = self._detect_khive_mode()
                if detected_mode:
                    info_msg(
                        f"Auto-detected mode: {detected_mode}",
                        console=not config.json_output,
                    )
                    # Add mode to commit message
                    if "\n\nCommitted-by:" not in commit_message:
                        commit_message += f"\n\nCommitted-by: {detected_mode}"

            # Validate conventional commit format
            if not config.conventional_commit_regex.match(
                commit_message.splitlines()[0]
            ):
                return CLIResult(
                    status="failure",
                    message=f"Commit message header does not follow Conventional Commits pattern: '{commit_message.splitlines()[0]}'",
                    data={"pattern": config.conventional_commit_regex.pattern},
                    exit_code=1,
                )

            # Perform the commit
            commit_result = self._perform_commit(commit_message, config)
            if not commit_result["success"]:
                return CLIResult(
                    status="failure",
                    message=commit_result["message"],
                    data=commit_result,
                    exit_code=1,
                )

            # Handle push
            push_result = self._handle_push(config)
            if not push_result["success"]:
                return CLIResult(
                    status="failure",
                    message=push_result["message"],
                    data={**commit_result, **push_result},
                    exit_code=1,
                )

            # Success
            message = f"Commit {commit_result['commit_sha']}. {push_result['message']}"
            if config.dry_run:
                message += " (dry run)."

            return CLIResult(
                status="success",
                message=message,
                data={
                    "commit_sha": commit_result["commit_sha"],
                    "branch_pushed": push_result.get("branch"),
                    "push_status": push_result["status"],
                },
            )

        except Exception as e:
            return CLIResult(
                status="failure", message=f"Commit failed: {e}", exit_code=1
            )

    def _ensure_git_identity(self, config: CommitConfig) -> None:
        """Ensure Git user identity is configured."""
        for key, default_val in [
            ("user.name", config.fallback_git_user_name),
            ("user.email", config.fallback_git_user_email),
        ]:
            result = git_run(
                ["config", "--get", key],
                capture=True,
                check=False,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            if (
                isinstance(result, CommandResult)
                and result.success
                and result.stdout.strip()
            ):
                continue  # Identity already set

            info_msg(f"Git {key} not set. Setting to fallback: {default_val}")
            git_run(
                ["config", key, default_val],
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

    def _stage_changes(self, stage_mode: str, config: CommitConfig) -> bool:
        """Stage changes and return True if something was staged."""
        # Check if anything is unstaged first
        dirty_result = git_run(
            ["diff", "--quiet"],
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        is_dirty = (isinstance(dirty_result, int) and dirty_result == 1) or (
            isinstance(dirty_result, CommandResult) and dirty_result.exit_code == 1
        )

        if is_dirty:
            if stage_mode == "patch":
                info_msg(
                    "Staging changes interactively ('git add -p')...",
                    console=not config.json_output,
                )
                if config.dry_run:
                    info_msg("[DRY-RUN] Would run 'git add -p'")
                else:
                    # Run interactive staging
                    p_process = subprocess.run(
                        ["git", "add", "-p"], cwd=config.project_root
                    )
                    if p_process.returncode != 0:
                        warn_msg(
                            "Interactive staging ('git add -p') exited non-zero. "
                            "Staging might be incomplete.",
                            console=not config.json_output,
                        )
            else:  # 'all'
                info_msg(
                    "Staging all changes ('git add -A')...",
                    console=not config.json_output,
                )
                git_run(["add", "-A"], dry_run=config.dry_run, cwd=config.project_root)
        else:
            info_msg(
                "Working tree is clean (no unstaged changes).",
                console=not config.json_output,
            )

        # Check if anything is staged for commit
        staged_result = git_run(
            ["diff", "--cached", "--quiet"],
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        has_staged_changes = (
            isinstance(staged_result, int) and staged_result == 1
        ) or (isinstance(staged_result, CommandResult) and staged_result.exit_code == 1)

        if not has_staged_changes and is_dirty:
            info_msg(
                "No changes were staged (e.g., 'git add -p' was exited without staging).",
                console=not config.json_output,
            )
            return False

        return has_staged_changes

    def _build_commit_message(self, config: CommitConfig) -> str | None:
        """Build the commit message from arguments or interactively."""
        if config.interactive:
            return self._interactive_commit_prompt(config)

        if config.message:
            return config.message

        return self._build_structured_message(config)

    def _build_structured_message(self, config: CommitConfig) -> str | None:
        """Build commit message from structured arguments."""
        if not config.type or not config.subject:
            return None

        header = config.type
        if config.scope:
            header += f"({config.scope})"
        if config.breaking_change_description:
            header += "!"
        header += f": {config.subject}"

        body_parts = []
        if config.body:
            body_parts.append(config.body)

        if config.breaking_change_description:
            body_parts.append(f"BREAKING CHANGE: {config.breaking_change_description}")

        # Append search ID and closes issues
        extra_info = []
        if config.search_id:
            extra_info.append(f"(search: {config.search_id})")
        if config.closes:
            extra_info.append(f"Closes #{config.closes}")

        if extra_info:
            if body_parts:
                body_parts.append("")  # Ensure separation
            body_parts.append(" ".join(extra_info))

        full_message = header
        if body_parts:
            full_message += "\n\n" + "\n".join(body_parts)

        # Add trailer
        if config.by:
            if body_parts or "\n\n" not in full_message:
                full_message += "\n\n"
            full_message += f"Committed-by: {config.by}"

        return full_message.strip()

    def _interactive_commit_prompt(self, config: CommitConfig) -> str | None:
        """Interactively build commit message."""
        info_msg(
            "Starting interactive commit message builder...",
            console=not config.json_output,
        )

        try:
            # Get commit type
            commit_type = ""
            while commit_type not in config.conventional_commit_types:
                commit_type = (
                    input(
                        f"Enter commit type ({', '.join(config.conventional_commit_types)}): "
                    )
                    .strip()
                    .lower()
                )

            # Get scope
            scope = input("Enter scope (optional, e.g., 'ui', 'api'): ").strip()

            # Get subject
            subject = ""
            while not subject:
                subject = input(
                    "Enter subject (max 72 chars, imperative mood): "
                ).strip()

            # Get body
            print(
                "Enter body (multi-line, press Ctrl-D or Ctrl-Z then Enter on Windows to finish):"
            )
            body_lines = []
            while True:
                try:
                    line = input()
                    body_lines.append(line)
                except EOFError:
                    break
            body = "\n".join(body_lines).strip()

            # Get breaking change info
            is_breaking = (
                input("Is this a breaking change? (yes/no): ").strip().lower() == "yes"
            )
            breaking_desc = ""
            if is_breaking:
                breaking_desc = input("Describe the breaking change: ").strip()

            # Get additional info
            closes_issue = input("Issue ID this closes (e.g., 123, optional): ").strip()
            search_id = input(
                "Search ID for evidence (e.g., pplx-abc, optional): "
            ).strip()
            committed_by = input(
                "Committed by (mode slug, optional, e.g., khive-implementer): "
            ).strip()

            # Construct message
            header = commit_type
            if scope:
                header += f"({scope})"
            if is_breaking:
                header += "!"
            header += f": {subject}"

            full_body_parts = []
            if body:
                full_body_parts.append(body)
            if breaking_desc:
                full_body_parts.append(f"BREAKING CHANGE: {breaking_desc}")

            extra_info = []
            if search_id:
                extra_info.append(f"(search: {search_id})")
            if closes_issue:
                extra_info.append(f"Closes #{closes_issue}")
            if extra_info:
                if full_body_parts:
                    full_body_parts.append("")
                full_body_parts.append(" ".join(extra_info))

            final_message = header
            if full_body_parts:
                final_message += "\n\n" + "\n".join(full_body_parts)

            if committed_by:
                if full_body_parts or "\n\n" not in final_message:
                    final_message += "\n\n"
                final_message += f"Committed-by: {committed_by}"

            # Confirm
            info_msg("\nConstructed commit message:", console=not config.json_output)
            if not config.json_output:
                print(final_message)

            if input("Confirm commit message? (yes/no): ").strip().lower() != "yes":
                info_msg("Commit aborted by user.", console=not config.json_output)
                return None

            return final_message.strip()

        except KeyboardInterrupt:
            info_msg(
                "\nInteractive commit aborted by user.", console=not config.json_output
            )
            return None

    def _perform_commit(
        self, commit_message: str, config: CommitConfig
    ) -> dict[str, Any]:
        """Perform the git commit operation."""
        commit_cmd_args = ["commit", "-m", commit_message]

        if config.amend:
            commit_cmd_args.append("--amend")

        if config.allow_empty and not config.amend:
            commit_cmd_args.append("--allow-empty")

        commit_result = git_run(
            commit_cmd_args,
            dry_run=config.dry_run,
            capture=True,
            check=False,
            cwd=config.project_root,
        )

        if isinstance(commit_result, int) and commit_result == 0:  # Dry run success
            return {
                "success": True,
                "commit_sha": "DRY_RUN_SHA",
                "message": "Commit successful (dry run).",
            }
        elif isinstance(commit_result, CommandResult) and commit_result.success:
            # Get commit SHA
            sha_result = git_run(
                ["rev-parse", "HEAD"],
                capture=True,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            commit_sha = "UNKNOWN_SHA"
            if isinstance(sha_result, CommandResult) and sha_result.success:
                commit_sha = sha_result.stdout.strip()

            info_msg(
                f"Committed successfully. SHA: {commit_sha}",
                console=not config.json_output,
            )
            return {
                "success": True,
                "commit_sha": commit_sha,
                "message": f"Committed successfully. SHA: {commit_sha}",
            }
        else:
            stderr = ""
            if isinstance(commit_result, CommandResult):
                stderr = commit_result.stderr

            return {
                "success": False,
                "message": f"Git commit command failed. Stderr: {stderr}",
                "stderr": stderr,
            }

    def _handle_push(self, config: CommitConfig) -> dict[str, Any]:
        """Handle the push operation."""
        should_push = config.push if config.push is not None else config.default_push

        if not should_push:
            info_msg("Push skipped.", console=not config.json_output)
            return {
                "success": True,
                "status": "SKIPPED",
                "message": "Push skipped by user/config.",
            }

        current_branch = self._get_current_branch(config.project_root)
        push_args = ["push"]
        action_verb = "Pushing"

        if config.dry_run:
            push_args.extend(["--set-upstream", "origin", current_branch])
            action_verb = "Publishing and setting upstream for"
        else:
            # Check if upstream is configured
            remote_result = git_run(
                ["config", f"branch.{current_branch}.remote"],
                capture=True,
                check=False,
                dry_run=False,
                cwd=config.project_root,
            )
            merge_result = git_run(
                ["config", f"branch.{current_branch}.merge"],
                capture=True,
                check=False,
                dry_run=False,
                cwd=config.project_root,
            )

            is_remote_set = (
                isinstance(remote_result, CommandResult)
                and remote_result.success
                and remote_result.stdout.strip()
            )
            is_merge_set = (
                isinstance(merge_result, CommandResult)
                and merge_result.success
                and merge_result.stdout.strip()
            )

            if not (is_remote_set and is_merge_set):
                push_args.extend(["--set-upstream", "origin", current_branch])
                action_verb = "Publishing and setting upstream for"
            else:
                push_args.extend(["origin", current_branch])

        action_description = f"{action_verb} branch '{current_branch}' to origin"
        if not config.json_output:
            info_msg(action_description, console=True)

        push_result = git_run(
            push_args,
            dry_run=config.dry_run,
            capture=True,
            check=False,
            cwd=config.project_root,
        )

        if isinstance(push_result, int) and push_result == 0:  # Dry run success
            return {
                "success": True,
                "status": "OK_DRY_RUN",
                "branch": current_branch,
                "message": f"{action_description} - successful (dry run).",
            }
        elif isinstance(push_result, CommandResult) and push_result.success:
            return {
                "success": True,
                "status": "OK",
                "branch": current_branch,
                "message": f"{action_description} - successful.",
            }
        else:
            stderr = ""
            if isinstance(push_result, CommandResult):
                stderr = push_result.stderr

            return {
                "success": False,
                "status": "FAILED",
                "branch": current_branch,
                "message": f"{action_description} failed for branch '{current_branch}'. Stderr: {stderr}",
                "stderr": stderr,
            }

    def _detect_khive_mode(self) -> Optional[str]:
        """Detect which khive mode initiated this commit."""
        # Check environment variable first (most reliable)
        khive_mode = os.environ.get("KHIVE_MODE")
        if khive_mode:
            return khive_mode

        # Check parent process name for khive modes
        try:
            # Try to detect from process tree
            parent_pid = os.getppid()
            if sys.platform == "win32":
                # Windows
                result = subprocess.run(
                    ["wmic", "process", "get", "processid,commandline"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if str(parent_pid) in line:
                            # Look for khive mode patterns
                            for mode in [
                                "orchestrator",
                                "researcher",
                                "architect",
                                "implementer",
                                "reviewer",
                                "documenter",
                            ]:
                                if f"khive-{mode}" in line.lower():
                                    return f"khive-{mode}"
            else:
                # Unix-like systems
                result = subprocess.run(
                    ["ps", "-p", str(parent_pid), "-o", "command="],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    command = result.stdout.strip()
                    for mode in [
                        "orchestrator",
                        "researcher",
                        "architect",
                        "implementer",
                        "reviewer",
                        "documenter",
                    ]:
                        if f"khive-{mode}" in command.lower():
                            return f"khive-{mode}"
        except Exception as e:
            log_msg(f"Could not detect parent process: {e}")

        # Check for mode-specific files in .khive directory
        khive_dir = (
            self.config.khive_config_dir if hasattr(self, "config") else Path(".khive")
        )
        if khive_dir.exists():
            mode_file = khive_dir / "current_mode"
            if mode_file.exists():
                try:
                    mode = mode_file.read_text().strip()
                    if mode:
                        return mode
                except Exception:
                    pass

        return None

    async def _generate_ai_commit_message(self, config: CommitConfig) -> Optional[str]:
        """Generate commit message using Git Service."""
        try:
            # Import Git Service
            from khive.services.git.git_service import GitServiceGroup
            from khive.services.git.parts import (
                CommitMessageParams,
                GitAction,
                GitRequest,
            )

            # Get diff and file changes
            diff_result = git_run(
                ["diff", "--cached"],
                capture=True,
                check=False,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            diff = ""
            if isinstance(diff_result, CommandResult) and diff_result.stdout:
                diff = diff_result.stdout.strip()

            file_changes_result = git_run(
                ["diff", "--cached", "--name-status"],
                capture=True,
                check=False,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            file_changes = ""
            if (
                isinstance(file_changes_result, CommandResult)
                and file_changes_result.stdout
            ):
                file_changes = file_changes_result.stdout.strip()

            if not diff and not file_changes:
                warn_msg("No staged changes to analyze for AI message generation.")
                return None

            # Initialize Git Service
            if not self._git_service:
                self._git_service = GitServiceGroup(default_provider=config.ai_provider)

            # Prepare parameters
            closes_issues = []
            if config.closes:
                closes_issues = (
                    [config.closes] if isinstance(config.closes, str) else config.closes
                )

            co_authors = []
            if config.by:
                # If mode is specified, could add as co-author or just in body
                pass

            # Create request
            request = GitRequest(
                action=GitAction.GENERATE_COMMIT_MESSAGE,
                params=CommitMessageParams(
                    diff=diff,
                    file_changes=file_changes,
                    conventional=True,
                    context=config.body,  # Use body as additional context
                    include_stats=False,
                    closes_issues=closes_issues,
                    co_authors=co_authors,
                    repo_path=config.project_root,
                ),
            )

            # Call service
            response = await self._git_service.handle_request(request)

            if response.success and response.content:
                message = response.content.get("message", "")

                # Add search ID if provided
                if config.search_id and "(search:" not in message:
                    if "\n\n" in message:
                        parts = message.split("\n\n", 1)
                        message = (
                            f"{parts[0]}\n\n(search: {config.search_id})\n\n{parts[1]}"
                        )
                    else:
                        message += f"\n\n(search: {config.search_id})"

                # Add mode if detected or specified
                mode = config.by or self._detect_khive_mode()
                if mode and "Committed-by:" not in message:
                    message += f"\n\nCommitted-by: {mode}"

                return message
            else:
                warn_msg(f"Git Service failed: {response.error}")
                return None

        except ImportError:
            warn_msg("Git Service not available. Falling back to basic generation.")
            return None
        except Exception as e:
            log_msg(f"Failed to generate AI commit message: {e}")
            return None

    async def _cleanup(self):
        """Cleanup resources."""
        if self._git_service:
            await self._git_service.close()


# --- CLI Entry Point ---
def cli_entry() -> None:
    """Entry point for khive CLI integration."""
    command = CommitCommand()
    sys.exit(command.run())


if __name__ == "__main__":
    cli_entry()
