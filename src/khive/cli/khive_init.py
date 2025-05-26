# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_init.py - Project initialization tool for khive projects.

Features
========
* Auto-detects project stacks (Python/uv, Node/pnpm, Rust/cargo)
* Initializes dependencies for detected or specified stacks
* Supports custom initialization steps via configuration
* Handles stack-specific options via --stack and --extra flags
* Executes custom initialization scripts if present

CLI
---
    khive init [--stack STACK] [--extra EXTRA] [--step STEP] [--dry-run] [--json-output] [--verbose]

Exit codes: 0 success · 1 error.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import stat
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from khive.cli.base import CLIResult, ConfigurableCLICommand, WorkflowStep, cli_command
from khive.utils import (
    BaseConfig,
    check_tool_available,
    ensure_directory,
    error_msg,
    info_msg,
    log_msg,
    warn_msg,
)


@dataclass
class CustomStepConfig:
    """Configuration for a custom initialization step."""

    cmd: str | None = None
    run_if: str | None = None
    cwd: str | None = None  # Relative to project_root


@dataclass
class InitConfig(BaseConfig):
    """Configuration for the init command."""

    ignore_missing_optional_tools: bool = False
    disable_auto_stacks: list[str] = field(default_factory=list)
    force_enable_steps: list[str] = field(default_factory=list)
    custom_steps: dict[str, CustomStepConfig] = field(default_factory=dict)
    steps_to_run_explicitly: list[str] | None = None
    stack: str | None = None  # Specific stack to initialize
    extra: str | None = None  # Extra dependencies to include


