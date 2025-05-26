# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_fmt.py - Opinionated multi-stack formatter for khive projects with nested configuration support.

Features
========
* Formats code across multiple stacks (Python, Rust, Deno, Markdown)
* Supports selective formatting via --stack flag
* Supports check-only mode via --check flag
* Configurable via TOML with nested configuration support for monorepos
* Handles missing formatters gracefully
* Respects nested .khive configurations in subdirectories

CLI
---
    khive fmt [--stack stack1,stack2,...] [--check] [--dry-run] [--json-output] [--verbose]

Exit codes: 0 success · 1 error.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from khive.cli.base import CLIResult, ConfigurableCLICommand, cli_command
from khive.utils import (
    BaseConfig,
    StackConfig,
    check_tool_available,
    error_msg,
    info_msg,
    load_toml_config,
    log_msg,
    merge_config,
    run_command,
    warn_msg,
)

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    pass  # type: ignore

# Maximum number of files to process in a single batch to avoid "Argument list too long" errors
MAX_FILES_PER_BATCH = 500


@dataclass
class FmtConfig(BaseConfig):
    """Configuration for the fmt command."""

    enable: list[str] = field(
        default_factory=lambda: ["python", "rust", "docs", "deno"]
    )
    stacks: dict[str, StackConfig] = field(default_factory=dict)
    check_only: bool = False
    selected_stacks: list[str] = field(default_factory=list)


