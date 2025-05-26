# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_clean.py - Delete a branch (local + remote) after
checking out / pulling the default branch.

Features
========
* Deletes a Git branch locally and remotely.
* Intelligently detects the default branch (using `gh`, `git symbolic-ref`, or common fallbacks).
* Refuses to delete the default branch or protected branches.
* Checks out the default branch and pulls latest before deleting.
* Handles cases where local/remote branches might not exist or fail to delete.
* Supports `--all-merged` to clean all branches merged into a base branch.
* Supports `--json-output` for structured reporting.
* Supports `--dry-run` to preview actions without executing.
* Configurable via `.khive/clean.toml`.

CLI
---
    khive clean <branch> [--dry-run] [--json-output] [--verbose]
    khive clean --all-merged [--into <base_branch>] [--yes] [--dry-run] [--json-output] [--verbose]

Exit codes: 0 success · 1 error.
"""

from __future__ import annotations

import argparse
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from khive.cli.base import CLIResult, GitBasedCLICommand
from khive.utils import (
    BaseConfig,
    CommandResult,
    check_tool_available,
    error_msg,
    git_run,
    info_msg,
    run_command,
    warn_msg,
)


# --- Configuration ---
@dataclass
class CleanConfig(BaseConfig):
    """Configuration for the clean command."""

    protected_branch_patterns: list[str] = field(
        default_factory=lambda: ["release/*", "develop"]
    )
    default_remote: str = "origin"
    strict_pull_on_default: bool = False
    all_merged_default_base: str = ""  # If empty, use auto-detected default branch


# --- Main Command Class ---
class CleanCommand(GitBasedCLICommand):
    """Git branch cleanup command."""

    def __init__(self):
        super().__init__(command_name="khive clean", description="Git branch cleaner")

    @property
    def config_filename(self) -> str:
        return "clean.toml"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "protected_branch_patterns": ["release/*", "develop"],
            "default_remote": "origin",
            "strict_pull_on_default": False,
            "all_merged_default_base": "",
        }

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add clean-specific arguments."""
        # Specify branch to clean or use --all-merged
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "branch_name", nargs="?", help="Name of the specific branch to delete."
        )
        group.add_argument(
            "--all-merged",
            action="store_true",
            help="Clean all local branches already merged into the target base branch.",
        )

        parser.add_argument(
            "--into",
            help="For --all-merged, specify the base branch to check merges against (default: auto-detected or config).",
        )
        parser.add_argument(
            "--yes",
            "-y",
            "--force",
            action="store_true",
            help="Skip confirmation when using --all-merged (DANGER!).",
        )

    def _create_config(self, args: argparse.Namespace) -> CleanConfig:
        """Create and return the clean configuration."""
        # Load configuration from file
        file_config = self._load_command_config(args.project_root)

        # Create config object
        config = CleanConfig(
            project_root=args.project_root,
            protected_branch_patterns=file_config.get(
                "protected_branch_patterns", ["release/*", "develop"]
            ),
            default_remote=file_config.get("default_remote", "origin"),
            strict_pull_on_default=file_config.get("strict_pull_on_default", False),
            all_merged_default_base=file_config.get("all_merged_default_base", ""),
        )

        # Update from CLI args
        config.update_from_cli_args(args)

        return config

    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate clean-specific arguments."""
        super()._validate_args(args)

        # Check if git is available
        if not check_tool_available("git"):
            raise RuntimeError("Git command not found. Is Git installed and in PATH?")

        # Validate mutual exclusion (should be handled by argparse, but double-check)
        if args.all_merged and args.branch_name:
            raise ValueError("Cannot use specific branch_name with --all-merged.")

    def _execute(self, args: argparse.Namespace, config: CleanConfig) -> CLIResult:
        """Execute the clean command."""
        try:
            # Detect default branch
            default_branch = self._detect_default_branch(config)
            current_branch = self._get_current_branch(config)

            # Switch to default branch and pull
            switch_result = self._switch_to_default_branch(
                default_branch, current_branch, config
            )
            if not switch_result["success"]:
                return CLIResult(
                    status="failure",
                    message=switch_result["message"],
                    data=switch_result,
                    exit_code=1,
                )

            # Determine branches to clean
            if args.all_merged:
                branches_result = self._get_merged_branches_to_clean(
                    args, default_branch, config
                )
                if not branches_result["success"]:
                    return CLIResult(
                        status=(
                            "failure" if branches_result.get("is_error") else "skipped"
                        ),
                        message=branches_result["message"],
                        data=branches_result,
                    )
                branches_to_clean = branches_result["branches"]
            else:
                branches_to_clean = [args.branch_name]

            # Clean branches
            clean_results = []
            for branch_name in branches_to_clean:
                if not config.json_output:
                    info_msg(f"Cleaning branch: {branch_name}")

                result = self._clean_single_branch(branch_name, default_branch, config)
                clean_results.append(result)

            # Determine overall status
            failed_branches = [r for r in clean_results if not r["success"]]

            if failed_branches:
                return CLIResult(
                    status="partial_failure",
                    message=f"Cleaned {len(clean_results) - len(failed_branches)} of {len(clean_results)} branches. {len(failed_branches)} had issues.",
                    data={
                        "default_branch_info": switch_result,
                        "branches_processed": clean_results,
                        "failed_count": len(failed_branches),
                    },
                )
            else:
                message = f"All {len(clean_results)} targeted branch(es) processed successfully."
                if config.dry_run:
                    message = "Dry run completed for targeted branches."

                return CLIResult(
                    status="success",
                    message=message,
                    data={
                        "default_branch_info": switch_result,
                        "branches_processed": clean_results,
                    },
                )

        except Exception as e:
            return CLIResult(
                status="failure", message=f"Clean failed: {e}", exit_code=1
            )

    def _detect_default_branch(self, config: CleanConfig) -> str:
        """Detect the default branch using various methods."""
        # Try gh CLI first (if available)
        if check_tool_available("gh"):
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
                branch = result.stdout.strip()
                info_msg(f"Detected default branch via 'gh repo view': {branch}")
                return branch

        # Try git symbolic-ref
        result = git_run(
            ["symbolic-ref", f"refs/remotes/{config.default_remote}/HEAD"],
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
            branch = result.stdout.strip().split("/")[-1]
            info_msg(f"Detected default branch via 'git symbolic-ref': {branch}")
            return branch

        # Fallback to common names
        for common_branch in ["main", "master"]:
            result = git_run(
                ["show-ref", "--verify", "--quiet", f"refs/heads/{common_branch}"],
                check=False,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            if isinstance(result, (int, CommandResult)) and (
                (isinstance(result, int) and result == 0)
                or (isinstance(result, CommandResult) and result.success)
            ):
                info_msg(f"Using fallback default branch: {common_branch}")
                return common_branch

        warn_msg("Could not reliably detect default branch. Falling back to 'main'.")
        return "main"

    def _switch_to_default_branch(
        self, default_branch: str, current_branch: str, config: CleanConfig
    ) -> dict[str, Any]:
        """Switch to default branch and pull latest changes."""
        result = {
            "success": True,
            "name": default_branch,
            "checkout_status": "SKIPPED",
            "pull_status": "SKIPPED",
            "message": "Default branch operations completed",
        }

        # Checkout default branch if not already on it
        if current_branch != default_branch:
            info_msg(f"Switching to default branch '{default_branch}'...")
            checkout_result = git_run(
                ["checkout", default_branch],
                check=False,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            if (
                isinstance(checkout_result, CommandResult)
                and not checkout_result.success
            ):
                result["success"] = False
                result["checkout_status"] = "FAILED"
                result["message"] = (
                    f"Failed to checkout default branch '{default_branch}'. Error: {checkout_result.stderr}"
                )
                return result

            result["checkout_status"] = "OK_DRY_RUN" if config.dry_run else "OK"
        else:
            info_msg(f"Already on default branch '{default_branch}'.")
            result["checkout_status"] = "ALREADY_ON"

        # Pull latest changes
        info_msg(f"Pulling latest changes for '{default_branch}'...")
        pull_result = git_run(
            ["pull", config.default_remote, default_branch],
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        if isinstance(pull_result, CommandResult) and not pull_result.success:
            result["pull_status"] = "FAILED"
            warn_msg(f"Failed to pull '{default_branch}'. Error: {pull_result.stderr}")

            if config.strict_pull_on_default:
                result["success"] = False
                result["message"] = (
                    f"Strict pull enabled and failed for '{default_branch}'. Halting."
                )
                return result
        else:
            result["pull_status"] = "OK_DRY_RUN" if config.dry_run else "OK"

        return result

    def _get_merged_branches_to_clean(
        self, args: argparse.Namespace, default_branch: str, config: CleanConfig
    ) -> dict[str, Any]:
        """Get list of merged branches to clean."""
        merged_base = args.into or config.all_merged_default_base or default_branch

        info_msg(f"Identifying branches merged into '{merged_base}'...")

        if config.dry_run:
            # Return dummy data for dry run
            raw_merged_branches = ["feature/dry-merged-1", "feature/dry-merged-2"]
        else:
            # Ensure base branch is up-to-date
            git_run(
                ["checkout", merged_base],
                check=True,
                cwd=config.project_root,
                dry_run=config.dry_run,
            )
            git_run(
                ["pull", config.default_remote, merged_base],
                check=False,
                cwd=config.project_root,
                dry_run=config.dry_run,
            )

            # Get merged branches
            result = git_run(
                ["branch", "--merged", merged_base, "--format=%(refname:short)"],
                capture=True,
                check=True,
                dry_run=config.dry_run,
                cwd=config.project_root,
            )

            if isinstance(result, CommandResult) and result.success:
                raw_merged_branches = [
                    b.strip() for b in result.stdout.splitlines() if b.strip()
                ]
            else:
                return {
                    "success": False,
                    "is_error": True,
                    "message": "Failed to get merged branches",
                    "branches": [],
                }

        # Filter out protected branches
        branches_to_clean = [
            b
            for b in raw_merged_branches
            if not self._is_branch_protected(b, default_branch, config)
        ]

        if not branches_to_clean:
            return {
                "success": False,
                "is_error": False,
                "message": f"No un-protected branches found merged into '{merged_base}' to clean.",
                "branches": [],
            }

        # Confirm deletion if not using --yes
        if not config.dry_run and not args.yes:
            print(
                f"The following branches merged into '{merged_base}' will be deleted locally and remotely:"
            )
            for b_name in branches_to_clean:
                print(f"  - {b_name}")

            confirm = (
                input("Are you sure you want to continue? (yes/no): ").strip().lower()
            )
            if confirm != "yes":
                return {
                    "success": False,
                    "is_error": False,
                    "message": "Branch cleaning aborted by user confirmation.",
                    "branches": [],
                }

        return {
            "success": True,
            "message": f"Found {len(branches_to_clean)} branches to clean",
            "branches": branches_to_clean,
        }

    def _is_branch_protected(
        self, branch_name: str, default_branch: str, config: CleanConfig
    ) -> bool:
        """Check if a branch is protected from deletion."""
        if branch_name == default_branch:
            return True

        for pattern in config.protected_branch_patterns:
            if fnmatch.fnmatchcase(branch_name, pattern):
                return True

        return False

    def _clean_single_branch(
        self, branch_to_clean: str, default_branch: str, config: CleanConfig
    ) -> dict[str, Any]:
        """Clean a single branch (local and remote)."""
        result = {
            "success": True,
            "branch_name": branch_to_clean,
            "local_delete_status": "SKIPPED",
            "remote_delete_status": "SKIPPED",
            "message": "",
        }

        # Check if branch is protected
        if self._is_branch_protected(branch_to_clean, default_branch, config):
            result["success"] = False
            result["local_delete_status"] = "PROTECTED"
            result["remote_delete_status"] = "PROTECTED"
            result["message"] = (
                f"Branch '{branch_to_clean}' is protected and will not be deleted."
            )
            warn_msg(result["message"])
            return result

        # Delete local branch
        local_result = self._delete_local_branch(branch_to_clean, config)
        result["local_delete_status"] = local_result["status"]

        # Delete remote branch
        remote_result = self._delete_remote_branch(branch_to_clean, config)
        result["remote_delete_status"] = remote_result["status"]

        # Determine overall success
        if result["local_delete_status"] in [
            "OK",
            "OK_DRY_RUN",
            "NOT_FOUND",
        ] and result["remote_delete_status"] in ["OK", "OK_DRY_RUN", "NOT_FOUND"]:
            result["message"] = f"Branch '{branch_to_clean}' cleaned successfully."
        else:
            result["success"] = False
            result["message"] = (
                f"Branch '{branch_to_clean}' cleanup had issues. Check statuses."
            )

        return result

    def _delete_local_branch(
        self, branch_name: str, config: CleanConfig
    ) -> dict[str, Any]:
        """Delete local branch."""
        # Check if local branch exists
        exists_result = git_run(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        local_exists = isinstance(exists_result, (int, CommandResult)) and (
            (isinstance(exists_result, int) and exists_result == 0)
            or (isinstance(exists_result, CommandResult) and exists_result.success)
        )

        if not local_exists and not config.dry_run:
            info_msg(f"Local branch '{branch_name}' not found.")
            return {"status": "NOT_FOUND"}

        # Delete the branch
        delete_result = git_run(
            ["branch", "-D", branch_name],
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        if isinstance(delete_result, (int, CommandResult)) and (
            (isinstance(delete_result, int) and delete_result == 0)
            or (isinstance(delete_result, CommandResult) and delete_result.success)
        ):
            info_msg(f"Local branch '{branch_name}' deleted.")
            return {"status": "OK_DRY_RUN" if config.dry_run else "OK"}
        else:
            stderr = ""
            if isinstance(delete_result, CommandResult):
                stderr = delete_result.stderr
            warn_msg(f"Failed to delete local branch '{branch_name}'. Stderr: {stderr}")
            return {"status": "FAILED", "error": stderr}

    def _delete_remote_branch(
        self, branch_name: str, config: CleanConfig
    ) -> dict[str, Any]:
        """Delete remote branch."""
        # Check if remote branch exists
        exists_result = git_run(
            ["ls-remote", "--exit-code", "--heads", config.default_remote, branch_name],
            check=False,
            capture=True,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        remote_exists = isinstance(exists_result, (int, CommandResult)) and (
            (isinstance(exists_result, int) and exists_result == 0)
            or (
                isinstance(exists_result, CommandResult)
                and exists_result.success
                and exists_result.stdout.strip()
            )
        )

        if not remote_exists and not config.dry_run:
            info_msg(
                f"Remote branch '{branch_name}' on '{config.default_remote}' not found."
            )
            return {"status": "NOT_FOUND"}

        # Delete the remote branch
        delete_result = git_run(
            ["push", config.default_remote, "--delete", branch_name],
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )

        if isinstance(delete_result, (int, CommandResult)) and (
            (isinstance(delete_result, int) and delete_result == 0)
            or (isinstance(delete_result, CommandResult) and delete_result.success)
        ):
            info_msg(
                f"Remote branch '{branch_name}' on '{config.default_remote}' deleted."
            )
            return {"status": "OK_DRY_RUN" if config.dry_run else "OK"}
        else:
            stderr = ""
            if isinstance(delete_result, CommandResult):
                stderr = delete_result.stderr
            warn_msg(
                f"Failed to delete remote branch '{branch_name}'. Stderr: {stderr}"
            )
            return {"status": "FAILED", "error": stderr}


# --- CLI Entry Point ---
def main() -> None:
    """Main entry point for the khive clean command."""
    command = CleanCommand()
    exit_code = command.run()
    exit(exit_code)


if __name__ == "__main__":
    main()