class AsyncWorkflowStep(WorkflowStep):
    """Async version of WorkflowStep for initialization."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[[InitConfig], Awaitable[dict[str, Any]]],
        required: bool = True,
    ):
        super().__init__(name, description, required)
        self.func = func

    async def execute(self, config: InitConfig) -> dict[str, Any]:
        """Execute the async step function."""
        try:
            result = await self.func(config)
            self.completed = result.get("status") in ["OK", "SKIPPED", "DRY_RUN"]
            if not self.completed:
                self.error = result.get("message", "Unknown error")
            return result
        except Exception as e:
            self.error = str(e)
            return {
                "name": self.name,
                "status": "FAILED",
                "message": f"Step failed: {e}",
            }


@cli_command("init")
class InitCommand(ConfigurableCLICommand):
    """Initialize project dependencies and tooling."""

    def __init__(self):
        super().__init__(
            command_name="init",
            description="Initialize project dependencies and tooling",
        )
        self._setup_builtin_steps()

    @property
    def config_filename(self) -> str:
        return "init.toml"

    @property
    def default_config(self) -> dict[str, Any]:
        """Default configuration for init command."""
        return {
            "ignore_missing_optional_tools": False,
            "disable_auto_stacks": [],
            "force_enable_steps": [],
            "custom_steps": {},
        }

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add init-specific arguments."""
        parser.add_argument(
            "--step",
            action="append",
            help="Run only specific step(s) by name. Can be repeated.",
        )
        parser.add_argument(
            "--stack",
            type=str,
            help="Specify which stack to initialize: 'uv' (Python), 'pnpm' (Node.js), 'cargo' (Rust)",
        )
        parser.add_argument(
            "--extra",
            type=str,
            help="Extra dependencies or options to include (stack-specific)",
        )

    def _create_config(self, args: argparse.Namespace) -> InitConfig:
        """Create InitConfig from arguments and configuration files."""
        config = InitConfig(project_root=args.project_root)
        config.update_from_cli_args(args)

        # Generate default config if needed
        if not args.dry_run:
            self._generate_default_config_if_needed(config)

        # Load configuration
        loaded_config = self._load_command_config(args.project_root)

        # Apply loaded configuration
        config.ignore_missing_optional_tools = loaded_config.get(
            "ignore_missing_optional_tools", False
        )
        config.disable_auto_stacks = loaded_config.get("disable_auto_stacks", [])
        config.force_enable_steps = loaded_config.get("force_enable_steps", [])

        # Load custom steps
        for name, step_data in loaded_config.get("custom_steps", {}).items():
            config.custom_steps[name] = CustomStepConfig(
                cmd=step_data.get("cmd"),
                run_if=step_data.get("run_if"),
                cwd=step_data.get("cwd"),
            )

        # Apply CLI arguments
        config.steps_to_run_explicitly = args.step
        config.stack = args.stack
        config.extra = args.extra

        return config

    def _generate_default_config_if_needed(self, config: InitConfig) -> None:
        """Generate default init.toml if it doesn't exist."""
        config_file = config.khive_config_dir / self.config_filename
        if config_file.exists():
            return

        content = """# khive init configuration
ignore_missing_optional_tools = false

# Stacks to disable even if auto-detected (e.g., "python", "npm", "rust")
disable_auto_stacks = []

# Steps to force enable (e.g., "tools", "husky", or stacks like "python")
force_enable_steps = []

# Custom steps (example)
#[custom_steps.example_custom_build]
#cmd = "echo Hello from khive custom step"
#run_if = "file_exists:pyproject.toml"  # Condition to run this step
#cwd = "."  # Working directory relative to project root
"""

        try:
            ensure_directory(config_file.parent)
            config_file.write_text(content)
            info_msg(
                f"Generated default config: {config_file.relative_to(config.project_root)}"
            )
        except OSError as e:
            warn_msg(f"Could not write default config: {e}")

    def _execute(self, args: argparse.Namespace, config: InitConfig) -> CLIResult:
        """Execute the init command."""
        # Run async initialization
        results = asyncio.run(self._run_async(config))

        # Determine overall status
        overall_status = "success"
        failed_steps = []

        for result in results:
            if result["status"] == "FAILED":
                overall_status = "failure"
                failed_steps.append(result["name"])
            elif result["status"] == "WARNING" and overall_status == "success":
                overall_status = "warning"

        # Build message
        if overall_status == "success":
            message = "Project initialization completed successfully"
        elif overall_status == "warning":
            message = "Project initialization completed with warnings"
        else:
            message = f"Project initialization failed. Failed steps: {', '.join(failed_steps)}"

        return CLIResult(
            status=overall_status,
            message=message,
            data={"steps": results},
            exit_code=1 if overall_status == "failure" else 0,
        )

    async def _run_async(self, config: InitConfig) -> list[dict[str, Any]]:
        """Run the async initialization workflow."""
        # Check for custom init script first
        custom_results = await self._check_and_run_custom_script_async(config)
        if custom_results is not None:
            return custom_results

        # Determine steps to run
        steps_to_run = self._determine_steps_to_run(config)

        if not steps_to_run:
            return [
                {
                    "name": "orchestrator",
                    "status": "SKIPPED",
                    "message": "No steps selected or auto-detected to run",
                }
            ]

        # Execute steps
        all_results = []

        for step_name, (step_type, step_action) in steps_to_run.items():
            if not config.json_output:
                print(f"\n{info_msg(f'Running {step_name}...', console=False)}")

            if config.dry_run:
                result = self._dry_run_step(step_name, step_type, step_action, config)
            else:
                if step_type == "builtin":
                    result = await step_action(config)
                else:  # custom
                    result = await self._run_custom_step(step_name, step_action, config)

            all_results.append(result)

            # Display status
            if not config.json_output and not config.dry_run:
                status = result["status"]
                if status == "OK":
                    info_msg(f"  {step_name}: {result.get('message', 'Success')}")
                elif status in ["SKIPPED", "WARNING", "DRY_RUN"]:
                    warn_msg(f"  {step_name}: {result.get('message', status)}")
                else:
                    error_msg(f"  {step_name}: {result.get('message', 'Failed')}")

            # Stop on failure (except for tools step)
            if result["status"] == "FAILED" and step_name != "tools":
                all_results.append({
                    "name": "orchestrator_halt",
                    "status": "FAILED",
                    "message": f"Step '{step_name}' failed. Halting execution.",
                })
                break

        return all_results

    def _determine_steps_to_run(
        self, config: InitConfig
    ) -> OrderedDict[str, tuple[str, Any]]:
        """Determine which steps to run based on configuration and auto-detection."""
        steps = OrderedDict()

        # Handle explicit step selection
        if config.steps_to_run_explicitly:
            for step_name in config.steps_to_run_explicitly:
                if step_name in self.builtin_steps:
                    steps[step_name] = ("builtin", self.builtin_steps[step_name])
                elif step_name in config.custom_steps:
                    steps[step_name] = ("custom", config.custom_steps[step_name])
                else:
                    warn_msg(f"Unknown step '{step_name}'")
            return steps

        # Handle stack-specific initialization
        if config.stack:
            steps["tools"] = ("builtin", self.builtin_steps["tools"])

            stack_map = {"uv": "python", "pnpm": "npm", "cargo": "rust"}

            if config.stack in stack_map:
                step_name = stack_map[config.stack]
                steps[step_name] = ("builtin", self.builtin_steps[step_name])

                # Include husky for npm/pnpm
                if (
                    config.stack == "pnpm"
                    and (config.project_root / "package.json").exists()
                ):
                    steps["husky"] = ("builtin", self.builtin_steps["husky"])
            else:
                warn_msg(f"Unknown stack '{config.stack}'")
        else:
            # Auto-detection logic
            for name, func in self.builtin_steps.items():
                should_run = False

                if name == "tools":
                    should_run = True
                elif (
                    (
                        name == "python"
                        and (config.project_root / "pyproject.toml").exists()
                    )
                    or name == "npm"
                    and (config.project_root / "package.json").exists()
                    or name == "rust"
                    and (config.project_root / "Cargo.toml").exists()
                ):
                    should_run = name not in config.disable_auto_stacks
                elif (
                    name == "husky" and (config.project_root / "package.json").exists()
                ):
                    should_run = "npm" not in config.disable_auto_stacks

                if should_run or name in config.force_enable_steps:
                    steps[name] = ("builtin", func)

        # Add custom steps
        for name, custom_cfg in config.custom_steps.items():
            if name not in steps:
                steps[name] = ("custom", custom_cfg)

        return steps

    def _dry_run_step(
        self, step_name: str, step_type: str, step_action: Any, config: InitConfig
    ) -> dict[str, Any]:
        """Generate dry-run result for a step."""
        cmd_info = "N/A (builtin function)"
        cwd_info = ""

        if step_type == "custom":
            custom_cfg = step_action
            cmd_info = custom_cfg.cmd or "No command defined"
            if custom_cfg.cwd:
                cwd_info = f" in {config.project_root / custom_cfg.cwd}"

        message = f"[DRY-RUN] Would run {step_type} step '{step_name}'. Command: {cmd_info}{cwd_info}"

        if not config.json_output:
            print(f"  {message}")

        return {"name": step_name, "status": "DRY_RUN", "message": message}

    async def _run_custom_step(
        self, step_name: str, custom_cfg: CustomStepConfig, config: InitConfig
    ) -> dict[str, Any]:
        """Run a custom initialization step."""
        # Check run_if condition
        if not self._check_condition(custom_cfg.run_if, config.project_root):
            return {
                "name": step_name,
                "status": "SKIPPED",
                "message": f"Condition '{custom_cfg.run_if}' not met",
            }

        if not custom_cfg.cmd:
            return {
                "name": step_name,
                "status": "SKIPPED",
                "message": "No command defined for custom step",
            }

        # Determine working directory
        cwd = config.project_root
        if custom_cfg.cwd:
            cwd = config.project_root / custom_cfg.cwd

        # Execute command
        return await self._run_shell_command_async(
            custom_cfg.cmd, cwd=cwd, step_name=step_name
        )

    def _check_condition(self, expr: str | None, project_root: Path) -> bool:
        """Check if a run_if condition is met."""
        if not expr:
            return True

        try:
            condition_type, _, value = expr.partition(":")

            if condition_type == "file_exists":
                return (project_root / value).exists()
            elif condition_type == "tool_exists":
                return check_tool_available(value)
            else:
                warn_msg(f"Unknown condition type: {condition_type}")
                return False
        except Exception as e:
            warn_msg(f"Error evaluating condition '{expr}': {e}")
            return False

    async def _run_shell_command_async(
        self, cmd: str, cwd: Path, step_name: str
    ) -> dict[str, Any]:
        """Run a shell command asynchronously."""
        log_msg(f"[{step_name}] $ {cmd} (in {cwd})")

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await process.communicate()

            stdout = stdout_bytes.decode(errors="replace").strip()
            stderr = stderr_bytes.decode(errors="replace").strip()

            status = "OK" if process.returncode == 0 else "FAILED"
            message = f"Command '{cmd}' {'succeeded' if status == 'OK' else f'failed (exit code {process.returncode})'}"

            if stderr and status == "FAILED":
                message += f". Stderr: {stderr}"

            return {
                "name": step_name,
                "status": status,
                "return_code": process.returncode,
                "command": cmd,
                "stdout": stdout,
                "stderr": stderr,
                "message": message,
            }
        except Exception as e:
            return {
                "name": step_name,
                "status": "FAILED",
                "message": f"Failed to execute command: {e}",
                "command": cmd,
            }

    async def _check_and_run_custom_script_async(
        self, config: InitConfig
    ) -> list[dict[str, Any]] | None:
        """Check for and run custom initialization script."""
        custom_script_path = config.khive_config_dir / "scripts" / "khive_init.sh"

        if not custom_script_path.exists():
            return None

        # Security checks
        if not os.access(custom_script_path, os.X_OK):
            warn_msg(
                f"Custom script exists but is not executable. "
                f"Run: chmod +x {custom_script_path}"
            )
            return None

        script_stat = custom_script_path.stat()
        if not stat.S_ISREG(script_stat.st_mode):
            error_msg("Custom script is not a regular file")
            return [
                {
                    "name": "custom_init_script",
                    "status": "FAILED",
                    "message": "Custom script is not a regular file",
                }
            ]

        if script_stat.st_mode & stat.S_IWOTH:
            warn_msg("Custom script is world-writable, security risk")

        info_msg(f"Using custom initialization script: {custom_script_path}")

        # Prepare environment
        env = self._prepare_custom_script_env(config)

        # Build command
        cmd = [str(custom_script_path)]
        if config.dry_run:
            cmd.append("--dry-run")
        if config.verbose:
            cmd.append("--verbose")
        if config.json_output:
            cmd.append("--json-output")
        if config.stack:
            cmd.extend(["--stack", config.stack])
        if config.extra:
            cmd.extend(["--extra", config.extra])
        if config.steps_to_run_explicitly:
            for step in config.steps_to_run_explicitly:
                cmd.extend(["--step", step])

        if config.dry_run:
            return [
                {
                    "name": "custom_init_script",
                    "status": "DRY_RUN",
                    "message": "Custom script execution (dry run)",
                    "command": " ".join(cmd),
                }
            ]

        # Execute script
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=config.project_root,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=600,  # 10 minute timeout
            )

            stdout = stdout_bytes.decode(errors="replace").strip()
            stderr = stderr_bytes.decode(errors="replace").strip()

            # Try to parse JSON output
            if config.json_output and stdout:
                try:
                    result = json.loads(stdout)
                    if isinstance(result, dict) and "steps" in result:
                        return result["steps"]
                    elif isinstance(result, list):
                        return result
                except json.JSONDecodeError:
                    pass

            # Return result based on exit code
            if process.returncode == 0:
                return [
                    {
                        "name": "custom_init_script",
                        "status": "OK",
                        "message": "Custom script completed successfully",
                        "stdout": stdout,
                        "stderr": stderr,
                    }
                ]
            else:
                return [
                    {
                        "name": "custom_init_script",
                        "status": "FAILED",
                        "message": f"Custom script failed with exit code {process.returncode}",
                        "stdout": stdout,
                        "stderr": stderr,
                    }
                ]

        except asyncio.TimeoutError:
            return [
                {
                    "name": "custom_init_script",
                    "status": "FAILED",
                    "message": "Custom script timed out after 10 minutes",
                }
            ]
        except Exception as e:
            return [
                {
                    "name": "custom_init_script",
                    "status": "FAILED",
                    "message": f"Failed to execute custom script: {e}",
                }
            ]

    def _prepare_custom_script_env(self, config: InitConfig) -> dict[str, str]:
        """Prepare environment variables for custom script."""
        # Detect stacks
        detected_stacks = []
        if (config.project_root / "pyproject.toml").exists():
            detected_stacks.append("python")
        if (config.project_root / "package.json").exists():
            detected_stacks.append("npm")
        if (config.project_root / "Cargo.toml").exists():
            detected_stacks.append("rust")

        # Get enabled steps
        steps = self._determine_steps_to_run(config)
        enabled_builtin = [n for n, (t, _) in steps.items() if t == "builtin"]
        enabled_custom = [n for n, (t, _) in steps.items() if t == "custom"]

        env = os.environ.copy()
        env.update({
            "KHIVE_PROJECT_ROOT": str(config.project_root),
            "KHIVE_CONFIG_DIR": str(config.khive_config_dir),
            "KHIVE_DRY_RUN": "1" if config.dry_run else "0",
            "KHIVE_VERBOSE": "1" if config.verbose else "0",
            "KHIVE_JSON_OUTPUT": "1" if config.json_output else "0",
            "KHIVE_DETECTED_STACKS": ",".join(detected_stacks),
            "KHIVE_DISABLED_STACKS": ",".join(config.disable_auto_stacks),
            "KHIVE_FORCED_STEPS": ",".join(config.force_enable_steps),
            "KHIVE_REQUESTED_STACK": config.stack or "",
            "KHIVE_REQUESTED_EXTRA": config.extra or "",
            "KHIVE_ENABLED_BUILTIN_STEPS": ",".join(enabled_builtin),
            "KHIVE_ENABLED_CUSTOM_STEPS": ",".join(enabled_custom),
            "KHIVE_EXPLICIT_STEPS": ",".join(config.steps_to_run_explicitly or []),
        })

        return env

    def _setup_builtin_steps(self):
        """Set up built-in initialization steps."""
        self.builtin_steps = OrderedDict([
            ("tools", self._step_tools),
            ("python", self._step_python),
            ("npm", self._step_npm),
            ("rust", self._step_rust),
            ("husky", self._step_husky),
        ])

    # Built-in step implementations
    async def _step_tools(self, config: InitConfig) -> dict[str, Any]:
        """Check for required and optional tools."""
        messages = []
        overall_status = "OK"

        # Determine required tools based on detected stacks
        required_tools = []
        if (
            config.project_root / "pyproject.toml"
        ).exists() and "python" not in config.disable_auto_stacks:
            required_tools.append(("uv", "Python environment/package management"))
        if (
            config.project_root / "package.json"
        ).exists() and "npm" not in config.disable_auto_stacks:
            required_tools.append(("pnpm", "Node package management"))
        if (
            config.project_root / "Cargo.toml"
        ).exists() and "rust" not in config.disable_auto_stacks:
            required_tools.extend([
                ("cargo", "Rust build tool/package manager"),
                ("rustc", "Rust compiler"),
            ])

        optional_tools = [("gh", "GitHub CLI"), ("jq", "JSON processor")]

        # Check required tools
        for tool, purpose in required_tools:
            if not check_tool_available(tool):
                messages.append(f"Required tool '{tool}' ({purpose}) not found")
                overall_status = "FAILED"
            else:
                messages.append(f"Tool '{tool}' found")

        if overall_status == "FAILED":
            return {
                "name": "tools",
                "status": "FAILED",
                "message": "Missing required tools. " + "; ".join(messages),
            }

        # Check optional tools
        for tool, purpose in optional_tools:
            if not check_tool_available(tool):
                msg = f"Optional tool '{tool}' ({purpose}) not found"
                if not config.ignore_missing_optional_tools:
                    messages.append(msg)

        return {
            "name": "tools",
            "status": overall_status,
            "message": (
                "Tool check completed. " + "; ".join(messages)
                if messages
                else "All tools present"
            ),
        }

    async def _step_python(self, config: InitConfig) -> dict[str, Any]:
        """Initialize Python dependencies with uv."""
        if not (config.project_root / "pyproject.toml").exists():
            return {
                "name": "python",
                "status": "SKIPPED",
                "message": "No pyproject.toml found",
            }

        if not check_tool_available("uv"):
            return {
                "name": "python",
                "status": "SKIPPED",
                "message": "uv tool not found",
            }

        cmd = ["uv", "sync"]

        # Handle extra dependencies
        if config.stack == "uv" and config.extra:
            if config.extra == "all":
                cmd.append("--all-extras")
            else:
                cmd.extend(["--extra", config.extra])

        return await self._run_shell_command_async(
            " ".join(cmd), cwd=config.project_root, step_name="python"
        )

    async def _step_npm(self, config: InitConfig) -> dict[str, Any]:
        """Initialize Node.js dependencies with pnpm."""
        if not (config.project_root / "package.json").exists():
            return {
                "name": "npm",
                "status": "SKIPPED",
                "message": "No package.json found",
            }

        if not check_tool_available("pnpm"):
            return {
                "name": "npm",
                "status": "SKIPPED",
                "message": "pnpm tool not found",
            }

        cmd = ["pnpm", "install"]

        # Handle extra options
        if config.stack == "pnpm" and config.extra:
            if config.extra == "all":
                cmd.append("--production=false")
            elif config.extra == "dev":
                cmd.append("--dev")
            elif config.extra == "prod":
                cmd.append("--production")
        else:
            cmd.append("--frozen-lockfile")

        return await self._run_shell_command_async(
            " ".join(cmd), cwd=config.project_root, step_name="npm"
        )

    async def _step_rust(self, config: InitConfig) -> dict[str, Any]:
        """Initialize Rust project with cargo."""
        if not (config.project_root / "Cargo.toml").exists():
            return {
                "name": "rust",
                "status": "SKIPPED",
                "message": "No Cargo.toml found",
            }

        if not check_tool_available("cargo"):
            return {
                "name": "rust",
                "status": "SKIPPED",
                "message": "cargo tool not found",
            }

        cmd = ["cargo"]

        # Handle extra options
        if config.stack == "cargo" and config.extra:
            if config.extra == "all":
                cmd.extend(["build", "--all-features", "--workspace"])
            elif config.extra == "dev":
                cmd.extend(["check", "--workspace", "--profile", "dev"])
            elif config.extra == "test":
                cmd.extend(["test", "--workspace"])
            else:
                cmd.extend(["check", "--workspace", "--features", config.extra])
        else:
            cmd.extend(["check", "--workspace"])

        return await self._run_shell_command_async(
            " ".join(cmd), cwd=config.project_root, step_name="rust"
        )

    async def _step_husky(self, config: InitConfig) -> dict[str, Any]:
        """Set up Husky git hooks."""
        if not (config.project_root / "package.json").exists():
            return {
                "name": "husky",
                "status": "SKIPPED",
                "message": "No package.json found",
            }

        if not check_tool_available("pnpm"):
            return {"name": "husky", "status": "SKIPPED", "message": "pnpm not found"}

        husky_dir = config.project_root / ".husky"
        if husky_dir.is_dir():
            return {"name": "husky", "status": "OK", "message": "Husky already set up"}

        # Check for prepare script
        try:
            pkg_data = json.loads((config.project_root / "package.json").read_text())
            if "prepare" not in pkg_data.get("scripts", {}):
                return {
                    "name": "husky",
                    "status": "SKIPPED",
                    "message": "No 'prepare' script in package.json",
                }
        except Exception:
            return {
                "name": "husky",
                "status": "FAILED",
                "message": "Malformed package.json",
            }

        # Run prepare script
        result = await self._run_shell_command_async(
            "pnpm run prepare", cwd=config.project_root, step_name="husky"
        )

        # Check if husky was set up
        if result["status"] == "OK" and husky_dir.is_dir():
            result["message"] = "Husky setup successful"
        elif result["status"] == "OK":
            result["status"] = "WARNING"
            result["message"] = "prepare script succeeded but .husky not created"

        return result


def main(argv: list[str] | None = None) -> None:
    """Entry point for khive CLI integration."""
    cmd = InitCommand()
    cmd.run(argv)


if __name__ == "__main__":
    main()