@cli_command("fmt")
class FormatCommand(ConfigurableCLICommand):
    """Format code across multiple stacks."""

    def __init__(self):
        super().__init__(
            command_name="fmt",
            description="Format code across multiple stacks (Python, Rust, Deno, Markdown)",
        )

    @property
    def config_filename(self) -> str:
        return "fmt.toml"

    @property
    def default_config(self) -> dict[str, Any]:
        """Default configuration for formatting stacks."""
        return {
            "enable": ["python", "rust", "docs", "deno"],
            "stacks": {
                "python": {
                    "name": "python",
                    "cmd": "ruff format {files}",
                    "check_cmd": "ruff format --check {files}",
                    "include": ["*.py"],
                    "exclude": [
                        "*_generated.py",
                        ".venv/**",
                        "venv/**",
                        "env/**",
                        ".env/**",
                        "node_modules/**",
                        "target/**",
                    ],
                },
                "rust": {
                    "name": "rust",
                    "cmd": "cargo fmt",
                    "check_cmd": "cargo fmt --check",
                    "include": ["*.rs"],
                    "exclude": [],
                },
                "docs": {
                    "name": "docs",
                    "cmd": "deno fmt {files}",
                    "check_cmd": "deno fmt --check {files}",
                    "include": ["*.md", "*.markdown"],
                    "exclude": [],
                },
                "deno": {
                    "name": "deno",
                    "cmd": "deno fmt {files}",
                    "check_cmd": "deno fmt --check {files}",
                    "include": ["*.ts", "*.js", "*.jsx", "*.tsx"],
                    "exclude": ["*_generated.*", "node_modules/**"],
                },
                "notebooks": {
                    "name": "notebooks",
                    "cmd": "nbqa ruff {files} --fix",
                    "check_cmd": "nbqa ruff {files}",
                    "include": ["*.ipynb"],
                    "exclude": ["*_generated.ipynb", ".ipynb_checkpoints/**"],
                },
            },
        }

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add fmt-specific arguments."""
        parser.add_argument(
            "--stack",
            help="Comma-separated list of stacks to format (e.g., python,rust,docs).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Check formatting without modifying files.",
        )

    def _create_config(self, args: argparse.Namespace) -> FmtConfig:
        """Create FmtConfig from arguments and configuration files."""
        config = FmtConfig(project_root=args.project_root)
        config.update_from_cli_args(args)

        # Load configuration from files
        loaded_config = self._load_format_config(args.project_root)

        # Convert stack configurations to StackConfig objects
        config.enable = loaded_config.get("enable", self.default_config["enable"])
        config.stacks = {}

        stack_configs = loaded_config.get("stacks", self.default_config["stacks"])
        for stack_name, stack_data in stack_configs.items():
            config.stacks[stack_name] = StackConfig(
                name=stack_name,
                cmd=stack_data.get("cmd", ""),
                check_cmd=stack_data.get("check_cmd", ""),
                include=stack_data.get("include", []),
                exclude=stack_data.get("exclude", []),
                enabled=stack_name in config.enable,
            )

        # Apply CLI arguments
        config.check_only = args.check
        if args.stack:
            config.selected_stacks = args.stack.split(",")
            # Disable stacks not in selected list
            for stack_name, stack in config.stacks.items():
                if stack_name not in config.selected_stacks:
                    stack.enabled = False

        return config

    def _load_format_config(self, project_root: Path) -> dict[str, Any]:
        """Load format configuration from multiple sources."""
        config = self.default_config.copy()

        # Load from pyproject.toml if it exists
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                pyproject_config = load_toml_config(pyproject_path)
                khive_fmt_config = pyproject_config.get("tool", {}).get("khive fmt", {})
                if khive_fmt_config:
                    config = merge_config(config, khive_fmt_config)
            except Exception as e:
                warn_msg(f"Could not parse {pyproject_path}: {e}")

        # Load from .khive/fmt.toml (overrides pyproject.toml)
        khive_config = self._load_command_config(project_root)
        config = merge_config(config, khive_config)

        return config

    def _execute(self, args: argparse.Namespace, config: FmtConfig) -> CLIResult:
        """Execute the format command."""
        # Check for custom script first
        custom_result = self._check_and_run_custom_script(config)
        if custom_result:
            return custom_result

        # Run main formatting flow
        results = self._main_fmt_flow(config)

        # Convert to CLIResult
        status = results["status"]
        if status == "check_failed" or (status == "failure" or status == "error"):
            return CLIResult(
                status="failure", message=results["message"], data=results, exit_code=1
            )
        else:
            return CLIResult(
                status=status, message=results["message"], data=results, exit_code=0
            )

    def _check_and_run_custom_script(self, config: FmtConfig) -> CLIResult | None:
        """Check for custom formatting script and execute it if found."""
        custom_script_path = config.khive_config_dir / "scripts" / "khive_fmt.sh"

        if not custom_script_path.exists():
            return None

        # Verify the script is executable
        if not os.access(custom_script_path, os.X_OK):
            warn_msg(
                f"Custom script {custom_script_path} exists but is not executable. "
                f"Run: chmod +x {custom_script_path}"
            )
            return None

        # Security check
        script_stat = custom_script_path.stat()
        if not stat.S_ISREG(script_stat.st_mode):
            return CLIResult(
                status="failure",
                message="Custom script is not a regular file",
                data={"custom_script": str(custom_script_path)},
                exit_code=1,
            )

        if script_stat.st_mode & stat.S_IWOTH:
            warn_msg(f"Custom script {custom_script_path} is world-writable")

        info_msg(f"Using custom formatting script: {custom_script_path}")

        # Prepare environment
        env = os.environ.copy()
        env.update({
            "KHIVE_PROJECT_ROOT": str(config.project_root),
            "KHIVE_CONFIG_DIR": str(config.khive_config_dir),
            "KHIVE_DRY_RUN": "1" if config.dry_run else "0",
            "KHIVE_VERBOSE": "1" if config.verbose else "0",
            "KHIVE_CHECK_ONLY": "1" if config.check_only else "0",
            "KHIVE_JSON_OUTPUT": "1" if config.json_output else "0",
            "KHIVE_SELECTED_STACKS": ",".join(config.selected_stacks),
            "KHIVE_ENABLED_STACKS": ",".join(config.enable),
        })

        # Build command
        cmd = [str(custom_script_path)]
        if config.check_only:
            cmd.append("--check")
        if config.dry_run:
            cmd.append("--dry-run")
        if config.verbose:
            cmd.append("--verbose")
        if config.json_output:
            cmd.append("--json-output")
        if config.selected_stacks:
            cmd.extend(["--stack", ",".join(config.selected_stacks)])

        # Execute
        result = run_command(
            cmd,
            capture=True,
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
            env=env,
            timeout=300,
            tool_name="custom_script",
        )

        if isinstance(result, int):
            # Dry run mode
            return CLIResult(
                status="success",
                message="Custom script execution completed (dry run)",
                data={"custom_script": str(custom_script_path)},
                exit_code=0,
            )

        # Parse result
        if result.success:
            # Try to parse JSON output
            if config.json_output and result.stdout.strip():
                try:
                    custom_data = json.loads(result.stdout.strip())
                    if isinstance(custom_data, dict) and "status" in custom_data:
                        return CLIResult(
                            status=custom_data["status"],
                            message=custom_data.get(
                                "message", "Custom script completed"
                            ),
                            data=custom_data,
                            exit_code=0,
                        )
                except json.JSONDecodeError:
                    pass

            return CLIResult(
                status="success",
                message="Custom script execution completed successfully",
                data={
                    "custom_script": str(custom_script_path),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                exit_code=0,
            )
        else:
            return CLIResult(
                status="failure",
                message=f"Custom script failed with exit code {result.exit_code}",
                data={
                    "custom_script": str(custom_script_path),
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                exit_code=1,
            )

    def _main_fmt_flow(self, config: FmtConfig) -> dict[str, Any]:
        """Main formatting flow with nested directory support."""
        overall_results: dict[str, Any] = {
            "status": "success",
            "message": "Formatting completed.",
            "stacks_processed": [],
            "nested_directories": [],
        }

        # Find and process nested directories
        nested_dirs = []
        for path in config.project_root.rglob(".khive/fmt.toml"):
            if path.parent.parent != config.project_root:
                nested_dirs.append(path.parent.parent)

        # Sort by depth
        nested_dirs.sort(key=lambda p: len(p.parts))

        # Process nested directories
        processed_dirs = set()
        for nested_dir in nested_dirs:
            # Skip if inside already processed directory
            skip = False
            for processed in processed_dirs:
                try:
                    nested_dir.relative_to(processed)
                    skip = True
                    break
                except ValueError:
                    continue

            if not skip:
                nested_result = self._format_directory_with_nested_config(
                    nested_dir, config
                )
                if nested_result:
                    overall_results["nested_directories"].append(nested_result)
                    processed_dirs.add(nested_dir)

        # Process root directory stacks
        for stack_name, stack in config.stacks.items():
            if stack.enabled:
                stack_result = self._format_stack(stack, config)
                overall_results["stacks_processed"].append(stack_result)

        # Determine overall status
        all_results = overall_results["stacks_processed"] + overall_results.get(
            "nested_directories", []
        )

        if not all_results:
            overall_results["status"] = "skipped"
            overall_results["message"] = "No stacks or directories were processed."
        else:
            has_errors = any(
                result.get("status") in ["error", "failure"] for result in all_results
            )
            has_check_failures = any(
                result.get("status") == "check_failed" for result in all_results
            )

            if has_errors:
                overall_results["status"] = "failure"
                overall_results["message"] = (
                    "Formatting failed for one or more stacks or directories."
                )
            elif has_check_failures:
                overall_results["status"] = "check_failed"
                overall_results["message"] = (
                    "Formatting check failed for one or more stacks or directories."
                )

        return overall_results

    def _format_directory_with_nested_config(
        self, dir_path: Path, parent_config: FmtConfig
    ) -> dict[str, Any] | None:
        """Format a directory that has its own .khive/fmt.toml configuration."""
        info_msg(
            f"Processing nested project: {dir_path.relative_to(parent_config.project_root)}"
        )

        # Create new config for this subdirectory
        nested_config = FmtConfig(project_root=dir_path)
        nested_config.update_from_cli_args(parent_config)

        # Load nested configuration
        loaded_config = self._load_format_config(dir_path)
        nested_config.enable = loaded_config.get(
            "enable", self.default_config["enable"]
        )
        nested_config.stacks = {}

        stack_configs = loaded_config.get("stacks", self.default_config["stacks"])
        for stack_name, stack_data in stack_configs.items():
            nested_config.stacks[stack_name] = StackConfig(
                name=stack_name,
                cmd=stack_data.get("cmd", ""),
                check_cmd=stack_data.get("check_cmd", ""),
                include=stack_data.get("include", []),
                exclude=stack_data.get("exclude", []),
                enabled=stack_name in nested_config.enable,
            )

        # Apply parent's selected stacks
        nested_config.check_only = parent_config.check_only
        nested_config.selected_stacks = parent_config.selected_stacks
        if nested_config.selected_stacks:
            for stack_name, stack in nested_config.stacks.items():
                if stack_name not in nested_config.selected_stacks:
                    stack.enabled = False

        # Check for custom script in nested directory
        custom_result = self._check_and_run_custom_script(nested_config)
        if custom_result:
            return {
                "directory": str(dir_path.relative_to(parent_config.project_root)),
                **custom_result.data,
            }

        # Run formatting for nested directory
        results = {
            "status": "success",
            "message": f"Formatting completed for {dir_path.name}.",
            "directory": str(dir_path.relative_to(parent_config.project_root)),
            "stacks_processed": [],
        }

        for stack_name, stack in nested_config.stacks.items():
            if stack.enabled:
                stack_result = self._format_stack(stack, nested_config)
                results["stacks_processed"].append(stack_result)

        # Update status
        if not results["stacks_processed"]:
            results["status"] = "skipped"
            results["message"] = f"No stacks were processed in {dir_path.name}."
        else:
            has_errors = any(
                r["status"] == "error" for r in results["stacks_processed"]
            )
            has_check_failures = any(
                r["status"] == "check_failed" for r in results["stacks_processed"]
            )

            if has_errors:
                results["status"] = "failure"
                results["message"] = f"Formatting failed in {dir_path.name}."
            elif has_check_failures:
                results["status"] = "check_failed"
                results["message"] = f"Check failed in {dir_path.name}."

        return results

    def _format_stack(self, stack: StackConfig, config: FmtConfig) -> dict[str, Any]:
        """Format files for a specific stack."""
        result = {
            "stack_name": stack.name,
            "status": "skipped",
            "message": f"Stack '{stack.name}' skipped.",
            "files_processed": 0,
        }

        if not stack.enabled:
            return result

        # Check if formatter is available
        tool_name = stack.cmd.split()[0]
        if not check_tool_available(tool_name):
            result["status"] = "error"
            result["message"] = (
                f"Formatter '{tool_name}' not found. Is it installed and in PATH?"
            )
            warn_msg(result["message"])
            return result

        # Find files to format
        files = self._find_files(
            config.project_root, stack.include, stack.exclude, stack.name
        )

        if not files:
            result["status"] = "success"
            result["message"] = f"No files found for stack '{stack.name}'."
            info_msg(result["message"])
            return result

        # Format based on tool type
        if tool_name == "cargo":
            return self._format_cargo(stack, config, files)
        else:
            return self._format_files_in_batches(stack, config, files)

    def _format_cargo(
        self, stack: StackConfig, config: FmtConfig, files: list[Path]
    ) -> dict[str, Any]:
        """Special handling for cargo fmt."""
        # Check if Cargo.toml exists
        cargo_toml_path = config.project_root / "Cargo.toml"
        if not cargo_toml_path.exists():
            return {
                "stack_name": stack.name,
                "status": "skipped",
                "message": "Skipping Rust formatting: No Cargo.toml found",
                "files_processed": 0,
            }

        # Cargo fmt doesn't take file arguments
        cmd_template = stack.check_cmd if config.check_only else stack.cmd
        cmd = cmd_template.split()

        result = run_command(
            cmd,
            capture=True,
            check=False,
            cwd=config.project_root,
            dry_run=config.dry_run,
            tool_name="cargo",
        )

        if isinstance(result, int) or result.success:
            return {
                "stack_name": stack.name,
                "status": "success",
                "message": f"Successfully formatted files for stack '{stack.name}'.",
                "files_processed": len(files),
            }
        else:
            if config.check_only:
                warn_msg(f"Formatting check failed for stack '{stack.name}'.")
                if result.stderr:
                    print(result.stderr)
                return {
                    "stack_name": stack.name,
                    "status": "check_failed",
                    "message": f"Formatting check failed for stack '{stack.name}'.",
                    "stderr": result.stderr,
                    "files_processed": 0,
                }
            else:
                error_msg(f"Formatting failed for stack '{stack.name}'.")
                if result.stderr:
                    print(result.stderr)
                return {
                    "stack_name": stack.name,
                    "status": "error",
                    "message": f"Formatting failed for stack '{stack.name}'.",
                    "stderr": result.stderr,
                    "files_processed": 0,
                }

    def _format_files_in_batches(
        self, stack: StackConfig, config: FmtConfig, files: list[Path]
    ) -> dict[str, Any]:
        """Format files in batches to avoid command line length limits."""
        total_files = len(files)
        files_processed = 0
        all_success = True
        stderr_messages = []

        # Process files in batches
        for i in range(0, total_files, MAX_FILES_PER_BATCH):
            batch_files = files[i : i + MAX_FILES_PER_BATCH]
            batch_size = len(batch_files)

            # Prepare command
            cmd_template = stack.check_cmd if config.check_only else stack.cmd
            file_str = " ".join(str(f) for f in batch_files)
            cmd = cmd_template.replace("{files}", file_str).split()

            log_msg(
                f"Processing batch {i // MAX_FILES_PER_BATCH + 1} ({batch_size} files)"
            )

            # Run formatter
            result = run_command(
                cmd,
                capture=True,
                check=False,
                cwd=config.project_root,
                dry_run=config.dry_run,
                tool_name=stack.cmd.split()[0],
            )

            if isinstance(result, int) or result.success:
                files_processed += batch_size
            else:
                # Check for encoding errors
                if result.stderr and (
                    "UnicodeDecodeError" in result.stderr
                    or "encoding" in result.stderr.lower()
                ):
                    warn_msg("Encoding error in batch, skipping affected files")
                    stderr_messages.append(
                        f"[WARNING] Encoding issues: {result.stderr}"
                    )
                    files_processed += batch_size
                else:
                    all_success = False
                    if result.stderr:
                        stderr_messages.append(result.stderr)
                    if not config.check_only:
                        break

        # Build result
        if all_success:
            return {
                "stack_name": stack.name,
                "status": "success",
                "message": f"Successfully formatted {files_processed} files for stack '{stack.name}'.",
                "files_processed": files_processed,
            }
        else:
            if config.check_only:
                return {
                    "stack_name": stack.name,
                    "status": "check_failed",
                    "message": f"Formatting check failed for stack '{stack.name}'.",
                    "stderr": "\n".join(stderr_messages),
                    "files_processed": files_processed,
                }
            else:
                return {
                    "stack_name": stack.name,
                    "status": "error",
                    "message": f"Formatting failed for stack '{stack.name}'.",
                    "stderr": "\n".join(stderr_messages),
                    "files_processed": files_processed,
                }

    def _find_files(
        self,
        root_dir: Path,
        include_patterns: list[str],
        exclude_patterns: list[str],
        stack_name: str | None = None,
    ) -> list[Path]:
        """Find files matching patterns, respecting nested configurations."""
        import fnmatch

        # Find directories with their own configs to skip
        dirs_with_config = set()
        for path in root_dir.rglob(".khive/fmt.toml"):
            if path.parent.parent != root_dir:
                dirs_with_config.add(path.parent.parent)

        all_files = []

        # Collect files matching include patterns
        for pattern in include_patterns:
            if "**" in pattern:
                parts = pattern.split("**", 1)
                base_dir = parts[0].rstrip("/\\")
                file_pattern = parts[1].lstrip("/\\")

                if (root_dir / base_dir).exists():
                    for path in (root_dir / base_dir).glob(f"**/{file_pattern}"):
                        # Skip files in nested config directories
                        skip = False
                        for config_dir in dirs_with_config:
                            try:
                                path.relative_to(config_dir)
                                skip = True
                                break
                            except ValueError:
                                continue

                        if not skip:
                            all_files.append(path.relative_to(root_dir))
            else:
                for path in root_dir.glob(f"**/{pattern}"):
                    # Skip files in nested config directories
                    skip = False
                    for config_dir in dirs_with_config:
                        try:
                            path.relative_to(config_dir)
                            skip = True
                            break
                        except ValueError:
                            continue

                    if not skip:
                        all_files.append(path.relative_to(root_dir))

        # Apply exclude patterns
        filtered_files = []
        for file_path in all_files:
            excluded = False
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(str(file_path), pattern) or fnmatch.fnmatch(
                    file_path.name, pattern
                ):
                    excluded = True
                    break

            if not excluded:
                filtered_files.append(file_path)

        # Remove duplicates
        seen = set()
        unique_files = []
        for f in filtered_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        log_msg(f"Found {len(unique_files)} files for stack '{stack_name}'")

        return unique_files


def main(argv: list[str] | None = None) -> None:
    """Entry point for khive CLI integration."""
    cmd = FormatCommand()
    cmd.run(argv)


if __name__ == "__main__":
    main()
